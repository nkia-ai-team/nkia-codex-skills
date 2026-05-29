#!/usr/bin/env python3
"""Lightweight validation for functional TC markdown files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTION_GROUPS = [
    ("In Scope", "테스트 범위"),
    ("Out of Scope", "제외 범위"),
    ("Coverage Design", "커버리지 설계"),
    ("Traceability", "추적성"),
]

FORBIDDEN_SCORE_TERMS = [
    "ragas",
    "faithfulness",
    "semantic score",
    "similarity score",
    "answer quality score",
    "llm quality",
]

EXECUTION_STATUSES = ["실행 가능", "부분 실행 가능", "설계 기반"]

AUTOMATION_READY_MARKERS = [
    "자동화 준비도",
    "자동화 상태",
    "소스 근거",
    "자동화 구현",
    "Fixture",
    "Cleanup",
    "Assertion",
]

STRICT_DOC_MARKERS = [
    ("coverage design section", "커버리지 설계"),
    ("coverage tier", "커버리지 티어"),
    ("target TC count", "목표 TC 수"),
    ("actual TC count", "실제 TC 수"),
    ("coverage axis", "커버리지 축"),
    ("automation readiness section", "자동화 준비도"),
    ("live environment contract", "실행 환경 계약"),
    ("runner command", "권장 실행 명령"),
    ("auth/permission setup", "인증/권한"),
    ("fixture or seed", "Fixture"),
    ("cleanup", "Cleanup"),
    ("source evidence", "Source Evidence"),
]

VAGUE_READY_ASSERTION_PATTERNS = [
    r"HTTP\s+4xx",
    r"HTTP\s+\dxx",
    r"또는\s+AP\s+공통",
    r"또는\s+not\s+found",
    r"또는\s+권한",
    r"구현\s+확인\s+필요",
]

MOCK_TARGET_PATTERNS = [
    r"자동화 대상:\s*(?:MockMvc|JUnit|pytest|Vitest|Jest RTL)",
    r"Cleanup:\s*mock-only",
    r"Fixture/Seed:\s*.*mock",
]

SOURCE_LINE_RE = re.compile(
    r"[\w./-]+\.(?:java|kt|ts|tsx|js|jsx|py|md):\d+"
)

COVERAGE_AXES = [
    "Core positive",
    "Server validation",
    "Boundary / edge",
    "Permission / ownership",
    "UI state",
    "Integration contract",
    "Persistence / cleanup",
    "Timing",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require automation-ready markers for new executable TC documents",
    )
    parser.add_argument("file")
    args = parser.parse_args()

    path = Path(args.file)
    if path.name.upper() == "INDEX.MD":
        print(f"SKIP: {path}")
        return 0

    text = path.read_text(encoding="utf-8")
    warnings: list[str] = []

    for sections in REQUIRED_SECTION_GROUPS:
        if not any(re.search(rf"^#+\s+{re.escape(section)}\s*$", text, re.MULTILINE) for section in sections):
            warnings.append(f"missing section: {' / '.join(sections)}")

    if "Expected pass/fail" not in text and "Expected Result" not in text and "기대 결과" not in text:
        warnings.append("missing expected pass/fail or expected result marker")

    if "실행 상태" not in text:
        warnings.append("missing execution status metadata")
    elif not any(status in text for status in EXECUTION_STATUSES):
        warnings.append("execution status should be one of: " + ", ".join(EXECUTION_STATUSES))

    if "Evidence" not in text and "증빙" not in text:
        warnings.append("missing evidence marker")

    if "Timing" in text and "threshold" not in text.casefold():
        warnings.append("timing cases should include an explicit threshold")

    lowered = text.casefold()
    for term in FORBIDDEN_SCORE_TERMS:
        if term in lowered:
            warnings.append(f"possible score-based LLM evaluation term: {term}")

    tc_headings = re.findall(r"^###\s+([A-Z]+-\d+)\b", text, re.MULTILINE)
    if len(tc_headings) != len(set(tc_headings)):
        warnings.append("duplicate TC IDs found")

    tc_sections = list(re.finditer(r"^###\s+([A-Z]+-\d+)\b.*$", text, re.MULTILINE))
    api_sections = [match for match in tc_sections if match.group(1).startswith("API-")]
    for match in api_sections:
        section = section_text(text, tc_sections, match)
        for marker in ("메서드", "경로", "요청", "응답"):
            if marker not in section:
                warnings.append(f"{match.group(0)} missing API marker: {marker}")

    if re.search(r"query_itg_mongo\s+또는|또는\s+POST\s+/api", text):
        warnings.append("possible mixed API layers in one TC; split service/tool and public API endpoint cases")

    if args.strict:
        validate_strict(text, tc_sections, warnings)

    if warnings:
        for warning in warnings:
            print(f"WARN: {warning}")
        return 1

    print(f"OK: {path}")
    return 0


def section_text(text: str, sections: list[re.Match[str]], match: re.Match[str]) -> str:
    idx = sections.index(match)
    end = sections[idx + 1].start() if idx + 1 < len(sections) else len(text)
    return text[match.start():end]


def validate_strict(text: str, tc_sections: list[re.Match[str]], warnings: list[str]) -> None:
    for label, marker in STRICT_DOC_MARKERS:
        if marker not in text:
            warnings.append(f"strict: missing {label} marker: {marker}")

    execution_status_line = next(
        (line for line in text.splitlines() if "| 실행 상태 |" in line),
        "",
    )
    if "실행 가능" in execution_status_line and not SOURCE_LINE_RE.search(text):
        warnings.append("strict: executable documents should cite at least one source path with line number")

    for marker in AUTOMATION_READY_MARKERS:
        if marker not in text:
            warnings.append(f"strict: missing automation-ready marker: {marker}")

    for axis in COVERAGE_AXES:
        if axis not in text:
            warnings.append(f"strict: missing coverage axis: {axis}")

    validate_tc_density(text, tc_sections, warnings)

    for match in tc_sections:
        tc_id = match.group(1)
        section = section_text(text, tc_sections, match)
        for marker in ("자동화 상태", "소스 근거", "자동화 구현"):
            if marker not in section:
                warnings.append(f"strict: {tc_id} missing marker: {marker}")

        if "자동화 상태: Ready" in section:
            if not SOURCE_LINE_RE.search(section):
                warnings.append(f"strict: {tc_id} Ready case missing source path:line evidence")
            for required in ("Fixture", "Cleanup", "Assertion"):
                if required not in section:
                    warnings.append(f"strict: {tc_id} Ready case missing automation implementation field: {required}")
            for pattern in VAGUE_READY_ASSERTION_PATTERNS:
                if re.search(pattern, section, re.IGNORECASE):
                    warnings.append(f"strict: {tc_id} Ready case has vague assertion pattern: {pattern}")
            for pattern in MOCK_TARGET_PATTERNS:
                if re.search(pattern, section, re.IGNORECASE):
                    warnings.append(f"strict: {tc_id} Ready case must be live-E2E, not mock/unit target: {pattern}")
            if (
                any(word in section for word in ("생성", "수정", "삭제", "업로드", "저장", "create", "update", "delete", "upload"))
                and "MongoDB" not in section
                and "Mongo" not in section
            ):
                warnings.append(f"strict: {tc_id} mutating Ready case should include MongoDB/state consistency evidence")


def validate_tc_density(text: str, tc_sections: list[re.Match[str]], warnings: list[str]) -> None:
    tier_line = next((line for line in text.splitlines() if "| 커버리지 티어 |" in line), "")
    tc_count = len(tc_sections)
    if not tier_line:
        return

    tier = None
    for candidate in ("Simple", "Standard", "Complex", "Design target"):
        if candidate in tier_line:
            tier = candidate
            break
    if tier is None:
        warnings.append("strict: coverage tier should be Simple, Standard, Complex, or Design target")
        return

    ranges = {
        "Simple": (4, 6),
        "Standard": (7, 10),
        "Complex": (9, 12),
        "Design target": (4, 7),
    }
    lower, upper = ranges[tier]

    executable_line = next((line for line in text.splitlines() if "| 실행 상태 |" in line), "")
    executable = "실행 가능" in executable_line or "부분 실행 가능" in executable_line
    gap_allowed = "source gap" in text.casefold() or "소스 갭" in text

    if tc_count < lower and executable and not gap_allowed:
        warnings.append(
            f"strict: {tier} executable document has too few TC ({tc_count}); expected at least {lower}"
        )
    if tc_count > upper and "exhaustive" not in text.casefold() and "초과 사유" not in text:
        warnings.append(
            f"strict: {tier} document has too many TC ({tc_count}); expected at most {upper} without an explicit reason"
        )


if __name__ == "__main__":
    raise SystemExit(main())
