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
import time
import uuid
from typing import Any
from urllib import error, parse, request

MCP_URL = "https://mcp.atlassian.com/v1/mcp"
TOKEN_URL = "https://mcp.atlassian.com/v1/token"
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
                if value.get("refresh_token") and value.get("expires_at", 0) < (time.time() + 60) * 1000:
                    self._refresh(path, data, key, value)
                token = value.get("access_token") or value.get("accessToken") or value.get("token")
                if token:
                    return token
        die("Atlassian OAuth token not found. Run: codex mcp login atlassian")

    @staticmethod
    def _refresh(path: Path, data: dict[str, Any], key: str, entry: dict[str, Any]) -> None:
        """Refresh an expired access token and write it back to the Codex credential store.

        Atlassian rotates refresh tokens, so the new pair must be saved or Codex loses its login.
        """
        form = parse.urlencode(
            {"grant_type": "refresh_token", "refresh_token": entry["refresh_token"], "client_id": entry["client_id"]}
        ).encode()
        req = request.Request(TOKEN_URL, data=form, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        try:
            with request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed HTTPS endpoint
                tok = json.loads(resp.read())
        except error.HTTPError as exc:
            die(f"Atlassian token refresh failed (HTTP {exc.code}). Run: codex mcp login atlassian")
        entry["access_token"] = tok["access_token"]
        if tok.get("refresh_token"):
            entry["refresh_token"] = tok["refresh_token"]
        entry["expires_at"] = int((time.time() + int(tok.get("expires_in", 3600))) * 1000)
        data[key] = entry
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        os.chmod(tmp, 0o600)
        tmp.replace(path)

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
        ["pandoc", "--from", "gfm+raw_html-auto_identifiers", "--to", "html", "--wrap=none"],
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


def sanitize_confluence_html(body: str) -> str:
    """Remove Pandoc attributes Atlassian MCP HTML rejects.

    Confluence MCP accepts structured HTML but rejects auto-generated heading ids and
    Pandoc code/pre classes. Mermaid is rendered to images before this step, so these
    attributes are not needed for diagram fidelity.
    """
    return re.sub(r'\s(?:id|class)="[^"]*"', "", body)


def find_puppeteer() -> str:
    """Use the puppeteer bundled with mermaid-cli, which this skill already requires."""
    mmdc = Path(require_tool("mmdc")).resolve()
    for base in [mmdc.parent, *mmdc.parents]:
        cand = base / "node_modules" / "puppeteer"
        if cand.is_dir():
            return str(cand)
    die("puppeteer not found next to mmdc")
    return ""


def frames_to_gif(frames: list[dict[str, Any]], out: Path, step_ms: int, colors: int) -> None:
    """Join step screenshots into one looping GIF; every frame is padded to the largest size."""
    ffmpeg = require_tool("ffmpeg")
    w = max(f["width"] for f in frames)
    h = max(f["height"] for f in frames)
    w, h = w + w % 2, h + h % 2
    lst = out.with_suffix(".txt")
    lines = []
    for n, f in enumerate(frames):
        hold = step_ms * (2 if n == len(frames) - 1 else 1)
        lines += [f"file '{f['file']}'", f"duration {hold / 1000:.2f}"]
    lines.append(f"file '{frames[-1]['file']}'")
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    vf = (
        f"pad={w}:{h}:0:0:white,split[a][b];[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
        "[b][p]paletteuse=dither=bayer:bayer_scale=5"
    )
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", vf, "-loop", "0", str(out)],
        check=True,
        timeout=300,
    )


def render_html_report(html_path: Path, workdir: Path, args: argparse.Namespace) -> str:
    """Render HTML in headless Chrome, turn each demo into a step GIF, return a static body."""
    cfg = {
        "html": str(html_path),
        "outDir": str(workdir),
        "demoSelector": args.demo_selector,
        "captureSelector": args.demo_capture,
        "removeSelector": args.demo_remove,
        "nextText": args.demo_next_text,
        "waitMs": args.demo_wait_ms,
        "maxSteps": args.demo_max_steps,
        "width": args.render_width,
        "snapshotSelector": args.snapshot_selector,
    }
    cfg_path = workdir / "render.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    env = {**os.environ, "PUPPETEER_PATH": find_puppeteer()}
    script = Path(__file__).with_name("render_html.cjs")
    # Run with the node that installed mermaid-cli, so puppeteer matches its runtime.
    node = Path(shutil.which("mmdc") or "").parent / "node"
    node_bin = str(node) if node.is_file() else require_tool("node")
    subprocess.run([node_bin, str(script), str(cfg_path)], check=True, env=env, timeout=1800)
    demos = json.loads((workdir / "demos.json").read_text(encoding="utf-8"))
    for n, demo in enumerate(demos, 1):
        if not demo["frames"]:
            print(f"WARN: demo {n} produced no frames", file=sys.stderr)
            continue
        frames_to_gif(demo["frames"], workdir / f"demo-{n:02d}.gif", args.demo_step_ms, args.image_colors)
        print(f"demo-{n:02d}: {len(demo['frames'])} steps")
    # Figures are flat charts; a small palette keeps the page under the MCP request size limit.
    for png in sorted(workdir.glob("figure-*.png")):
        out = png.with_suffix(".p.png")
        subprocess.run(
            [require_tool("ffmpeg"), "-y", "-loglevel", "error", "-i", str(png), "-vf",
             f"split[a][b];[a]palettegen=max_colors={args.image_colors}[p];[b][p]paletteuse=dither=none", str(out)],
            check=True, timeout=120,
        )
        out.replace(png)
    return (workdir / "body.html").read_text(encoding="utf-8")


