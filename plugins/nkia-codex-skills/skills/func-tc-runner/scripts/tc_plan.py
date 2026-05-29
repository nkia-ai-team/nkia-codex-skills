#!/usr/bin/env python3
"""Parse functional TC markdown files into an execution plan summary."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TC_RE = re.compile(r"^###\s+([A-Z]+-\d+)\s+-\s+(.+)$", re.MULTILINE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tc_path", help="TC markdown file or directory")
    parser.add_argument("--json", dest="json_path", help="write JSON plan to this path")
    args = parser.parse_args()

    root = Path(args.tc_path)
    files = [root] if root.is_file() else sorted(root.glob("*.md"))
    tests: list[dict[str, Any]] = []

    for path in files:
        if path.name.upper() == "INDEX.MD" or path.name == "tc-test.config.json":
            continue
        text = path.read_text(encoding="utf-8")
        matches = list(TC_RE.finditer(text))
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            section = text[start:end]
            tc_id = match.group(1)
            title = match.group(2).strip()
            tests.append(
                {
                    "feature_file": str(path),
                    "feature": path.stem,
                    "id": f"{path.stem}/{tc_id}",
                    "tc_id": tc_id,
                    "title": title,
                    "type": find_value(section, "유형") or infer_type(tc_id),
                    "target": find_value(section, "자동화 대상"),
                    "status": find_value(section, "자동화 상태"),
                    "lane": infer_lane(tc_id, section),
                    "ready": "자동화 상태: Ready" in section,
                    "source_gap": "source gap" in section.casefold() or "소스 갭" in section,
                }
            )

    summary = {
        "total": len(tests),
        "by_lane": count_by(tests, "lane"),
        "by_status": count_by(tests, "status"),
        "ready": sum(1 for test in tests if test["ready"]),
        "tests": tests,
    }

    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def find_value(section: str, label: str) -> str | None:
    match = re.search(rf"^-\s+{re.escape(label)}:\s*(.+)$", section, re.MULTILINE)
    return match.group(1).strip() if match else None


def infer_type(tc_id: str) -> str:
    if tc_id.startswith("UI-"):
        return "UI"
    if tc_id.startswith("API-"):
        return "API"
    if tc_id.startswith("INT-"):
        return "Integration"
    if tc_id.startswith("TIMING-"):
        return "Timing"
    return "Auxiliary"


def infer_lane(tc_id: str, section: str) -> str:
    target = (find_value(section, "자동화 대상") or "").casefold()
    tc_type = (find_value(section, "유형") or infer_type(tc_id)).casefold()
    if any(token in target for token in ("mockmvc", "junit", "pytest", "vitest", "jest rtl", "jest")):
        return "blocked"
    if "playwright" in target:
        lowered = section.casefold()
        if "network" in lowered or "api log" in lowered or "mongodb" in lowered or "ui-api" in lowered:
            return "ui-api"
        return "ui"
    if "curl" in target:
        return "api"
    if tc_id.startswith("API-"):
        return "api"
    if "timing" in tc_type:
        return "ui"
    if tc_id.startswith("UI-"):
        return "ui"
    if tc_id.startswith("INT-"):
        return "ui-api"
    return "blocked"


def count_by(tests: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for test in tests:
        value = test.get(key) or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
