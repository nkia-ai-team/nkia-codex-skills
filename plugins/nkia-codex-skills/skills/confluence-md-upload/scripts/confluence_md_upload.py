#!/usr/bin/env python3
"""Upload Markdown to Confluence through Atlassian MCP with diagram-safe ADF sizing."""
from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib import request

MCP_URL = "https://mcp.atlassian.com/v1/mcp"
DEFAULT_CLOUD_ID = "ed55cda3-43a9-4e60-ac24-d16a8f9aa88d"
DEFAULT_SPACE_ID = "98313"  # NKIAAI


def die(message: str, code: int = 2) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def page_id_from_url(value: str | None) -> str | None:
    if not value:
        return None
    m = re.search(r"/pages/(\d+)(?:/|$)", value)
    return m.group(1) if m else value


class AtlassianMCP:
    def __init__(self, creds_path: Path | None = None) -> None:
        self.token = self._load_token(creds_path)
        self.session_id: str | None = None
        self._initialize()

    def _load_token(self, creds_path: Path | None) -> str:
        path = creds_path or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / ".credentials.json"
        if not path.exists():
            die(f"Codex credentials not found: {path}. Run: codex mcp login atlassian")
        data = json.loads(path.read_text())
        for key, value in data.items():
            if str(key).startswith("atlassian|") and isinstance(value, dict):
                token = value.get("access_token") or value.get("accessToken") or value.get("token")
                if token:
                    return token
        die("Atlassian OAuth token not found. Run: codex mcp login atlassian")

    def _post(self, payload: dict[str, Any], *, expect_session: bool = False, allow_empty: bool = False) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "Codex/confluence-md-upload",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = request.Request(MCP_URL, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=120) as resp:  # noqa: S310 - fixed HTTPS endpoint
            raw = resp.read().decode("utf-8", errors="replace")
            if expect_session:
                self.session_id = resp.headers.get("mcp-session-id") or resp.headers.get("Mcp-Session-Id")
        for line in raw.splitlines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if "error" in data:
                    die(json.dumps(data["error"], ensure_ascii=False, indent=2))
                return data.get("result", {})
        if raw.strip().startswith("{"):
            data = json.loads(raw)
            if "error" in data:
                die(json.dumps(data["error"], ensure_ascii=False, indent=2))
            return data.get("result", data)
        if allow_empty and not raw.strip():
            return {}
        die(f"Unexpected MCP response: {raw[:500]}")

    def _initialize(self) -> None:
        self._post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "confluence-md-upload", "version": "1.0"},
                },
            },
            expect_session=True,
        )
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, allow_empty=True)

    def tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._post(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        die(f"Required tool not found: {name}")
    return path


def render_mermaid_blocks(markdown: str, workdir: Path, mermaid_width: int) -> str:
    if "```mermaid" not in markdown:
        return markdown
    mmdc = require_tool("mmdc")
    tmp = Path(tempfile.mkdtemp(prefix="confluence-md-mermaid-"))
    puppeteer_cfg = tmp / "puppeteer.json"
    puppeteer_cfg.write_text(json.dumps({"args": ["--no-sandbox", "--disable-setuid-sandbox"]}), encoding="utf-8")
    counter = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        code = match.group(1).strip() + "\n"
        stem = f"mermaid-{counter:02d}"
        inp = tmp / f"{stem}.mmd"
        out = tmp / f"{stem}.svg"
        inp.write_text(code, encoding="utf-8")
        cmd = [mmdc, "-i", str(inp), "-o", str(out), "-b", "white", "--puppeteerConfigFile", str(puppeteer_cfg)]
        try:
            subprocess.run(cmd, cwd=str(workdir), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
        except subprocess.CalledProcessError as exc:
            print(exc.stderr[-2000:], file=sys.stderr)
            die(f"Mermaid render failed for {stem}")
        svg = out.read_text(encoding="utf-8")
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return f'<p><img src="data:image/svg+xml;base64,{encoded}" alt="{stem}" width="{mermaid_width}"></p>'

    return re.sub(r"```mermaid\s*\n(.*?)\n```", repl, markdown, flags=re.S)


def pandoc_to_html(markdown: str, cwd: Path) -> str:
    require_tool("pandoc")
    proc = subprocess.run(
        ["pandoc", "--from", "gfm+raw_html", "--to", "html", "--wrap=none"],
        input=markdown,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(cwd),
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        die("pandoc conversion failed")
    return proc.stdout


def embed_local_images(body: str, base_dir: Path, image_width: int) -> str:
    def repl(match: re.Match[str]) -> str:
        tag = match.group(0)
        src_m = re.search(r'\ssrc="([^"]+)"', tag)
        if not src_m:
            return tag
        src = html.unescape(src_m.group(1))
        if src.startswith(("data:", "http://", "https://")):
            return tag
        path = (base_dir / src).resolve()
        if not path.exists() or not path.is_file():
            print(f"WARN: image not found, leaving path as-is: {src}", file=sys.stderr)
            return tag
        mime = mimetypes.guess_type(str(path))[0] or ("image/svg+xml" if path.suffix.lower() == ".svg" else "application/octet-stream")
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        tag = re.sub(r'\ssrc="[^"]+"', f' src="data:{mime};base64,{data}"', tag, count=1)
        if re.search(r'\swidth="\d+"', tag):
            return tag
        return tag[:-1] + f' width="{image_width}">'

    return re.sub(r"<img\b[^>]*>", repl, body)


def parse_mcp_page(result: dict[str, Any]) -> dict[str, Any]:
    text = result.get("content", [{}])[0].get("text")
    if not text:
        die(f"MCP result has no page text: {str(result)[:300]}")
    return json.loads(text)


def svg_url_with_intrinsic_width(url: str, width: int) -> str:
    prefix = "data:image/svg+xml;base64,"
    if not isinstance(url, str) or not url.startswith(prefix):
        return url
    try:
        svg = base64.b64decode(url[len(prefix) :]).decode("utf-8", errors="replace")
    except Exception:
        return url
    m = re.search(r"<svg\b[^>]*>", svg, re.I)
    if not m:
        return url
    tag = m.group(0)
    ratio = 1.0
    vb = re.search(r'\sviewBox="([^"]+)"', tag)
    if vb:
        vals = []
        for part in re.split(r"[\s,]+", vb.group(1).strip()):
            try:
                vals.append(float(part))
            except ValueError:
                pass
        if len(vals) == 4 and vals[2]:
            ratio = vals[3] / vals[2]
    else:
        wm = re.search(r'\swidth="([0-9.]+)"', tag)
        hm = re.search(r'\sheight="([0-9.]+)"', tag)
        if wm and hm and float(wm.group(1)):
            ratio = float(hm.group(1)) / float(wm.group(1))
    height = width * ratio

    def fmt(value: float) -> str:
        value = round(value, 2)
        return str(int(value)) if abs(value - round(value)) < 0.01 else str(value).rstrip("0").rstrip(".")

    if re.search(r'\swidth="[^"]*"', tag):
        tag = re.sub(r'\swidth="[^"]*"', f' width="{fmt(width)}"', tag, count=1)
    else:
        tag = tag[:-1] + f' width="{fmt(width)}">'
    if re.search(r'\sheight="[^"]*"', tag):
        tag = re.sub(r'\sheight="[^"]*"', f' height="{fmt(height)}"', tag, count=1)
    else:
        tag = tag[:-1] + f' height="{fmt(height)}">'
    svg = svg[: m.start()] + tag + svg[m.end() :]
    return prefix + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def adjust_adf_media(adf: dict[str, Any], mermaid_width: int, image_width: int) -> dict[str, int]:
    counts = {"mediaSingle": 0, "media": 0, "mermaid": 0, "image": 0}

    def desired_width(alt: str) -> int:
        if str(alt).startswith("mermaid"):
            counts["mermaid"] += 1
            return mermaid_width
        counts["image"] += 1
        return image_width

    def child_alt(node: Any) -> str:
        if isinstance(node, dict):
            if node.get("type") == "media":
                return (node.get("attrs") or {}).get("alt", "")
            for child in node.get("content") or []:
                alt = child_alt(child)
                if alt:
                    return alt
        return ""

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "mediaSingle":
                alt = child_alt(node)
                width = mermaid_width if str(alt).startswith("mermaid") else image_width
                attrs = node.setdefault("attrs", {})
                attrs["layout"] = "center"
                attrs["width"] = width
                attrs["widthType"] = "pixel"
                counts["mediaSingle"] += 1
            if node.get("type") == "media":
                attrs = node.setdefault("attrs", {})
                width = desired_width(attrs.get("alt", ""))
                attrs["width"] = width
                if attrs.get("type") == "external" and isinstance(attrs.get("url"), str):
                    attrs["url"] = svg_url_with_intrinsic_width(attrs["url"], width)
                counts["media"] += 1
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(adf)
    return counts


def verify_page(client: AtlassianMCP, cloud_id: str, page_id: str) -> None:
    page = parse_mcp_page(
        client.tool(
            "getConfluencePage",
            {"cloudId": cloud_id, "pageId": page_id, "contentType": "page", "contentFormat": "adf"},
        )
    )
    media_single: list[dict[str, Any]] = []
    media: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "mediaSingle":
                media_single.append(node.get("attrs") or {})
            if node.get("type") == "media":
                media.append(node.get("attrs") or {})
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(page.get("body", {}))
    ms_widths: dict[Any, int] = {}
    media_widths: dict[Any, int] = {}
    for attrs in media_single:
        ms_widths[attrs.get("width")] = ms_widths.get(attrs.get("width"), 0) + 1
    for attrs in media:
        media_widths[attrs.get("width")] = media_widths.get(attrs.get("width"), 0) + 1
    print(f"page: {page.get('title')} / version {page.get('version', {}).get('number')}")
    print(f"mediaSingle: {len(media_single)} width_counts={ms_widths}")
    print(f"media: {len(media)} width_counts={media_widths}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", type=Path, help="Markdown file to upload")
    parser.add_argument("--title", help="Confluence page title")
    parser.add_argument("--page-id")
    parser.add_argument("--page-url")
    parser.add_argument("--parent-id")
    parser.add_argument("--parent-url")
    parser.add_argument("--cloud-id", default=os.environ.get("ATLASSIAN_CLOUD_ID", DEFAULT_CLOUD_ID))
    parser.add_argument("--space-id", default=os.environ.get("ATLASSIAN_SPACE_ID", DEFAULT_SPACE_ID))
    parser.add_argument("--mermaid-width", type=int, default=800)
    parser.add_argument("--image-width", type=int, default=900)
    parser.add_argument("--dry-run-html", type=Path, help="Write rendered HTML and do not upload")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    page_id = page_id_from_url(args.page_url) or args.page_id
    parent_id = page_id_from_url(args.parent_url) or args.parent_id

    if args.verify_only:
        if not page_id:
            die("--verify-only requires --page-id or --page-url")
        client = AtlassianMCP()
        verify_page(client, args.cloud_id, page_id)
        return

    if not args.markdown:
        die("--markdown is required unless --verify-only is used")
    md_path = args.markdown.resolve()
    if not md_path.exists():
        die(f"Markdown file not found: {md_path}")
    title = args.title or md_path.stem

    raw_md = md_path.read_text(encoding="utf-8")
    md = render_mermaid_blocks(raw_md, md_path.parent, args.mermaid_width)
    body = pandoc_to_html(md, md_path.parent)
    body = embed_local_images(body, md_path.parent, args.image_width)

    if args.dry_run_html:
        args.dry_run_html.write_text(body, encoding="utf-8")
        print(f"wrote {args.dry_run_html}")
        return

    client = AtlassianMCP()

    if page_id:
        result = client.tool(
            "updateConfluencePage",
            {
                "cloudId": args.cloud_id,
                "pageId": page_id,
                "title": title,
                "body": body,
                "contentType": "page",
                "contentFormat": "html",
                "versionMessage": "Upload rendered Markdown report",
            },
        )
        page = parse_mcp_page(result)
        page_id = str(page.get("id") or page_id)
    else:
        if not parent_id:
            die("Create requires --parent-id/--parent-url, or use --page-id/--page-url to update")
        result = client.tool(
            "createConfluencePage",
            {
                "cloudId": args.cloud_id,
                "spaceId": args.space_id,
                "parentId": parent_id,
                "title": title,
                "body": body,
                "contentType": "page",
                "contentFormat": "html",
            },
        )
        page = parse_mcp_page(result)
        page_id = str(page.get("id"))

    adf_page = parse_mcp_page(
        client.tool(
            "getConfluencePage",
            {"cloudId": args.cloud_id, "pageId": page_id, "contentType": "page", "contentFormat": "adf"},
        )
    )
    adf = adf_page.get("body")
    if not isinstance(adf, dict):
        die("ADF body missing after upload")
    counts = adjust_adf_media(adf, args.mermaid_width, args.image_width)
    if counts["mediaSingle"]:
        client.tool(
            "updateConfluencePage",
            {
                "cloudId": args.cloud_id,
                "pageId": page_id,
                "title": title,
                "body": json.dumps(adf, ensure_ascii=False),
                "contentType": "page",
                "contentFormat": "adf",
                "versionMessage": "Normalize diagram media widths after Markdown upload",
            },
        )

    verify_page(client, args.cloud_id, page_id)
    print(f"url: https://nkia-ai.atlassian.net/wiki/spaces/NKIAAI/pages/{page_id}")


if __name__ == "__main__":
    main()
