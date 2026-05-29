#!/usr/bin/env python3
"""Run a functional test manifest concurrently and collect evidence."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HTTP_STATUS_RE = re.compile(r"^\d{3}$")


@dataclass
class TestResult:
    id: str
    title: str
    lane: str
    status: str
    duration_s: float
    exit_code: int | None
    stdout_path: str
    stderr_path: str
    failures: list[str]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-workers", type=int, default=6)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "stdout").mkdir(exist_ok=True)
    (output_dir / "stderr").mkdir(exist_ok=True)

    tests = manifest.get("tests", [])
    results: list[TestResult] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_map = {
            executor.submit(run_one, test, output_dir): test
            for test in tests
            if not test.get("skip")
        }
        for future in concurrent.futures.as_completed(future_map):
            results.append(future.result())

    skipped = [
        TestResult(
            id=test.get("id", "unknown"),
            title=test.get("title", ""),
            lane=test.get("lane", "unknown"),
            status=test.get("skip_status", "SKIPPED"),
            duration_s=0.0,
            exit_code=None,
            stdout_path="",
            stderr_path="",
            failures=[test.get("skip_reason", "marked skip")],
        )
        for test in tests
        if test.get("skip")
    ]
    results.extend(skipped)
    results.sort(key=lambda item: item.id)

    write_results(output_dir, manifest, results)
    unclean = [result for result in results if result.status in {"FAIL", "BLOCKED", "INFRA"}]
    return 1 if unclean else 0


def run_one(test: dict[str, Any], output_dir: Path) -> TestResult:
    test_id = test.get("id", "unknown")
    lane = test.get("lane", "unknown")
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", test_id)
    stdout_path = output_dir / "stdout" / f"{safe_id}.out"
    stderr_path = output_dir / "stderr" / f"{safe_id}.err"
    start = time.monotonic()
    failures: list[str] = []

    command = test.get("command")
    if not command:
        return TestResult(test_id, test.get("title", ""), lane, "BLOCKED", 0.0, None, str(stdout_path), str(stderr_path), ["missing command"])

    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in test.get("env", {}).items()})
    timeout = int(test.get("timeout", 60))
    cwd = test.get("cwd")

    try:
        completed = subprocess.run(
            command,
            shell=isinstance(command, str),
            cwd=cwd,
            env=env,
            timeout=timeout,
            text=True,
            capture_output=True,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nTIMEOUT after {timeout}s\n"
        exit_code = None
        failures.append(f"timeout after {timeout}s")

    stdout_path.write_text(redact(stdout), encoding="utf-8")
    stderr_path.write_text(redact(stderr), encoding="utf-8")

    expect = test.get("expect", {})
    expected_exit = expect.get("exit_code", 0)
    if exit_code != expected_exit:
        failures.append(f"exit_code expected {expected_exit}, got {exit_code}")

    body, http_status = split_http_status(stdout)
    if "http_status" in expect and http_status != int(expect["http_status"]):
        failures.append(f"http_status expected {expect['http_status']}, got {http_status}")

    for needle in expect.get("stdout_contains", []):
        if needle not in stdout:
            failures.append(f"stdout missing: {needle}")
    for needle in expect.get("stdout_not_contains", []):
        if needle in stdout:
            failures.append(f"stdout should not contain: {needle}")
    for needle in expect.get("stderr_not_contains", []):
        if needle in stderr:
            failures.append(f"stderr should not contain: {needle}")

    if expect.get("json"):
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            failures.append(f"response body is not JSON: {exc}")
            data = None
        if data is not None:
            for assertion in expect["json"]:
                failures.extend(check_json_assertion(data, assertion))

    duration = time.monotonic() - start
    status = "FAIL" if failures else "PASS"
    return TestResult(test_id, test.get("title", ""), lane, status, duration, exit_code, str(stdout_path), str(stderr_path), failures)


def split_http_status(stdout: str) -> tuple[str, int | None]:
    lines = stdout.rstrip("\n").splitlines()
    if lines and HTTP_STATUS_RE.match(lines[-1].strip()):
        return "\n".join(lines[:-1]), int(lines[-1].strip())
    return stdout, None


def check_json_assertion(data: Any, assertion: dict[str, Any]) -> list[str]:
    path = assertion.get("path")
    if not path:
        return ["json assertion missing path"]
    exists, value = get_path(data, path)
    failures: list[str] = []
    if assertion.get("exists") is True and not exists:
        failures.append(f"json path missing: {path}")
    if "equals" in assertion:
        if not exists:
            failures.append(f"json path missing: {path}")
        elif value != assertion["equals"]:
            failures.append(f"json {path} expected {assertion['equals']!r}, got {value!r}")
    if "contains" in assertion:
        if not exists or assertion["contains"] not in value:
            failures.append(f"json {path} does not contain {assertion['contains']!r}")
    return failures


def get_path(data: Any, path: str) -> tuple[bool, Any]:
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
            continue
        if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
            continue
        return False, None
    return True, cur


def redact(text: str) -> str:
    text = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <REDACTED>", text)
    text = re.sub(r"(?i)(password['\"]?\s*[:=]\s*['\"])[^'\"]+", r"\1<REDACTED>", text)
    return text


def write_results(output_dir: Path, manifest: dict[str, Any], results: list[TestResult]) -> None:
    serializable = serialize_results(results)
    counts, by_lane = summarize_results(results)
    score = score_results(results)

    payload = {
        "run_id": manifest.get("run_id"),
        "counts": counts,
        "by_lane": by_lane,
        "score": score,
        "results": serializable,
    }
    (output_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "report.md").write_text(render_report(str(manifest.get("run_id", "unknown")), results) + "\n", encoding="utf-8")
    write_document_reports(output_dir, manifest, results)


def serialize_results(results: list[TestResult]) -> list[dict[str, Any]]:
    return [
        {
            "id": result.id,
            "title": result.title,
            "tc_document": tc_document_id(result.id),
            "lane": result.lane,
            "status": result.status,
            "duration_s": round(result.duration_s, 3),
            "exit_code": result.exit_code,
            "stdout_path": result.stdout_path,
            "stderr_path": result.stderr_path,
            "failures": result.failures,
        }
        for result in results
    ]


def summarize_results(results: list[TestResult]) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    counts: dict[str, int] = {}
    by_lane: dict[str, dict[str, int]] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
        lane_counts = by_lane.setdefault(result.lane, {})
        lane_counts[result.status] = lane_counts.get(result.status, 0) + 1
    return counts, by_lane


def score_results(results: list[TestResult]) -> dict[str, Any]:
    counts, _ = summarize_results(results)
    total = len(results)
    passed = counts.get("PASS", 0)
    failed = counts.get("FAIL", 0)
    blocked = counts.get("BLOCKED", 0)
    skipped = counts.get("SKIPPED", 0)
    infra = counts.get("INFRA", 0)
    # INFRA = runner/infra failure (worker crash, quota, auth, connection), NOT a product
    # FAIL. It is deliberately excluded from `executed` so it cannot pollute the executed
    # pass rate; it counts as not-executed alongside BLOCKED/SKIPPED.
    executed = passed + failed
    not_executed = total - executed
    return {
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "skipped": skipped,
        "infra_cases": infra,
        "executed_cases": executed,
        "not_executed_cases": not_executed,
        "execution_coverage_percent": percent(executed, total),
        "pass_rate_total_percent": percent(passed, total),
        "pass_rate_executed_percent": percent(passed, executed),
    }


def percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


STATUS_EMOJI = {"PASS": "✅", "FAIL": "❌", "BLOCKED": "⛔", "SKIPPED": "⏭️", "INFRA": "🔧"}


def status_badge(status: str) -> str:
    return f"{STATUS_EMOJI.get(status, '•')} {status}"


def format_duration(duration_s: float) -> str:
    """Render a measured duration, or '—' when it was not recorded (0/missing).

    A 0 duration means no per-case timing was captured, not that the case ran
    instantly — showing '0.000s' is misleading, so emit an em dash instead.
    """
    return f"{duration_s:.3f}s" if duration_s and duration_s > 0 else "—"


def render_report(run_id: str, results: list[TestResult], title_suffix: str = "") -> str:
    counts, _ = summarize_results(results)
    score = score_results(results)
    lines = [
        f"# Functional Test Report - {run_id}{title_suffix}",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"| {status} | {count} |")
    lines.extend(
        [
            "",
            "## Score",
            "",
            f"- Total score: {score['pass_rate_total_percent']}%",
            f"- Executed pass rate: {score['pass_rate_executed_percent']}%",
            f"- Execution coverage: {score['execution_coverage_percent']}%",
            f"- Executed cases: {score['executed_cases']} / {score['total_cases']}",
            f"- Not executed cases: {score['not_executed_cases']}",
        ]
    )
    lines.extend(["", "## Results", "", "| Test | Lane | Status | Duration |", "|---|---|:--:|---:|"])
    for result in results:
        lines.append(
            f"| `{result.id}` | {result.lane} | {status_badge(result.status)} | {format_duration(result.duration_s)} |"
        )
    not_pass = [r for r in results if r.status != "PASS"]
    if not_pass:
        lines.extend(["", "## 미통과 상세", ""])
        for result in not_pass:
            reason = "; ".join(result.failures) if result.failures else "(사유 미기재)"
            lines.append(f"- {status_badge(result.status)} `{result.id}` — {reason}")
    return "\n".join(lines)


def write_document_reports(output_dir: Path, manifest: dict[str, Any], results: list[TestResult]) -> None:
    results_dir = output_dir / "results"
    results_dir.mkdir(exist_ok=True)
    grouped: dict[str, list[TestResult]] = {}
    for result in results:
        grouped.setdefault(tc_document_id(result.id), []).append(result)
    for document, doc_results in sorted(grouped.items()):
        report_path = results_dir / f"{safe_path_segment(document)}-result.md"
        report = render_document_report(
            str(manifest.get("run_id", "unknown")),
            document,
            doc_results,
            report_dir=results_dir,
        )
        report_path.write_text(report + "\n", encoding="utf-8")


def render_document_report(
    run_id: str,
    document: str,
    results: list[TestResult],
    report_dir: Path | None = None,
) -> str:
    counts, by_lane = summarize_results(results)
    score = score_results(results)
    lines = [
        f"# {document} 테스트 결과",
        "",
        f"- 실행 ID: `{run_id}`",
        f"- TC 문서: `{document}.md`",
        f"- 전체 케이스 수: {score['total_cases']}",
        f"- 실행된 케이스 수: {score['executed_cases']}",
        f"- 미실행 케이스 수: {score['not_executed_cases']}",
        f"- 총점: {score['pass_rate_total_percent']}%",
        f"- 실행 통과율: {score['pass_rate_executed_percent']}%",
        f"- 실행 커버리지: {score['execution_coverage_percent']}%",
        "",
        "## 요약",
        "",
        "| 상태 | 개수 |",
        "|---|---:|",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"| {status} | {count} |")
    lines.extend(["", "## 레인별", "", "| 레인 | 상태 | 개수 |", "|---|---|---:|"])
    for lane, lane_counts in sorted(by_lane.items()):
        for status, count in sorted(lane_counts.items()):
            lines.append(f"| {lane} | {status} | {count} |")
    lines.extend(
        [
            "",
            "## 테스트케이스별 결과",
            "",
            "| ID | 테스트케이스 | 결과 | 소요시간 | 비고 |",
            "|---|---|:--:|---:|---|",
        ]
    )
    for result in results:
        short_id = result.id.rsplit("/", 1)[-1]
        title = md_cell(result.title)
        note = md_cell(case_note(result))
        lines.append(
            f"| `{short_id}` | {title} | {status_badge(result.status)} | {format_duration(result.duration_s)} | {note} |"
        )
    lines.extend(["", "## 케이스 상세", ""])
    for result in results:
        lines.extend(render_case_result_block(result, report_dir=report_dir))
    return "\n".join(lines)


def md_cell(text: str) -> str:
    """Sanitize a value for a markdown table cell (escape pipes, collapse newlines)."""
    if not text:
        return ""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def case_note(result: TestResult) -> str:
    """Short note for the summary table: the primary failure/block reason, truncated."""
    if not result.failures:
        return ""
    reason = result.failures[0].strip()
    limit = 80
    return reason[:limit] + "…" if len(reason) > limit else reason


FAILURE_LABEL = {"BLOCKED": "차단 사유", "SKIPPED": "스킵 사유", "INFRA": "인프라 실패 사유"}


def render_case_result_block(result: TestResult, report_dir: Path | None = None) -> list[str]:
    lines = [
        f"### {status_badge(result.status)} · `{result.id}`",
        "",
    ]
    if result.title:
        lines.extend([result.title, ""])
    lines.extend(
        [
            "| 레인 | 소요 시간 |",
            "|---|---:|",
            f"| {result.lane} | {format_duration(result.duration_s)} |",
            "",
        ]
    )
    if result.failures:
        label = FAILURE_LABEL.get(result.status, "실패 내역")
        lines.extend([f"**{label}**", ""])
        for failure in result.failures:
            lines.append(f"- {failure}")
        lines.append("")
    lines.extend(render_evidence(result, report_dir=report_dir))
    return lines


EVIDENCE_TEXT_EXTS = {".log", ".txt", ".json", ".jsonl", ".html", ".xml", ".csv", ".tsv", ".out", ".err"}
EVIDENCE_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
EVIDENCE_MAX_BYTES = 50 * 1024
EVIDENCE_TAIL_LINES = 200


def render_evidence(result: TestResult, report_dir: Path | None = None) -> list[str]:
    """Return markdown lines for the evidence section with inline logs/images.

    Missing/empty stdout/stderr produce no output (ultraqa workers do not write them),
    so the report no longer shows "파일 없음" noise. Each block keeps blank-line spacing
    so fenced code and images render correctly instead of merging into list items.
    """
    blocks: list[str] = []
    blocks.extend(render_log_block(result.stdout_path, "stdout", report_dir))
    blocks.extend(render_log_block(result.stderr_path, "stderr", report_dir))

    evidence_dir = discover_evidence_dir(result.stdout_path)
    for path in discover_case_evidence(evidence_dir, result.id):
        blocks.extend(render_evidence_file(path, report_dir))

    if not blocks:
        return []
    return ["**증빙**", "", *blocks]


def render_log_block(path_str: str, label: str, report_dir: Path | None) -> list[str]:
    if not path_str:
        return []
    path = Path(path_str)
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    content, truncated = truncate_text(raw)
    if not content.strip():
        return []
    rel = relative_to_report(path, report_dir)
    header = f"- `{label}` · `{rel}`"
    if truncated:
        header += f" — 마지막 {EVIDENCE_TAIL_LINES}줄"
    return [header, "", "```text", content.rstrip(), "```", ""]


def truncate_text(text: str) -> tuple[str, bool]:
    if len(text.encode("utf-8", errors="replace")) <= EVIDENCE_MAX_BYTES:
        return text, False
    lines = text.splitlines()
    return "\n".join(lines[-EVIDENCE_TAIL_LINES:]), True


def discover_evidence_dir(stdout_path: str) -> Path | None:
    if not stdout_path:
        return None
    parent = Path(stdout_path).parent
    candidate = parent / "evidence"
    return candidate if candidate.is_dir() else None


def case_kebab_prefix(test_id: str) -> str:
    case_part = test_id.rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "", case_part.lower())


def discover_case_evidence(evidence_dir: Path | None, test_id: str) -> list[Path]:
    if evidence_dir is None or not evidence_dir.is_dir():
        return []
    prefix = case_kebab_prefix(test_id)
    if not prefix:
        return []
    matched = [
        path
        for path in evidence_dir.iterdir()
        if path.is_file() and case_kebab_prefix(path.stem).startswith(prefix)
    ]
    return sorted(matched, key=lambda p: p.name)


def render_evidence_file(path: Path, report_dir: Path | None) -> list[str]:
    rel = relative_to_report(path, report_dir)
    suffix = path.suffix.lower()
    if suffix in EVIDENCE_IMAGE_EXTS:
        alt = path.name.replace("[", "\\[").replace("]", "\\]")
        return [f"- `{path.name}`", "", f"![{alt}](<{rel}>)", ""]
    if suffix in EVIDENCE_TEXT_EXTS or suffix == "":
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return [f"- `{path.name}` (읽기 실패: {exc})", ""]
        if not raw.strip():
            return [f"- `{path.name}` (비어 있음)", ""]
        pretty, lang = prettify_evidence(raw, suffix)
        content, truncated = truncate_text(pretty)
        header = f"- `{path.name}`"
        if truncated:
            header += f" — 마지막 {EVIDENCE_TAIL_LINES}줄"
        return [header, "", f"```{lang}", content.rstrip(), "```", ""]
    return [f"- `{path.name}` (바이너리, 임베드 생략)", ""]


def prettify_evidence(raw: str, suffix: str) -> tuple[str, str]:
    """Pretty-print JSON evidence (indented) for readable code blocks.

    Handles whole-document JSON, JSON followed by trailing text (e.g. a curl body
    plus a "HTTP_STATUS: 200" line), and JSONL. Falls back to the raw text + "text"
    language when the content is not JSON.
    """
    stripped = raw.strip()
    looks_json = suffix in (".json", ".jsonl") or stripped[:1] in ("{", "[")
    if not looks_json:
        return raw, "text"
    try:
        return json.dumps(json.loads(stripped), ensure_ascii=False, indent=2), "json"
    except (ValueError, TypeError):
        pass
    # Leading JSON value plus trailing non-JSON text (curl body + HTTP_STATUS line, etc.).
    try:
        obj, idx = json.JSONDecoder().raw_decode(stripped)
        pretty = json.dumps(obj, ensure_ascii=False, indent=2)
        rest = stripped[idx:].strip()
        return (pretty + ("\n\n" + rest if rest else "")), "json"
    except (ValueError, TypeError):
        pass
    if suffix == ".jsonl":
        out: list[str] = []
        parsed_any = False
        for line in stripped.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.dumps(json.loads(line), ensure_ascii=False, indent=2))
                parsed_any = True
            except (ValueError, TypeError):
                out.append(line)
        if parsed_any:
            return "\n".join(out), "json"
    return raw, "text"


def relative_to_report(path: Path, report_dir: Path | None) -> str:
    if report_dir is None:
        return str(path)
    try:
        return os.path.relpath(path, report_dir)
    except ValueError:
        return str(path)


def format_evidence(result: TestResult) -> str:
    paths = [path for path in (result.stdout_path, result.stderr_path) if path]
    if not paths:
        return ""
    return "<br>".join(f"`{path}`" for path in paths)


def tc_document_id(test_id: str) -> str:
    return test_id.split("/", 1)[0] if "/" in test_id else "unknown"


def safe_path_segment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


if __name__ == "__main__":
    raise SystemExit(main())
