---
name: confluence-md-upload
description: Upload Markdown or HTML reports to Confluence. HTML reports (including claude.ai artifacts) are shown as-is in an Advanced HTML & Iframe Embed macro so scripts and animations keep working; Markdown is rendered with Mermaid/SVG diagrams preserved and correctly sized. Use when a user gives a .md or .html report and asks to publish it to Confluence.
---

# Confluence MD Upload

Publish a report to Confluence.

## Core Rule

**HTML reports go up as HTML, as-is** (`--embed-html`, next section). This is the team default:
the page shows the original HTML with its styles, toggles and animations.
Do not convert an HTML report to Markdown or to native Confluence content unless the user asks.

Markdown reports use the bundled script with `--markdown`:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/confluence-md-upload/scripts/confluence_md_upload.py" \
  --markdown /path/to/report.md \
  --parent-url 'https://nkia-ai.atlassian.net/wiki/spaces/NKIAAI/pages/198443011/' \
  --title 'Report title'
```

For existing pages:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/confluence-md-upload/scripts/confluence_md_upload.py" \
  --markdown /path/to/report.md \
  --page-url 'https://nkia-ai.atlassian.net/wiki/spaces/NKIAAI/pages/201719809/...' \
  --title 'Report title'
```

## HTML Reports As-Is (`--embed-html`) — default for HTML

For an HTML report (for example a claude.ai artifact), put the whole file into one
"Advanced HTML & Iframe Embed" macro (Forge app installed on nkia-ai). Scripts, styles, toggles and
animations keep working because the app renders the HTML in its own iframe:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/confluence-md-upload/scripts/confluence_md_upload.py" \
  --embed-html /path/to/report.html \
  --parent-id 250314753 \
  --title 'Report title'
```

- Give a complete HTML document (`<!doctype html>`, `<head>`, styles inline). External scripts must be on public CDNs.
- `--parent-id` may be a folder id. Use `--page-id`/`--page-url` to replace an existing page.
- The script re-reads the page and prints the stored HTML size; it must equal the source size.
- The HTML is stored as the macro's parameter inside the page body (page history keeps each version),
  not as a file attachment. Viewers see it rendered by the app in an iframe.
- Page text is not searchable in Confluence search (it lives in the macro parameters).
- Size: a 790 KB HTML page works. Inline images as data URIs count toward it.

## HTML Converted To Confluence Content (`--html`)

Use only when the page must be native Confluence content (searchable, editable).

Confluence strips scripts and styles, so the script renders the page in headless Chrome first:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/confluence-md-upload/scripts/confluence_md_upload.py" \
  --html /path/to/report.html \
  --parent-id 250314753 \
  --title 'Report title'
```

What it does:

1. Opens every `<details>` and runs the page's scripts (charts and tables built by JS are included).
2. Each interactive demo (`--demo-selector`, default `.demo`) is stepped with its next button
   (`--demo-next-text`, default `다음`). The visual parts (`--demo-capture`, default `.stage,.say`) are
   captured per step and joined into one looping GIF (`--demo-step-ms`, default 2500 per frame).
   Controls (`--demo-remove`, default `.ctrl`) are hidden. Text around the demo stays as text.
3. Drawn figures outside demos (`--snapshot-selector`, default `.figure,[role=img],svg,canvas`) become PNG images.
4. Layout wrappers and styling attributes are removed; headings, paragraphs, lists, tables and links stay.
5. Block-level `<details>` become Confluence expand macros. Toggles nested in another toggle, a list or a
   table become a bold title line followed by their content (ADF does not allow those as expands).
   If Confluence rejects the expands, the page falls back to bold title lines.

Check with `--dry-run-html out.html` first: it renders and writes the body without uploading.
The temp work dir (GIFs, PNGs) is printed under `/tmp/confluence-html-*`.

Requirements: `mmdc` (its bundled puppeteer and node are reused) and `ffmpeg`.
Keep `TMPDIR` short or unset: Chrome fails to start when its temp path is too long.

## Why This Script Exists

Confluence does not render Markdown/SVG like local preview by default.

Known failure modes:

- Raw Markdown uploaded literally.
- Mermaid fences appear as code, not diagrams.
- Relative SVG/image paths break.
- SVG colors become black if Mermaid CSS/id/style are stripped.
- `<img width>` changes appear to do nothing because Confluence ADF stores the real visible width on the parent `mediaSingle` node.

The script handles these by:

1. Rendering Mermaid fences to SVG with `mmdc`.
2. Converting Markdown to HTML with `pandoc`.
3. Embedding local images/SVGs as data URIs.
4. Uploading through Atlassian MCP using Codex OAuth credentials.
5. Re-reading the page as ADF.
6. Setting both `mediaSingle.attrs.width` and `media.attrs.width`.
7. Rewriting SVG intrinsic `<svg width height>` while preserving `viewBox`, CSS, colors, and internal ids/classes.
8. Re-uploading ADF so Confluence viewer uses the intended size.

## Required Inputs

Need either:

- `--page-url` or `--page-id` to update an existing page; or
- `--parent-url`/`--parent-id`, `--space-id`, and `--title` to create a child page.

NKIA defaults:

- cloud id: `ed55cda3-43a9-4e60-ac24-d16a8f9aa88d`
- NKIAAI space id: `98313`

Override with `--cloud-id` and `--space-id` if publishing elsewhere.

## Sizing Defaults

Use these defaults unless the user asks otherwise:

- Mermaid/process diagrams: `--mermaid-width 800`
- Topology/result diagrams and other images: `--image-width 900`

If the page looks too large/small, rerun the same command with adjusted widths. Always adjust ADF parent width, not only `<img width>`.

## Verification

After upload, verify with:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/confluence-md-upload/scripts/confluence_md_upload.py" \
  --verify-only \
  --page-url '<page-url>'
```

Expected evidence:

- version number increased;
- `mediaSingle` count equals diagram/image count;
- no stale oversized `mediaSingle.width` remains;
- Mermaid SVG data still contains `<style>` and is not stripped.

If a browser tab still shows the old page, tell the user to hard refresh (`Ctrl+Shift+R`). Do not assume upload failed until ADF verification is checked.

## Fallbacks

If `mmdc` is unavailable, install or use an existing generated SVG artifact before upload. Do not upload Mermaid fences as raw code when the user wants diagrams preserved.

An expired access token is refreshed automatically with the stored refresh token, and the new pair is written
back to `~/.codex/.credentials.json`. If the refresh fails (HTTP 403) or credentials are missing, run
`codex mcp login atlassian` first, then retry.