HTML_EMBED_APP = "7ab333e9-27d6-4645-8590-4b76a05b279e/04e07b35-6adc-46c6-bbd8-a58687c0270a"
HTML_EMBED_KEY = f"{HTML_EMBED_APP}/static/html-live-preview"


def html_embed_adf(html_code: str, page_id: str, version: int, account_id: str, cloud_id: str, space_id: str, space_key: str) -> dict[str, Any]:
    """ADF doc holding the whole HTML in one "Advanced HTML & Iframe Embed" (Forge) macro.

    The app renders the HTML in its own iframe, so scripts, styles and animations keep working.
    """
    local_id = str(uuid.uuid4())
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "extension",
                "attrs": {
                    "layout": "default",
                    "extensionType": "com.atlassian.ecosystem",
                    "extensionKey": HTML_EMBED_KEY,
                    "text": "Advanced HTML & Iframe Embed",
                    "parameters": {
                        "layout": "extension",
                        "guestParams": {"body": json.dumps({"htmlCode": html_code}, ensure_ascii=False)},
                        "forgeEnvironment": "PRODUCTION",
                        "embeddedMacroContext": {
                            "accountId": account_id,
                            "cloudId": cloud_id,
                            "extensionData": {
                                "type": "macro",
                                "content": {"id": page_id, "type": "page", "version": version},
                                "space": {"id": space_id, "key": space_key},
                            },
                        },
                        "localId": local_id,
                        "extensionId": f"ari:cloud:ecosystem::extension/{HTML_EMBED_KEY}",
                        "extensionTitle": "Advanced HTML & Iframe Embed",
                    },
                    "localId": local_id,
                },
            }
        ],
    }


def upload_embedded_html(client: AtlassianMCP, args: argparse.Namespace, src: Path, title: str, page_id: str | None, parent_id: str | None) -> None:
    html_code = src.read_text(encoding="utf-8")
    if not page_id:
        if not parent_id:
            die("Create requires --parent-id/--parent-url, or use --page-id/--page-url to update")
        page = parse_mcp_page(
            client.tool(
                "createConfluencePage",
                {"cloudId": args.cloud_id, "spaceId": args.space_id, "parentId": parent_id, "title": title,
                 "body": "<p>HTML</p>", "contentType": "page", "contentFormat": "html"},
            )
        )
        page_id = str(page.get("id"))
    current = parse_mcp_page(
        client.tool("getConfluencePage", {"cloudId": args.cloud_id, "pageId": page_id, "contentType": "page", "contentFormat": "adf"})
    )
    version = int(current.get("version", {}).get("number", 1)) + 1
    account = json.loads(client.tool("atlassianUserInfo", {})["content"][0]["text"])["account_id"]
    doc = html_embed_adf(html_code, page_id, version, account, args.cloud_id, args.space_id, args.space_key)
    parse_mcp_page(
        client.tool(
            "updateConfluencePage",
            {"cloudId": args.cloud_id, "pageId": page_id, "title": title, "body": json.dumps(doc, ensure_ascii=False),
             "contentType": "page", "contentFormat": "adf", "versionMessage": "Embed HTML report"},
        )
    )
    page = parse_mcp_page(
        client.tool("getConfluencePage", {"cloudId": args.cloud_id, "pageId": page_id, "contentType": "page", "contentFormat": "adf"})
    )
    body = page.get("body")
    body = json.loads(body) if isinstance(body, str) else body
    stored = [n for n in body.get("content", []) if n.get("type") == "extension"]
    size = len(json.loads(stored[0]["attrs"]["parameters"]["guestParams"]["body"])["htmlCode"]) if stored else 0
    print(f"page: {page.get('title')} / version {page.get('version', {}).get('number')}")
    print(f"embedded html: {size} chars (source {len(html_code)})")
    print(f"url: https://nkia-ai.atlassian.net/wiki/spaces/NKIAAI/pages/{page_id}")


EXPAND_OPEN = "[[EXPAND-OPEN]]"
EXPAND_CLOSE = "[[EXPAND-CLOSE]]"


def adf_text(node: dict[str, Any]) -> str:
    return "".join(c.get("text", "") for c in node.get("content") or [] if isinstance(c, dict))


