#!/usr/bin/env python3
"""Filter a Google Sheet CSV/TSV export to rows assigned to an owner."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Iterable


OWNER_COLUMNS = [
    "owner",
    "assignee",
    "담당자",
    "담당",
    "개발자",
    "작업자",
]


def read_text(source: str) -> str:
    if source.startswith(("http://", "https://")):
        source = to_csv_export_url(source)
        with urllib.request.urlopen(source, timeout=20) as response:
            return response.read().decode("utf-8-sig")
    return Path(source).read_text(encoding="utf-8-sig")


def to_csv_export_url(url: str) -> str:
    match = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not match:
        return url
    sheet_id = match.group(1)
    gid_match = re.search(r"(?:[?#&]gid=)(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def sniff_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample[:4096], delimiters=",\t")
    except csv.Error:
        return csv.excel


def norm(value: object) -> str:
    return str(value or "").strip().casefold()


def owner_matches(row: dict[str, str], owner: str, columns: Iterable[str]) -> bool:
    expected = norm(owner)
    for column in columns:
        for actual_key, value in row.items():
            if norm(actual_key) == norm(column) and expected in norm(value):
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="CSV/TSV file path or exported sheet URL")
    parser.add_argument("--owner", required=True, help="Owner/assignee value to match")
    parser.add_argument(
        "--owner-column",
        action="append",
        default=[],
        help="Additional owner column name; can be repeated",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    text = read_text(args.source)
    dialect = sniff_dialect(text)
    rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
    owner_columns = [*OWNER_COLUMNS, *args.owner_column]
    filtered = [row for row in rows if owner_matches(row, args.owner, owner_columns)]

    json.dump(
        {"owner": args.owner, "count": len(filtered), "rows": filtered},
        sys.stdout,
        ensure_ascii=False,
        indent=2 if args.pretty else None,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
