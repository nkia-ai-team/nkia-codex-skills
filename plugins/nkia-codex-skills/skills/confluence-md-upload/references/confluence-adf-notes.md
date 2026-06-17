# Confluence ADF Image Notes

Confluence page view uses Atlassian Document Format (ADF), not raw HTML.

For external/data images, Confluence stores width in two places:

```json
{
  "type": "mediaSingle",
  "attrs": {"layout": "center", "width": 900, "widthType": "pixel"},
  "content": [{"type": "media", "attrs": {"type": "external", "url": "data:image/svg+xml;base64,...", "width": 900}}]
}
```

If only `<img width="900">` is changed in HTML, Confluence may retain `mediaSingle.attrs.width = 1600`, so the visible viewer stays oversized.

Correct fix:

1. Upload rendered HTML.
2. Fetch page as `contentFormat=adf`.
3. Traverse all `mediaSingle` + child `media` nodes.
4. Set parent and child widths to the same intended pixel value.
5. For SVG data URIs, also set intrinsic root `<svg width height>` while preserving `viewBox`, `<style>`, `id`, `class`, and inline colors.
6. Update page with `contentFormat=adf`.
