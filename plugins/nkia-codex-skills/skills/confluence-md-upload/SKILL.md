---
name: confluence-md-upload
description: Upload Markdown reports to Confluence as rendered pages, preserving Mermaid/SVG diagrams and Markdown-preview-like formatting. Use when a user gives a .md report and asks to publish it to Confluence, especially when diagrams must remain visible, colored, centered, and correctly sized instead of raw Markdown or broken/oversized images.
---

# Confluence MD Upload

Publish a Markdown report to Confluence so it looks like a rendered Markdown preview, not raw Markdown.

## Core Rule

Use the bundled script first:

```bash
python3 /home/jhjang/nkia-codex-skills/plugins/nkia-codex-skills/skills/confluence-md-upload/scripts/confluence_md_upload.py \
  --markdown /path/to/report.md \
  --parent-url 'https://nkia-ai.atlassian.net/wiki/spaces/NKIAAI/pages/198443011/' \
  --title 'Report title'
```

For existing pages:

```bash
python3 /home/jhjang/nkia-codex-skills/plugins/nkia-codex-skills/skills/confluence-md-upload/scripts/confluence_md_upload.py \
  --markdown /path/to/report.md \
  --page-url 'https://nkia-ai.atlassian.net/wiki/spaces/NKIAAI/pages/201719809/...' \
  --title 'Report title'
```

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
python3 /home/jhjang/nkia-codex-skills/plugins/nkia-codex-skills/skills/confluence-md-upload/scripts/confluence_md_upload.py \
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

If Codex lacks Atlassian OAuth credentials, run `codex mcp login atlassian` first, then retry.