def fold_expands(adf: dict[str, Any], flatten: bool = False) -> int:
    """Turn marker paragraphs left by render_html.cjs into ADF expand nodes.

    With flatten=True the markers become a bold title line instead (fallback when
    Confluence rejects an expand's content).
    """
    folded = 0
    root: list[Any] = []
    stack: list[tuple[list[Any], dict[str, Any] | None]] = [(root, None)]
    for node in adf.get("content") or []:
        text = adf_text(node) if isinstance(node, dict) and node.get("type") == "paragraph" else ""
        if text.startswith(EXPAND_OPEN):
            title = text[len(EXPAND_OPEN):].strip()
            if flatten:
                stack[-1][0].append({"type": "paragraph", "content": [{"type": "text", "text": title, "marks": [{"type": "strong"}]}]})
                continue
            exp = {"type": "expand", "attrs": {"title": title}, "content": []}
            stack.append((exp["content"], exp))
            continue
        if text == EXPAND_CLOSE:
            if flatten or len(stack) == 1:
                continue
            content, exp = stack.pop()
            if not content:
                content.append({"type": "paragraph"})
            stack[-1][0].append(exp)
            folded += 1
            continue
        stack[-1][0].append(node)
    while len(stack) > 1:
        content, exp = stack.pop()
        stack[-1][0].append(exp)
        folded += 1
    adf["content"] = root
    return folded


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
    page = json.loads(text)
    if isinstance(page, dict) and page.get("error"):
        die(page.get("message") or json.dumps(page, ensure_ascii=False))
    return page


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
    parser.add_argument("--html", type=Path, help="HTML report to upload (rendered in headless Chrome; demos become step GIFs)")
    parser.add_argument("--embed-html", type=Path, help="HTML file shown as-is in an Advanced HTML & Iframe Embed macro (scripts and animations keep working)")
    parser.add_argument("--space-key", default=os.environ.get("ATLASSIAN_SPACE_KEY", "NKIAAI"))
    parser.add_argument("--demo-selector", default=".demo", help="HTML mode: interactive demo container")
    parser.add_argument("--demo-capture", default=".stage,.say", help="HTML mode: parts of a demo to capture (whole demo if none match)")
    parser.add_argument("--demo-remove", default=".ctrl", help="HTML mode: demo parts dropped from the page (controls)")
    parser.add_argument("--demo-next-text", default="다음", help="HTML mode: label of the demo's next-step button")
    parser.add_argument("--demo-wait-ms", type=int, default=1500, help="HTML mode: wait after each step for transitions")
    parser.add_argument("--demo-step-ms", type=int, default=2500, help="HTML mode: GIF frame duration")
    parser.add_argument("--demo-max-steps", type=int, default=40)
    parser.add_argument("--render-width", type=int, default=1200, help="HTML mode: browser viewport width")
    parser.add_argument("--image-colors", type=int, default=64, help="HTML mode: palette size for GIFs and figure PNGs")
    parser.add_argument("--snapshot-selector", default=".figure,[role=img],svg,canvas", help="HTML mode: drawn figures outside demos saved as still images")
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

    if args.embed_html:
        src = args.embed_html.resolve()
        if not src.exists():
            die(f"HTML file not found: {src}")
        upload_embedded_html(AtlassianMCP(), args, src, args.title or src.stem, page_id, parent_id)
        return

    if bool(args.markdown) == bool(args.html):
        die("Give exactly one of --markdown or --html unless --verify-only is used")
    src_path = (args.markdown or args.html).resolve()
    if not src_path.exists():
        die(f"Source file not found: {src_path}")
    title = args.title or src_path.stem

    if args.html:
        workdir = Path(tempfile.mkdtemp(prefix="confluence-html-"))
        body = render_html_report(src_path, workdir, args)
        body = embed_local_images(body, workdir, args.image_width)
    else:
        raw_md = src_path.read_text(encoding="utf-8")
        md = render_mermaid_blocks(raw_md, src_path.parent, args.mermaid_width)
        body = pandoc_to_html(md, src_path.parent)
        body = sanitize_confluence_html(body)
        body = embed_local_images(body, src_path.parent, args.image_width)

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
    expands = fold_expands(json.loads(json.dumps(adf))) if args.html else 0
    if counts["mediaSingle"] or expands:
        def push(doc: dict[str, Any]) -> dict[str, Any]:
            return client.tool(
                "updateConfluencePage",
                {
                    "cloudId": args.cloud_id,
                    "pageId": page_id,
                    "title": title,
                    "body": json.dumps(doc, ensure_ascii=False),
                    "contentType": "page",
                    "contentFormat": "adf",
                    "versionMessage": "Normalize media widths and fold toggles after upload",
                },
            )

        if expands:
            folded = json.loads(json.dumps(adf))
            fold_expands(folded)
            try:
                parse_mcp_page(push(folded))
                print(f"expand: {expands}")
            except SystemExit:
                print("WARN: Confluence rejected expands; toggles kept as bold titles", file=sys.stderr)
                fold_expands(adf, flatten=True)
                parse_mcp_page(push(adf))
        else:
            push(adf)

    verify_page(client, args.cloud_id, page_id)
    print(f"url: https://nkia-ai.atlassian.net/wiki/spaces/NKIAAI/pages/{page_id}")


if __name__ == "__main__":
    main()
