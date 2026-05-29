#!/usr/bin/env python3
"""One-shot live functional TC runner.

Reads markdown TC files, creates a per-run tc-test.config.json under the result
directory, gates live execution until required environment access is configured,
builds a live-only manifest, then executes it in parallel through run_manifest.py.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from run_manifest import TestResult, redact as redact_for_file, safe_path_segment, write_results


SCRIPT_DIR = Path(__file__).resolve().parent
RUN_MANIFEST = SCRIPT_DIR / "run_manifest.py"
SKILL_ROOT = SCRIPT_DIR.parent
SKILLS_ROOT = SKILL_ROOT.parent

WORKSPACE = Path(os.environ.get("FUNC_TC_WORKSPACE", os.getcwd())).expanduser()
DOCS_ROOT = Path(os.environ.get("FUNC_TC_DOCS_ROOT", str(WORKSPACE))).expanduser()
REPO_ROOTS = {
    "workspace": WORKSPACE,
    "docs": DOCS_ROOT,
    "cwd": Path.cwd(),
}
VALIDATOR = SKILLS_ROOT / "func-tc-creator/scripts/validate_tc_markdown.py"
for _validator_candidate in (
    Path.home() / ".codex/skills/func-tc-creator/scripts/validate_tc_markdown.py",
):
    if VALIDATOR.exists():
        break
    VALIDATOR = _validator_candidate
DEFAULT_LOG_PATH = Path(os.environ.get("FUNC_TC_LOG_PATH", "")).expanduser()

CONFIG_NAME = "tc-test.config.json"
KST = timezone(timedelta(hours=9), "KST")
TC_RE = re.compile(r"^###\s+([A-Z]+-\d+)\s+-\s+(.+)$", re.MULTILINE)
MOCK_TARGET_RE = re.compile(r"\b(MockMvc|JUnit|pytest|Vitest|Jest RTL|Jest)\b", re.IGNORECASE)
MUTATING_RE = re.compile(r"(생성|수정|삭제|업로드|저장|create|update|delete|upload|save)", re.IGNORECASE)
PLAYWRIGHT_SPEC_RE = re.compile(r"\.(spec|test)\.(ts|tsx|js|jsx|mjs|cjs)$")
# Worker-backend infra failures (NOT product failures): quota/rate/credit/auth/connection
# limits, model overload, or the worker process exiting non-zero. When the worker dies with
# one of these and produced zero case progress, the cases are INFRA, never product FAIL,
# and retrying the same backend is pointless (non-retryable).
INFRA_SIGNATURE_RE = re.compile(
    r"usage limit|rate.?limit|rate.?limited|\bquota\b|insufficient_quota|out of credit|"
    r"credit balance|credit balance is too low|billing|payment required|\b402\b|\b429\b|\b529\b|"
    r"overloaded_error|overloaded|service unavailable|\b503\b|"
    r"ECONNREFUSED|connection refused|connection reset|ETIMEDOUT|ENOTFOUND|getaddrinfo|"
    r"authentication_error|invalid api key|invalid x-api-key|\bunauthorized\b|\b401\b|"
    r"command not found|exited with code [1-9]",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tc_path",
        nargs="?",
        default="test/testcase/release-1.0",
        help="TC markdown file or directory",
    )
    parser.add_argument("--config", help="optional config seed path; default creates a fresh config in <run-dir>/tc-test.config.json")
    parser.add_argument("--init-config", action="store_true", help="create/update config from arguments and stop")
    parser.add_argument("--force-config", action="store_true", help="overwrite existing config when used with --init-config")
    parser.add_argument("--environment", choices=("local", "docker"), help="execution environment type for config")
    parser.add_argument("--app-url", help="browser entry URL for config")
    parser.add_argument("--api-base-url", help="primary API base URL for config")
    parser.add_argument("--aux-url", help="optional secondary service URL for config")
    parser.add_argument("--mongo-database", help="MongoDB database name for config")
    parser.add_argument("--output-dir", help="run output directory")
    parser.add_argument("--run-id", help="run id")
    parser.add_argument("--engine", choices=("ultraqa", "static"), help="execution engine; default is config runner.engine or ultraqa")
    parser.add_argument("--max-workers", type=int, help="override runner max workers")
    parser.add_argument("--ultraqa-workers", type=int, help="override one-shot ultraqa document workers")
    parser.add_argument("--ultraqa-timeout", type=int, help="override one-shot ultraqa timeout seconds per TC document")
    parser.add_argument("--ultraqa-blocked-retries", type=int, help="self-heal BLOCKED cases by adjusting test strategy, up to N retries per doc (default 3, never modifies product source)")
    parser.add_argument("--ultraqa-max-continuations", type=int, help="override timeout/error continuation attempts per TC document")
    parser.add_argument("--dry-run", action="store_true", help="write plan/manifest but do not execute")
    parser.add_argument("--prepare-only", action="store_true", help="config gate + auth + plan + manifest + per-document ultraqa prompt.md render, then stop (no worker spawn); the main session drives subagents")
    parser.add_argument("--finalize", action="store_true", help="collect per-document ultraqa result.json files written by subagents and emit results.json/report.md/results/<doc>-result.md scoring (no worker spawn)")
    parser.add_argument("--include-needs-selector", action="store_true")
    parser.add_argument("--include-needs-source-confirmation", action="store_true")
    parser.add_argument("--include-design-target", action="store_true")
    args = parser.parse_args()

    tc_root = resolve_path(args.tc_path)
    run_id = args.run_id or current_kst_run_id()
    output_dir = Path(args.output_dir) if args.output_dir else default_output_dir(tc_root, run_id)
    if args.config and not args.output_dir:
        config_arg = resolve_path(args.config)
        if config_arg.name == CONFIG_NAME:
            output_dir = config_arg.parent
            if not args.run_id:
                run_id = output_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)
    tests = parse_tc_files(tc_root)

    config_path = resolve_config_path(args.config, output_dir)
    config = ensure_run_config(config_path, args, output_dir)
    if args.finalize:
        return finalize_ultraqa_suite(tests, tc_root, run_id, output_dir, config)
    auth_issue = ensure_auth(config, output_dir)
    mongo_issue = ensure_mongodb(config, tests)
    log_issue = ensure_app_log(config, tests)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate_issues = config_gate_issues(config, tests)
    if auth_issue:
        gate_issues.insert(0, auth_issue)
    if mongo_issue:
        gate_issues.insert(0, mongo_issue)
    if log_issue:
        gate_issues.insert(0, log_issue)

    print(f"CONFIG={config_path}")
    print(f"CONFIG_CREATED=1")
    print(f"RUN_ID={run_id}")
    print(f"TC_PATH={tc_root}")
    print(f"OUTPUT_DIR={output_dir}")
    if args.init_config or gate_issues:
        print("CONFIG_GATE=1")
        for issue in gate_issues:
            print(f"CONFIG_MISSING={issue}")
        print("NEXT=Fill the generated run config or export the referenced env vars, then rerun with --config <run-dir>/tc-test.config.json to execute live TC in the same run directory.")
        return 0

    validation_log = output_dir / "validation.log"
    validate_tc_files(tc_root, validation_log)

    engine = selected_engine(args, config)
    manifest = build_ultraqa_manifest(tests, tc_root, run_id, output_dir, config, args) if engine == "ultraqa" else build_manifest(tests, run_id, output_dir, config, args)
    manifest_path = output_dir / "manifest.json"
    plan_path = output_dir / "plan.json"
    plan_path.write_text(json.dumps({"tests": tests}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"PLAN={plan_path}")
    print(f"MANIFEST={manifest_path}")
    print(f"ENGINE={engine}")
    print_summary(manifest)

    if args.dry_run:
        print("DRY_RUN=1")
        return 0

    if args.prepare_only:
        if engine != "ultraqa":
            print("PREPARE_ONLY_REQUIRES_ULTRAQA=1", file=sys.stderr)
            return 2
        prepared = prepare_ultraqa_documents(tests, tc_root, output_dir, config)
        print("PREPARE_READY=1")
        print("PREPARE_DOCS=" + json.dumps(prepared, ensure_ascii=False))
        print(f"PREPARE_DOC_COUNT={len(prepared)}")
        print(f"PREPARE_CASE_COUNT={sum(d['case_count'] for d in prepared)}")
        return 0

    if engine == "ultraqa":
        return run_ultraqa_suite(tests, tc_root, run_id, output_dir, config, args)

    command = [
        sys.executable,
        str(RUN_MANIFEST),
        str(manifest_path),
        "--output-dir",
        str(output_dir),
        "--max-workers",
        str(args.max_workers or config.get("runner", {}).get("maxWorkers", 6)),
    ]
    return subprocess.call(command, cwd=str(DOCS_ROOT))


def resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    candidate = DOCS_ROOT / path
    return candidate if candidate.exists() else Path.cwd() / path


def resolve_config_path(path_text: str | None, output_dir: Path) -> Path:
    if path_text:
        path = Path(path_text)
        return path if path.is_absolute() else DOCS_ROOT / path
    return output_dir / CONFIG_NAME


def default_output_dir(tc_root: Path, run_id: str) -> Path:
    cycle_dir = tc_root if tc_root.is_dir() else tc_root.parent
    return DOCS_ROOT / "test/test-results" / cycle_version_slug(cycle_dir.name) / run_id


def current_kst_run_id() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d_%H-%M-%S")


def current_kst_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def cycle_version_slug(dirname: str) -> str:
    match = re.match(r"^(cycle\d+)_(.+)$", dirname)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return dirname.replace("_", "-")


def ensure_run_config(config_path: Path, args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if args.config and config_path.exists() and not args.force_config:
        config = load_config(config_path)
        return config
    interactive_config_args(args)
    config = default_config(args, output_dir)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return config


def interactive_config_args(args: argparse.Namespace) -> None:
    if not sys.stdin.isatty():
        return
    if not args.environment:
        choice = input("Execution environment [local/docker] (default: local): ").strip().lower()
        args.environment = "docker" if choice == "docker" else "local"
    if not args.app_url:
        value = input("App URL: ").strip()
        if value:
            args.app_url = value
    if not args.api_base_url:
        value = input("API base URL: ").strip()
        if value:
            args.api_base_url = value
    if not args.aux_url:
        value = input("Aux service URL (optional): ").strip()
        if value:
            args.aux_url = value
    if not args.mongo_database:
        value = input("MongoDB database name (optional, can edit later): ").strip()
        if value:
            args.mongo_database = value


def default_config(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    return {
        "version": 1,
        "environment": {
            "type": args.environment or "local",
            "name": "test-env",
            "appUrl": args.app_url or "",
            "apiBaseUrl": args.api_base_url or "",
            "auxUrl": args.aux_url or "",
            "production": False,
        },
        "auth": {
            "required": False,
            "usernameEnv": "FUNC_TC_USER",
            "passwordEnv": "FUNC_TC_PASSWORD",
            "tokenEnv": "FUNC_TC_TOKEN",
            "storageStatePath": str(output_dir / "auth/storage-state.json"),
            "login": {
                "mode": "disabled",
                "command": "",
            },
        },
        "mongodb": {
            "uriEnv": "MONGO_URI",
            "uri": "",
            "database": args.mongo_database or "",
            "dockerContainer": "",
            "collections": {},
            "mongoshCommand": "mongosh",
        },
        "logs": {
            "app": {
                "mode": "file" if str(DEFAULT_LOG_PATH) else "none",
                "filePath": str(DEFAULT_LOG_PATH) if str(DEFAULT_LOG_PATH) else "",
                "dockerContainer": "",
                "command": "",
            }
        },
        "runner": {
            "engine": "ultraqa",
            "maxWorkers": 6,
            "apiWorkers": 8,
            "uiWorkers": 2,
            "uiApWorkers": 2,
            "ultraqaWorkers": 4,
            "ultraqaTimeoutSeconds": 1800,
            "ultraqaMaxContinuations": 2,
            "ultraqaBlockedMaxRetries": 3,
            "uniquePrefix": "tc",
        },
        "safety": {
            "liveOnly": True,
            "allowDestructive": True,
            "requireCleanupVerification": True,
        },
    }


def ensure_mongodb(config: dict[str, Any], tests: list[dict[str, Any]]) -> str | None:
    if not any(needs_mongodb(test) for test in tests):
        return None

    mongo = config.setdefault("mongodb", {})
    uri_env = mongo.get("uriEnv", "MONGO_URI")
    if uri_env and os.environ.get(uri_env):
        if not mongo.get("database"):
            mongo["database"] = os.environ.get("MONGODB_DATABASE", "shared")
        mongo.setdefault("uri", "")
        return None

    configured_uri = mongo.get("uri")
    if configured_uri:
        os.environ[uri_env] = configured_uri
        if not mongo.get("database"):
            mongo["database"] = os.environ.get("MONGODB_DATABASE", "shared")
        return None

    container = mongo.get("dockerContainer", "")
    if not container:
        return "mongodb URI is required: set mongodb.uri, export mongodb.uriEnv, or configure mongodb.dockerContainer"
    try:
        inspect = docker_inspect(container)
    except RuntimeError as exc:
        return f"mongodb docker container is not available: {container}: {exc}"

    env = docker_env(inspect)
    database = mongo.get("database") or env.get("MONGODB_DATABASE") or "shared"
    uri = mongo_uri_from_docker(inspect, database)
    if not uri:
        return f"mongodb docker container has no published 27017 port: {container}"

    ping = subprocess.run(
        ["docker", "exec", container, "mongosh", "--quiet", "--eval", "db.runCommand({ ping: 1 }).ok"],
        text=True,
        capture_output=True,
        timeout=20,
    )
    if ping.returncode != 0 or "1" not in ping.stdout:
        detail = (ping.stderr or ping.stdout).strip()[:300]
        return f"mongodb docker ping failed for {container}: {detail}"

    mongo["dockerContainer"] = container
    mongo["database"] = database
    mongo["uri"] = uri
    mongo["mongoshCommand"] = f"docker exec {container} mongosh"
    os.environ[uri_env] = uri
    return None


def ensure_app_log(config: dict[str, Any], tests: list[dict[str, Any]]) -> str | None:
    if not any(needs_log(test) for test in tests):
        return None

    app_log = config.setdefault("logs", {}).setdefault("app", {})
    mode = app_log.get("mode", "none")
    file_path = app_log.get("filePath", "")
    if mode == "file" and file_path and Path(file_path).exists():
        return None
    if mode == "docker" and app_log.get("dockerContainer"):
        return None
    if mode == "command" and app_log.get("command"):
        return None

    if str(DEFAULT_LOG_PATH) and DEFAULT_LOG_PATH.exists():
        app_log["mode"] = "file"
        app_log["filePath"] = str(DEFAULT_LOG_PATH)
        app_log["dockerContainer"] = ""
        app_log["command"] = ""
        return None

    candidates = app_log.get("dockerCandidates") or []
    container = first_existing_docker_container([str(item) for item in candidates])
    if container:
        app_log["mode"] = "docker"
        app_log["filePath"] = ""
        app_log["dockerContainer"] = container
        app_log["command"] = ""
        return None

    return "logs.app source is required for log assertions"


def docker_inspect(container: str) -> dict[str, Any]:
    proc = subprocess.run(
        ["docker", "inspect", container],
        text=True,
        capture_output=True,
        timeout=20,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:300])
    data = json.loads(proc.stdout)
    if not data:
        raise RuntimeError("docker inspect returned no data")
    return data[0]


def docker_env(inspect: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in inspect.get("Config", {}).get("Env", []) or []:
        if "=" in item:
            key, value = item.split("=", 1)
            result[key] = value
    return result


def mongo_uri_from_docker(inspect: dict[str, Any], database: str) -> str | None:
    ports = inspect.get("NetworkSettings", {}).get("Ports", {}) or {}
    bindings = ports.get("27017/tcp") or []
    host_port = ""
    for binding in bindings:
        if binding.get("HostPort"):
            host_port = binding["HostPort"]
            break
    if not host_port:
        return None
    return f"mongodb://127.0.0.1:{host_port}/{database}?directConnection=true"


def first_existing_docker_container(candidates: list[str]) -> str | None:
    for container in candidates:
        proc = subprocess.run(
            ["docker", "inspect", container],
            text=True,
            capture_output=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return container
    return None


def ensure_auth(config: dict[str, Any], output_dir: Path) -> str | None:
    auth = config.get("auth", {})
    if not auth.get("required", False):
        return None

    token_env = auth.get("tokenEnv", "FUNC_TC_TOKEN")
    if os.environ.get(token_env):
        return None

    storage_state_path = Path(auth.get("storageStatePath") or output_dir / "auth/storage-state.json")
    if not storage_state_path.is_absolute():
        storage_state_path = DOCS_ROOT / storage_state_path
    if storage_state_path.exists():
        return None

    login_cfg = auth.get("login", {})
    command = login_cfg.get("command", "")
    if not command:
        return f"auth is required: export {token_env}, provide auth.storageStatePath, or set auth.login.command"

    env = os.environ.copy()
    env.update(default_env(config))
    completed = subprocess.run(
        ["bash", "-lc", command],
        cwd=str(DOCS_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=int(login_cfg.get("timeoutSeconds", 120)),
    )
    auth_dir = output_dir / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    (auth_dir / "login-command.out").write_text(redact_for_file(completed.stdout), encoding="utf-8")
    (auth_dir / "login-command.err").write_text(redact_for_file(completed.stderr), encoding="utf-8")
    if completed.returncode != 0:
        return f"auth.login.command failed with exit code {completed.returncode}"
    if not os.environ.get(token_env) and not storage_state_path.exists():
        return f"auth.login.command finished but {token_env} or auth.storageStatePath is still unavailable"
    return None


def config_gate_issues(config: dict[str, Any], tests: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    env_cfg = config.get("environment", {})
    for key in ("appUrl", "apiBaseUrl"):
        if requires_environment_key(tests, key) and not env_cfg.get(key):
            issues.append(f"environment.{key} is required")

    auth = config.get("auth", {})
    token_env = auth.get("tokenEnv", "FUNC_TC_TOKEN")
    storage_state = auth.get("storageStatePath", "")
    auth_ready = bool(os.environ.get(token_env)) or bool(storage_state and Path(storage_state).exists())
    if auth.get("required", False) and not auth_ready:
        issues.append(f"auth is required: export {token_env} or provide auth.storageStatePath")

    if any(needs_mongodb(test) for test in tests):
        mongo = config.get("mongodb", {})
        uri_env = mongo.get("uriEnv", "MONGO_URI")
        if not os.environ.get(uri_env):
            issues.append(f"mongodb URI is required: export {uri_env}")
        if not mongo.get("database"):
            issues.append("mongodb.database is required for MongoDB consistency checks")

    if any(needs_log(test) for test in tests):
        app_log = config.get("logs", {}).get("app", {})
        if app_log.get("mode", "none") == "none":
            issues.append("logs.app source is required for log assertions")
    return issues


def requires_environment_key(tests: list[dict[str, Any]], key: str) -> bool:
    if key == "appUrl":
        return any(test["tc_id"].startswith(("UI-", "INT-", "TIMING-")) for test in tests)
    if key == "apiBaseUrl":
        return any(test["tc_id"].startswith(("API-", "INT-", "TIMING-")) or "curl" in test.get("target", "").casefold() for test in tests)
    return False


def needs_mongodb(test: dict[str, Any]) -> bool:
    return "mongodb" in test.get("section", "").casefold()


def needs_log(test: dict[str, Any]) -> bool:
    text = test.get("section", "").casefold()
    return "log" in text or "로그" in test.get("section", "")


def load_config(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    env_type = config.get("environment", {}).get("type")
    if env_type not in {"local", "docker"}:
        raise SystemExit(f"Invalid environment.type in {config_path}: {env_type!r}")
    return config


def validate_tc_files(tc_root: Path, log_path: Path) -> None:
    if not VALIDATOR.exists():
        log_path.write_text(f"validator not found: {VALIDATOR}\n", encoding="utf-8")
        return
    files = [tc_root] if tc_root.is_file() else sorted(tc_root.glob("*.md"))
    lines: list[str] = []
    for path in files:
        if path.name.upper() == "INDEX.MD" or path.name == CONFIG_NAME:
            continue
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--strict", str(path)],
            text=True,
            capture_output=True,
            cwd=str(DOCS_ROOT),
        )
        lines.append(f"$ {VALIDATOR} --strict {path}")
        lines.append(proc.stdout)
        lines.append(proc.stderr)
        if proc.returncode != 0:
            lines.append(f"VALIDATION_FAILED {path}")
    log_path.write_text("\n".join(lines), encoding="utf-8")


def parse_tc_files(tc_root: Path) -> list[dict[str, Any]]:
    files = [tc_root] if tc_root.is_file() else sorted(tc_root.glob("*.md"))
    tests: list[dict[str, Any]] = []
    for path in files:
        if path.name.upper() == "INDEX.MD" or path.name == CONFIG_NAME:
            continue
        text = path.read_text(encoding="utf-8")
        matches = list(TC_RE.finditer(text))
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            section = text[start:end]
            tc_id = match.group(1)
            tests.append(
                {
                    "feature_file": str(path),
                    "feature": path.stem,
                    "tc_id": tc_id,
                    "id": f"{path.stem}/{tc_id}",
                    "title": match.group(2).strip(),
                    "section": section,
                    "type": find_value(section, "유형") or infer_type(tc_id),
                    "target": find_value(section, "자동화 대상") or "",
                    "status": find_value(section, "자동화 상태") or "",
                    "test_file": extract_test_file(section),
                    "method": extract_inline(section, "메서드"),
                    "api_path": extract_inline(section, "경로"),
                    "request": extract_inline(section, "요청"),
                    "response": extract_inline(section, "응답"),
                }
            )
    return tests


def selected_engine(args: argparse.Namespace, config: dict[str, Any]) -> str:
    engine = args.engine or config.get("runner", {}).get("engine", "ultraqa")
    if engine not in {"ultraqa", "static"}:
        raise SystemExit(f"Invalid runner engine: {engine!r}")
    return engine


def build_ultraqa_manifest(
    tests: list[dict[str, Any]],
    tc_root: Path,
    run_id: str,
    output_dir: Path,
    config: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    docs = []
    for document, doc_tests in sorted(group_tests_by_document(tests).items()):
        feature_file = Path(doc_tests[0]["feature_file"])
        docs.append(
            {
                "id": document,
                "lane": "ultraqa",
                "tc_document": str(feature_file),
                "case_count": len(doc_tests),
                "case_ids": [test["id"] for test in doc_tests],
                "output_json": str(output_dir / "ultraqa" / document / "result.json"),
                "progress_json": str(output_dir / "ultraqa" / document / "progress.json"),
                "worker_context_json": str(output_dir / "ultraqa" / document / "worker-context.json"),
                "output_markdown": str(output_dir / "ultraqa" / document / "final.md"),
                "one_shot": True,
                "no_fix_loop": True,
                "resumable": True,
            }
        )
    return {
        "run_id": run_id,
        "generated_at": current_kst_iso(),
        "engine": "ultraqa",
        "tc_path": str(tc_root),
        "environment": redacted_environment(config),
        "tests": docs,
    }


def run_ultraqa_suite(
    tests: list[dict[str, Any]],
    tc_root: Path,
    run_id: str,
    output_dir: Path,
    config: dict[str, Any],
    args: argparse.Namespace,
) -> int:
    docs = group_tests_by_document(tests)
    ultraqa_dir = output_dir / "ultraqa"
    ultraqa_dir.mkdir(exist_ok=True)
    workers = args.ultraqa_workers or int(config.get("runner", {}).get("ultraqaWorkers", 2))
    results: list[TestResult] = []
    total_docs = len(docs)
    completed_docs = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {
            executor.submit(run_ultraqa_document, document, doc_tests, tc_root, run_id, output_dir, config, args): document
            for document, doc_tests in sorted(docs.items())
        }
        for future in concurrent.futures.as_completed(future_map):
            document = future_map[future]
            try:
                doc_results = future.result()
            except Exception as exc:
                doc_tests = docs[document]
                doc_dir = ultraqa_dir / safe_path_segment(document)
                doc_dir.mkdir(parents=True, exist_ok=True)
                stdout_path = doc_dir / "worker-exception.out"
                stderr_path = doc_dir / "worker-exception.err"
                failure = f"ultraqa document worker crashed before returning results: {exc!r}"
                stdout_path.write_text("", encoding="utf-8")
                stderr_path.write_text(failure + "\n", encoding="utf-8")
                results.extend(
                    TestResult(
                        id=test["id"],
                        title=test.get("title", ""),
                        lane="ultraqa",
                        status="INFRA",
                        duration_s=0.0,
                        exit_code=None,
                        stdout_path=str(stdout_path),
                        stderr_path=str(stderr_path),
                        failures=[failure],
                    )
                    for test in doc_tests
                )
                completed_docs += 1
                print(
                    f"[{completed_docs}/{total_docs}] WORKER-ERROR {document}: {exc!r}",
                    file=sys.stderr,
                    flush=True,
                )
                continue
            results.extend(doc_results)
            completed_docs += 1
            tally: dict[str, int] = {}
            for item in doc_results:
                tally[item.status] = tally.get(item.status, 0) + 1
            summary = " ".join(f"{status}={count}" for status, count in sorted(tally.items())) or "no-cases"
            print(
                f"[{completed_docs}/{total_docs}] DONE {document} ({summary})",
                file=sys.stderr,
                flush=True,
            )
    results.sort(key=lambda item: item.id)
    manifest = {
        "run_id": run_id,
        "generated_at": current_kst_iso(),
        "engine": "ultraqa",
        "tc_path": str(tc_root),
        "environment": redacted_environment(config),
        "tests": [{"id": result.id, "lane": result.lane} for result in results],
    }
    write_results(output_dir, manifest, results)
    return 1 if any(result.status in {"FAIL", "BLOCKED", "INFRA"} for result in results) else 0


def prepare_ultraqa_documents(
    tests: list[dict[str, Any]],
    tc_root: Path,
    output_dir: Path,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Render one ultraqa worker prompt per TC document without spawning any worker.

    The main Codex session reads each prompt.md and dispatches it to a bounded
    subagent; the subagent writes result.json / progress.json /
    worker-context.json / evidence under the document dir using that prompt's contract.
    """
    docs = group_tests_by_document(tests)
    ultraqa_dir = output_dir / "ultraqa"
    ultraqa_dir.mkdir(exist_ok=True)
    prepared: list[dict[str, Any]] = []
    for document, doc_tests in sorted(docs.items()):
        doc_dir = ultraqa_dir / safe_path_segment(document)
        doc_dir.mkdir(parents=True, exist_ok=True)
        result_json = doc_dir / "result.json"
        progress_json = doc_dir / "progress.json"
        context_json = doc_dir / "worker-context.json"
        state_json = doc_dir / "worker-state.json"
        prompt = render_ultraqa_prompt(
            document=document,
            doc_tests=doc_tests,
            all_doc_tests=doc_tests,
            tc_root=tc_root,
            output_dir=output_dir,
            config=config,
            result_json=result_json,
            progress_json=progress_json,
            context_json=context_json,
            state_json=state_json,
            attempt=1,
            previous={},
            attempts=[],
        )
        prompt_path = doc_dir / "prompt.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        prepared.append(
            {
                "document": document,
                "feature_file": doc_tests[0]["feature_file"],
                "case_count": len(doc_tests),
                "case_ids": [t["id"] for t in doc_tests],
                "prompt": str(prompt_path),
                "doc_dir": str(doc_dir),
                "result_json": str(result_json),
                "progress_json": str(progress_json),
            }
        )
    return prepared


def finalize_ultraqa_suite(
    tests: list[dict[str, Any]],
    tc_root: Path,
    run_id: str,
    output_dir: Path,
    config: dict[str, Any],
) -> int:
    """Collect subagent-written per-document result.json and emit suite scoring artifacts.

    Reuses the same result.json -> TestResult -> write_results path as run_ultraqa_suite,
    so results.json / report.md / results/<doc>-result.md stay identical to the inline
    worker engine. Cases with no subagent result are marked via synthetic unfinished cases.
    """
    docs = group_tests_by_document(tests)
    results: list[TestResult] = []
    for document, doc_tests in sorted(docs.items()):
        doc_dir = output_dir / "ultraqa" / safe_path_segment(document)
        result_json = doc_dir / "result.json"
        progress_json = doc_dir / "progress.json"
        context_json = doc_dir / "worker-context.json"
        state_json = doc_dir / "worker-state.json"
        final_md = doc_dir / "final.md"
        parsed = best_ultraqa_progress(result_json, progress_json)
        pending = pending_ultraqa_tests(doc_tests, parsed)
        if pending:
            # A case with no subagent result was never executed, so it can never be FAIL
            # (FAIL means the product was exercised and an assertion failed). Zero terminal
            # cases for the whole document means the subagent crashed/never wrote -> INFRA.
            # If it produced some cases, the stragglers are unexecuted test-side gaps -> BLOCKED.
            # Marking stragglers FAIL manufactures fake product defects and tanks the score.
            forced = "BLOCKED" if terminal_case_ids(parsed) else "INFRA"
            parsed = add_synthetic_unfinished_cases(
                parsed, pending, [], "finalize: subagent produced no result for this case", forced_status=forced
            )
        if not final_md.exists():
            final_md.write_text(
                render_worker_final_summary(document, [], parsed, progress_json, context_json, state_json),
                encoding="utf-8",
            )
        results.extend(
            ultraqa_results_to_test_results(
                doc_tests=doc_tests,
                parsed=parsed,
                duration=0.0,
                exit_code=0,
                stdout_path=doc_dir / "stdout.log",
                stderr_path=doc_dir / "stderr.log",
                final_md=final_md,
                result_json=result_json,
            )
        )
    results.sort(key=lambda item: item.id)
    manifest = {
        "run_id": run_id,
        "generated_at": current_kst_iso(),
        "engine": "ultraqa",
        "tc_path": str(tc_root),
        "environment": redacted_environment(config),
        "tests": [{"id": r.id, "lane": r.lane} for r in results],
    }
    write_results(output_dir, manifest, results)
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    total = len(results)
    passed = counts.get("PASS", 0)
    failed = counts.get("FAIL", 0)
    executed = passed + failed
    total_score = round(passed / total * 100, 1) if total else 0.0
    pass_rate = round(passed / executed * 100, 1) if executed else 0.0
    coverage = round(executed / total * 100, 1) if total else 0.0
    print("FINALIZE_READY=1")
    print("COUNTS=" + json.dumps(counts, ensure_ascii=False, sort_keys=True))
    print(f"TOTAL_SCORE={total_score}")
    print(f"EXECUTED_PASS_RATE={pass_rate}")
    print(f"EXECUTION_COVERAGE={coverage}")
    print(f"INFRA_CASES={counts.get('INFRA', 0)}")
    print(f"RESULTS={output_dir / 'results.json'}")
    print(f"REPORT={output_dir / 'report.md'}")
    return 1 if (failed or counts.get("BLOCKED", 0) or counts.get("INFRA", 0)) else 0


def run_ultraqa_document(
    document: str,
    doc_tests: list[dict[str, Any]],
    tc_root: Path,
    run_id: str,
    output_dir: Path,
    config: dict[str, Any],
    args: argparse.Namespace,
) -> list[TestResult]:
    doc_dir = output_dir / "ultraqa" / safe_path_segment(document)
    doc_dir.mkdir(parents=True, exist_ok=True)
    result_json = doc_dir / "result.json"
    progress_json = doc_dir / "progress.json"
    context_json = doc_dir / "worker-context.json"
    state_json = doc_dir / "worker-state.json"
    final_md = doc_dir / "final.md"
    timeout = args.ultraqa_timeout or int(config.get("runner", {}).get("ultraqaTimeoutSeconds", 1800))
    max_continuations = args.ultraqa_max_continuations
    if max_continuations is None:
        max_continuations = int(config.get("runner", {}).get("ultraqaMaxContinuations", 2))

    attempts: list[dict[str, Any]] = []
    latest_stdout = doc_dir / "stdout-attempt-00.log"
    latest_stderr = doc_dir / "stderr-attempt-00.log"
    latest_final = final_md
    latest_exit_code = 0
    total_duration = 0.0
    exhausted_reason = ""

    for attempt in range(1, max_continuations + 2):
        current = best_ultraqa_progress(result_json, progress_json)
        pending_tests = pending_ultraqa_tests(doc_tests, current)
        write_worker_state(state_json, document, attempt, max_continuations, attempts, current, pending_tests, "starting")
        if not pending_tests:
            break

        prompt_path = doc_dir / f"prompt-attempt-{attempt:02d}.md"
        latest_stdout = doc_dir / f"stdout-attempt-{attempt:02d}.log"
        latest_stderr = doc_dir / f"stderr-attempt-{attempt:02d}.log"
        latest_final = doc_dir / f"final-attempt-{attempt:02d}.md"
        prompt = render_ultraqa_prompt(
            document=document,
            doc_tests=pending_tests,
            all_doc_tests=doc_tests,
            tc_root=tc_root,
            output_dir=output_dir,
            config=config,
            result_json=result_json,
            progress_json=progress_json,
            context_json=context_json,
            state_json=state_json,
            attempt=attempt,
            previous=current,
            attempts=attempts,
        )
        prompt_path.write_text(prompt, encoding="utf-8")
        if attempt == 1:
            (doc_dir / "prompt.md").write_text(prompt, encoding="utf-8")

        worker = run_omx_ultraqa_worker(prompt, latest_final, timeout, config)
        total_duration += worker["duration_s"]
        latest_exit_code = int(worker["returncode"])
        latest_stdout.write_text(redact_for_file(str(worker["stdout"])), encoding="utf-8")
        latest_stderr.write_text(redact_for_file(str(worker["stderr"])), encoding="utf-8")
        attempts.append(
            {
                "attempt": attempt,
                "exit_code": latest_exit_code,
                "timed_out": worker["timed_out"],
                "duration_s": round(float(worker["duration_s"]), 3),
                "prompt": str(prompt_path),
                "stdout": str(latest_stdout),
                "stderr": str(latest_stderr),
                "final": str(latest_final),
            }
        )

        current = best_ultraqa_progress(result_json, progress_json)
        pending_tests = pending_ultraqa_tests(doc_tests, current)
        reason = classify_worker_outcome(worker, current, pending_tests)
        write_worker_state(state_json, document, attempt, max_continuations, attempts, current, pending_tests, reason)
        if not pending_tests:
            break
        if reason == "worker_infra_failure_non_retryable":
            # Non-retryable backend failure: stop now instead of burning the continuation budget.
            exhausted_reason = reason
            break
        if attempt > max_continuations:
            exhausted_reason = reason
            break

    blocked_max_retries = args.ultraqa_blocked_retries
    if blocked_max_retries is None:
        blocked_max_retries = int(config.get("runner", {}).get("ultraqaBlockedMaxRetries", 3))

    for retry in range(1, blocked_max_retries + 1):
        current = best_ultraqa_progress(result_json, progress_json)
        blocked_now = blocked_cases_detail(current, doc_tests)
        if not blocked_now:
            break
        attempt_index = max_continuations + 1 + retry
        prompt_path = doc_dir / f"prompt-blocked-retry-{retry:02d}.md"
        latest_stdout = doc_dir / f"stdout-blocked-retry-{retry:02d}.log"
        latest_stderr = doc_dir / f"stderr-blocked-retry-{retry:02d}.log"
        latest_final = doc_dir / f"final-blocked-retry-{retry:02d}.md"

        blocked_ids = {b["id"] for b in blocked_now}
        evicted_progress = evict_cases_from_progress(current, blocked_ids)
        progress_json.write_text(json.dumps(evicted_progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        blocked_tests = [t for t in doc_tests if t["id"] in blocked_ids]
        prompt = render_blocked_retry_prompt(
            document=document,
            doc_tests=blocked_tests,
            all_doc_tests=doc_tests,
            tc_root=tc_root,
            output_dir=output_dir,
            config=config,
            result_json=result_json,
            progress_json=progress_json,
            context_json=context_json,
            state_json=state_json,
            retry=retry,
            max_retries=blocked_max_retries,
            blocked_history=blocked_now,
            attempts=attempts,
            previous=evicted_progress,
        )
        prompt_path.write_text(prompt, encoding="utf-8")
        write_worker_state(state_json, document, attempt_index, max_continuations, attempts, evicted_progress, blocked_tests, f"blocked-retry-{retry}/{blocked_max_retries}-start")

        worker = run_omx_ultraqa_worker(prompt, latest_final, timeout, config)
        total_duration += worker["duration_s"]
        latest_exit_code = int(worker["returncode"])
        latest_stdout.write_text(redact_for_file(str(worker["stdout"])), encoding="utf-8")
        latest_stderr.write_text(redact_for_file(str(worker["stderr"])), encoding="utf-8")
        attempts.append(
            {
                "attempt": attempt_index,
                "kind": "blocked-retry",
                "retry": retry,
                "max_retries": blocked_max_retries,
                "blocked_case_ids": sorted(blocked_ids),
                "exit_code": latest_exit_code,
                "timed_out": worker["timed_out"],
                "duration_s": round(float(worker["duration_s"]), 3),
                "prompt": str(prompt_path),
                "stdout": str(latest_stdout),
                "stderr": str(latest_stderr),
                "final": str(latest_final),
            }
        )
        write_worker_state(state_json, document, attempt_index, max_continuations, attempts, best_ultraqa_progress(result_json, progress_json), [], f"blocked-retry-{retry}/{blocked_max_retries}-done")

    parsed = best_ultraqa_progress(result_json, progress_json)
    pending_tests = pending_ultraqa_tests(doc_tests, parsed)
    if pending_tests:
        parsed = add_synthetic_unfinished_cases(parsed, pending_tests, attempts, exhausted_reason)
    final_md.write_text(render_worker_final_summary(document, attempts, parsed, progress_json, context_json, state_json), encoding="utf-8")
    result_json.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return ultraqa_results_to_test_results(
        doc_tests=doc_tests,
        parsed=parsed,
        duration=total_duration,
        exit_code=latest_exit_code,
        stdout_path=latest_stdout,
        stderr_path=latest_stderr,
        final_md=final_md,
        result_json=result_json,
    )


def render_ultraqa_prompt(
    document: str,
    doc_tests: list[dict[str, Any]],
    all_doc_tests: list[dict[str, Any]],
    tc_root: Path,
    output_dir: Path,
    config: dict[str, Any],
    result_json: Path,
    progress_json: Path,
    context_json: Path,
    state_json: Path,
    attempt: int,
    previous: dict[str, Any],
    attempts: list[dict[str, Any]],
) -> str:
    env_cfg = config.get("environment", {})
    mongo = config.get("mongodb", {})
    app_log = config.get("logs", {}).get("app", {})
    cases = [{"id": test["id"], "title": test["title"], "type": test.get("type", ""), "tc_id": test["tc_id"]} for test in doc_tests]
    completed = sorted(terminal_case_ids(previous))
    artifact_summary = summarize_worker_artifacts(result_json.parent)
    return f"""$ultraqa

Functional TC resumable one-shot QA execution.

Hard constraints:
- Test only once. Do not enter UltraQA's diagnose/fix/retest loop.
- Do not modify product source files.
- Do not ask the user for endpoints, selectors, cleanup steps, or bearer tokens.
- Dynamically discover API endpoints, selectors, network calls, DB state, logs, and cleanup from live UI, source, browser network capture, configured logs, and DB.
- **TC references to Playwright spec files are hints, not requirements.** If the TC names a spec path:
  - If the file exists on disk: prefer running it via `npx playwright test` from its repo root.
  - If the file does NOT exist on disk: do NOT mark the case BLOCKED. Drive Playwright directly using the TC body as the test contract. Use `$PWCLI` (`$HOME/.codex/skills/playwright/scripts/playwright_cli.sh`) or write an inline Playwright script under `{output_dir}/ultraqa/{document}/scripts/` to navigate, interact, capture network, and assert the TC's expected UI/API behavior. The TC's 절차/기대 결과/Assertion fields define what to verify; selectors and exact API paths are discovered live from DOM and network capture.
  - Treat `Needs selector` / `Design target` / `Needs source confirmation` cases the same way: try live discovery via DOM/source/network first; only BLOCK after bounded discovery genuinely fails, and only for that case.
- **UNIT-* cases (and any case whose 자동화 대상 / 유형 is a unit test or mock target) MUST be executed by RUNNING the referenced unit test — never auto-SKIP them.** Locate the target test file + method from the TC's `소스 근거` / `대상 테스트 파일` / Assertion fields, find its repo root (the directory holding `gradlew`/`build.gradle`, `pom.xml`, `pytest.ini`/`pyproject.toml`, or `package.json`), and run only that test: e.g. `./gradlew test --tests "*ClassName"` (or `--tests "*ClassName.methodName"`), `mvn -Dtest=ClassName#method test`, `pytest path::test_name`, or `npx jest -t "name"` / `npx vitest run -t "name"`. Map the result to PASS (test green) or FAIL (test red). Put the exact runner command, the suite `tests/failures` count, and the matched method/displayName in the Korean evidence. Mark a UNIT case SKIPPED ONLY if the test file/method genuinely does not exist or no build tool can be located after bounded discovery — and state which was missing. Run the test from the product repo WITHOUT editing product source or product test files.
- Execute non-UNIT cases against the live environment only; no subjective quality scoring unless the TC defines a deterministic oracle. (UNIT-* cases run their repo unit test per the rule above; that is their live execution.)
- **Self-signed cert / TLS**: if the target uses a self-signed cert, direct `curl` fallback MUST use `-k` (insecure), and browser navigation relies on repo-local Playwright config (`.playwright/cli.config.json` with `ignoreHTTPSErrors: true`) or `PLAYWRIGHT_MCP_IGNORE_HTTPS_ERRORS=true` set by the orchestrator. Do not BLOCK a case only on a cert error; use the configured bypass. If a 403 / `Access denied` / missing-function-permission error blocks every call, that is an environment/permission wall the orchestrator must resolve, not a per-case product FAIL — report it as BLOCKED with the exact status/error code.
- Use unique test seed prefixes and clean up only data created by this run.
- If a case cannot be safely executed after bounded discovery, mark only that case BLOCKED with exact evidence.
- This is attempt {attempt}. Treat previous completed case results as final and do not retest them.
- After every case, immediately rewrite progress JSON at `{progress_json}` so timeout can resume safely.
- Frequently rewrite worker context JSON at `{context_json}` with current step, active case id, discovered endpoints/selectors, cleanup status, and last observed error.
- At the end, write the final machine-readable result JSON to `{result_json}`.
- **Screenshots are the preferred evidence form.** For every UI-touching case (UI-*, INT-*, TIMING- with visible state, UI-API integration, error/empty/loading/disabled/banner state), capture at least one Playwright screenshot of the asserted state and save under `{output_dir}/ultraqa/{document}/evidence/{{case-kebab}}-{{label}}.png` (example: `ui001-banner.png`, `ui002-table-empty.png`). Use `fullPage: true` when state spans below the fold. Use `$PWCLI screenshot` or `page.screenshot()`. The case-kebab prefix MUST match the case id (UI-001 → `ui001`, API-003 → `api003`) — files not matching this convention will not auto-embed in the result markdown.
- For API-only cases with visible UI side effect (CRUD row appears/disappears, banner shown), also screenshot the resulting UI state. Pure backend cases without UI side effect may skip screenshots; save the response body as `{{case-kebab}}-body.txt` under the same evidence dir.
- If a UI assertion has no screenshot evidence saved, mark the case BLOCKED with `screenshot missing` rather than PASS.
- Reference the saved screenshot/file paths in the case `evidence` array of the result JSON. Absolute paths under `{output_dir}/ultraqa/{document}/evidence/` are accepted.
- **모든 case 의 `summary` / `failures` / `evidence` 필드는 한국어로 작성한다.** PASS/FAIL/BLOCKED/SKIPPED 같은 상태 enum, HTTP method/path, JSON 필드명, 파일 경로, mongo 컬렉션명, 코드 식별자는 영문 그대로 유지한다. 영어 narrative 는 한국어로 번역해서 적는다. 보고서는 한국어 보고서이다.
- **API-*, INT-*, TIMING-* 케이스는 반드시 API 실행 시간을 밀리초 단위로 측정해 evidence 에 포함**한다. 예: `"API POST /api/items 응답 시간 1234ms (HTTP 200)"`. curl 은 `-w '%{{time_total}}'` 또는 wallclock 측정으로, fetch/Playwright network capture 는 `request.timing()` 또는 `Date.now()` 차이로 측정한다. TIMING-* 케이스는 측정 임계치와 실측값 둘 다 evidence 에 기록한다 (예: `"임계치 2000ms, 실측 187ms — 통과"`). 측정값 없는 API/TIMING 케이스는 BLOCKED 처리한다.
- **앱 로그 원문 증빙**: 케이스의 assertion 이 백엔드 로그/예외/권한 거부/에러 코드(4xx·5xx·AccessDenied·errorCode 등)와 관련되거나, 실패·차단을 검증하는 경우, configured app log 에서 해당 케이스의 요청 시각·endpoint·errorCode 로 관련 윈도우를 grep 해 `{output_dir}/ultraqa/{document}/evidence/{{case-kebab}}-applog.log` 로 저장한다 (예: `ui003-applog.log`, `api002-applog.log`). case-kebab prefix 가 케이스 id 와 일치하는 `.log`/`.txt` evidence 파일은 result 보고서에 코드블럭으로 자동 임베드된다. 주의: app log 는 보통 WARN/ERROR 레벨이라 정상 성공 동작(2xx success)은 로그 라인이 없을 수 있다 — 관련 라인이 실제로 존재할 때만 저장하고, 없으면 생략한다 (빈/무관한 로그 저장 금지). 비밀값은 마스킹한다.

Environment:
- TC root: `{tc_root}`
- TC document: `{doc_tests[0]["feature_file"]}`
- Run output dir: `{output_dir}`
- App URL: `{env_cfg.get("appUrl", "")}`
- API base URL: `{env_cfg.get("apiBaseUrl", "")}`
- Aux URL: `{env_cfg.get("auxUrl", "")}`
- Playwright storage state: `{config.get("auth", {}).get("storageStatePath", "")}`
- Mongo URI env: `{mongo.get("uriEnv", "MONGO_URI")}`
- Mongo database: `{mongo.get("database", "")}`
- Mongosh command: `{mongo.get("mongoshCommand", "mongosh")}`
- App log mode: `{app_log.get("mode", "none")}`
- App log file: `{app_log.get("filePath", "")}`
- Runner worker state: `{state_json}`
- Previous completed cases: {json.dumps(completed, ensure_ascii=False)}
- Previous worker attempts:
```json
{json.dumps(attempts[-3:], ensure_ascii=False, indent=2)}
```

Existing progress snapshot:
```json
{json.dumps(previous, ensure_ascii=False, indent=2)[:12000]}
```

Existing artifact inventory for this TC document:
```text
{artifact_summary}
```

Cases to execute now from `{document}.md`:
```json
{json.dumps(cases, ensure_ascii=False, indent=2)}
```

All cases in this document:
```json
{json.dumps([{"id": test["id"], "title": test["title"], "type": test.get("type", ""), "tc_id": test["tc_id"]} for test in all_doc_tests], ensure_ascii=False, indent=2)}
```

Required progress/final JSON schema:
```json
{{
  "document": "{document}",
  "run_id": "{output_dir.name}",
  "attempt": {attempt},
  "worker_context": {{
    "current_case_id": "",
    "current_step": "",
    "discovered": {{}},
    "cleanup": {{}},
    "last_error": ""
  }},
  "cases": [
    {{
      "id": "{document}/API-001",
      "status": "PASS",
      "summary": "what was tested and observed",
      "duration_s": 12.3,
      "evidence": ["artifact path or concise observed signal"],
      "failures": []
    }}
  ]
}}
```

Status values must be exactly PASS, FAIL, BLOCKED, SKIPPED, or INFRA.
Use INFRA only for runner/backend/tooling failures that prevent a product verdict.
Every case id in "Cases to execute now" must appear exactly once in progress/final JSON once attempted.
Do not remove previous completed cases from progress JSON; append/update the cases array.
"""


def render_blocked_retry_prompt(
    document: str,
    doc_tests: list[dict[str, Any]],
    all_doc_tests: list[dict[str, Any]],
    tc_root: Path,
    output_dir: Path,
    config: dict[str, Any],
    result_json: Path,
    progress_json: Path,
    context_json: Path,
    state_json: Path,
    retry: int,
    max_retries: int,
    blocked_history: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    previous: dict[str, Any],
) -> str:
    base_prompt = render_ultraqa_prompt(
        document=document,
        doc_tests=doc_tests,
        all_doc_tests=all_doc_tests,
        tc_root=tc_root,
        output_dir=output_dir,
        config=config,
        result_json=result_json,
        progress_json=progress_json,
        context_json=context_json,
        state_json=state_json,
        attempt=retry,
        previous=previous,
        attempts=attempts,
    )
    blocked_summary = json.dumps(blocked_history, ensure_ascii=False, indent=2)
    preamble = f"""[자가수복 재시도 {retry}/{max_retries}]

이전 실행에서 BLOCKED 으로 종료된 케이스들의 테스트 전략을 조정해 다시 실행한다.

자가수복 강제 규칙:
- **제품 소스 코드를 절대 수정하지 않는다.** product repository 의 소스/설정/스키마/마이그레이션 파일은 read-only. 한 줄도 편집 금지.
- **TC 마크다운/Playwright spec 등 product repo 의 test 파일도 수정 금지.** 산출물은 오직 `{output_dir}/ultraqa/{document}/` 하위의 evidence/scripts/fixtures 에만 쓴다.
- **조정 가능한 것 (test approach 조정)**: selector 전략 (role/text/data-attr/CSS 대체), endpoint 발견 범위 (controller grep 키워드/디렉토리 확대), source-grep 키워드 추가, alt log source/도커 컨테이너, MongoDB collection alias 후보 확장, seed prefix/timing 변경, auth 재로그인, fixture 경로/내용 (run-dir 안에만), screenshot 캡처 시점/뷰포트, network capture filter 조정, curl 옵션 (-w timing, --max-time), wait 전략 (waitForSelector → networkidle 등), 임의 sleep 추가 (BLOCKED 회피 정당화 가능 시), 재로그인 + 새 storage state.
- 이전 BLOCKED 원인을 먼저 분석하고, 무엇을 다르게 시도할지 evidence 에 한국어로 기록한 뒤 실행한다.
- 조정 후에도 case 가 통과할 수 없으면 BLOCKED 유지하되 시도한 전략 + 남은 차단 원인을 evidence 에 한국어로 명시한다.
- 신규 PASS/FAIL/BLOCKED 결과를 progress.json 의 cases 배열에 append (기존 항목 보존, 같은 id 는 덮어쓰기).

직전 BLOCKED 케이스 + 사유 (이전 attempt 의 summary/failures/evidence):
```json
{blocked_summary}
```

다음 ultraqa 본문 규약은 그대로 적용한다.

"""
    return preamble + base_prompt


def run_omx_ultraqa_worker(prompt: str, final_md: Path, timeout: int, config: dict[str, Any]) -> dict[str, Any]:
    # Legacy inline-worker engine for Codex/OMX hosts. Default flow is host-driven
    # orchestration (prepare-only -> subagents -> finalize); this is only used
    # when --config is run alone without the prepare/finalize phases.
    command = [
        "timeout",
        "--kill-after=30s",
        str(timeout),
        "omx",
        "exec",
        "--cd",
        str(DOCS_ROOT),
        "--ephemeral",
        "--dangerously-bypass-approvals-and-sandbox",
        "-o",
        str(final_md),
        "-",
    ]
    env = os.environ.copy()
    env.update(default_env(config))
    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=str(DOCS_ROOT),
            env=env,
            timeout=timeout + 90,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": completed.returncode in {124, 137},
            "duration_s": time.monotonic() - start,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + f"\nPYTHON_TIMEOUT after {timeout + 90}s\n",
            "timed_out": True,
            "duration_s": time.monotonic() - start,
        }


def summarize_worker_artifacts(doc_dir: Path) -> str:
    if not doc_dir.exists():
        return "(no previous artifacts)"
    lines: list[str] = []
    for path in sorted(doc_dir.rglob("*"))[:120]:
        if path.is_dir():
            continue
        try:
            rel = path.relative_to(doc_dir)
        except ValueError:
            rel = path
        size = path.stat().st_size
        lines.append(f"- {rel} ({size} bytes)")
    for name in ("worker-context.json", "worker-state.json", "stdout.log", "stderr.log", "final.md", "prompt.md"):
        path = doc_dir / name
        if path.exists() and path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")[:2000]
            lines.extend(["", f"## excerpt: {name}", text])
    return "\n".join(lines) if lines else "(no previous artifacts)"


def best_ultraqa_progress(result_json: Path, progress_json: Path) -> dict[str, Any]:
    result, result_error = load_ultraqa_result_json(result_json)
    progress, progress_error = load_ultraqa_result_json(progress_json)
    candidates = []
    if not result_error:
        candidates.append(result)
    if not progress_error:
        candidates.append(progress)
    if candidates:
        return max(candidates, key=lambda item: len(terminal_case_ids(item)))
    if not progress_error:
        return progress
    return {"cases": []}


def terminal_case_ids(parsed: dict[str, Any]) -> set[str]:
    statuses = {"PASS", "FAIL", "BLOCKED", "SKIPPED", "INFRA"}
    return {
        str(case.get("id"))
        for case in parsed.get("cases", [])
        if isinstance(case, dict) and str(case.get("status", "")).upper() in statuses and case.get("id")
    }


def pending_ultraqa_tests(doc_tests: list[dict[str, Any]], parsed: dict[str, Any]) -> list[dict[str, Any]]:
    done = terminal_case_ids(parsed)
    return [test for test in doc_tests if test["id"] not in done]


def blocked_cases_detail(parsed: dict[str, Any], doc_tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    title_lookup = {test["id"]: test.get("title", "") for test in doc_tests}
    out: list[dict[str, Any]] = []
    for case in parsed.get("cases", []) or []:
        if not isinstance(case, dict):
            continue
        if str(case.get("status", "")).upper() != "BLOCKED":
            continue
        case_id = str(case.get("id", ""))
        if not case_id:
            continue
        out.append(
            {
                "id": case_id,
                "title": case.get("title") or title_lookup.get(case_id, ""),
                "summary": case.get("summary", ""),
                "failures": case.get("failures", []) or [],
                "evidence": case.get("evidence", []) or [],
            }
        )
    return out


def evict_cases_from_progress(parsed: dict[str, Any], case_ids: set[str]) -> dict[str, Any]:
    if not case_ids:
        return parsed
    new_cases = [
        case
        for case in parsed.get("cases", []) or []
        if not (isinstance(case, dict) and str(case.get("id", "")) in case_ids)
    ]
    out = dict(parsed)
    out["cases"] = new_cases
    return out


def classify_worker_outcome(worker: dict[str, Any], parsed: dict[str, Any], pending_tests: list[dict[str, Any]]) -> str:
    if not pending_tests:
        return "complete"
    if not terminal_case_ids(parsed) and INFRA_SIGNATURE_RE.search(str(worker.get("stderr", ""))):
        # Worker backend died (quota/auth/connection/non-zero exit) before any case progress.
        # Strategy adjustment cannot fix this — do not waste continuation budget retrying.
        return "worker_infra_failure_non_retryable"
    if worker.get("timed_out"):
        if terminal_case_ids(parsed):
            return "timeout_with_progress_continue_remaining"
        return "timeout_without_case_progress_retry_with_context"
    if int(worker.get("returncode", 1)) != 0:
        if terminal_case_ids(parsed):
            return "worker_error_with_progress_continue_remaining"
        return "worker_error_without_progress_retry_with_context"
    return "incomplete_result_continue_remaining"


def write_worker_state(
    path: Path,
    document: str,
    attempt: int,
    max_continuations: int,
    attempts: list[dict[str, Any]],
    parsed: dict[str, Any],
    pending_tests: list[dict[str, Any]],
    state: str,
) -> None:
    payload = {
        "document": document,
        "updated_at": current_kst_iso(),
        "attempt": attempt,
        "max_continuations": max_continuations,
        "state": state,
        "completed_case_ids": sorted(terminal_case_ids(parsed)),
        "pending_case_ids": [test["id"] for test in pending_tests],
        "attempts": attempts,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def attempts_stderr_tail(attempts: list[dict[str, Any]], limit: int = 8000) -> str:
    if not attempts:
        return ""
    path_text = attempts[-1].get("stderr", "")
    if not path_text:
        return ""
    path = Path(path_text)
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError:
        return ""


def add_synthetic_unfinished_cases(
    parsed: dict[str, Any],
    pending_tests: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    reason: str,
    forced_status: str | None = None,
) -> dict[str, Any]:
    cases = [case for case in parsed.get("cases", []) if isinstance(case, dict)]
    by_id = {str(case.get("id")) for case in cases}
    last_attempt = attempts[-1] if attempts else {}
    if forced_status:
        status = forced_status
    else:
        had_progress = bool(terminal_case_ids(parsed))
        infra = (not had_progress) and (
            "infra" in (reason or "").lower()
            or INFRA_SIGNATURE_RE.search(attempts_stderr_tail(attempts)) is not None
        )
        if infra:
            # Worker/infra failure (quota, auth, connection, non-zero exit) — not a product FAIL.
            status = "INFRA"
        else:
            # The worker never produced a result for this case, so it was never executed.
            # An unexecuted case is a test-side gap (BLOCKED), never a product FAIL — whether
            # the worker timed out or just ran out of continuation budget. FAIL is reserved for
            # cases the product was actually exercised against and failed an assertion.
            status = "BLOCKED"
    summary = (
        "Worker/infra failure before this case could run (quota/auth/connection/crash); not a product failure."
        if status == "INFRA"
        else "UltraQA worker could not complete this case within the configured continuation budget; case was not executed."
    )
    for test in pending_tests:
        if test["id"] in by_id:
            continue
        cases.append(
            {
                "id": test["id"],
                "status": status,
                "summary": summary,
                "duration_s": 0,
                "evidence": [last_attempt.get("stdout", ""), last_attempt.get("stderr", ""), last_attempt.get("final", "")],
                "failures": [reason or "unfinished after continuation budget"],
            }
        )
    merged = dict(parsed)
    merged["cases"] = cases
    merged["unfinished_reason"] = reason
    merged["attempts"] = attempts
    return merged


def render_worker_final_summary(
    document: str,
    attempts: list[dict[str, Any]],
    parsed: dict[str, Any],
    progress_json: Path,
    context_json: Path,
    state_json: Path,
) -> str:
    counts: dict[str, int] = {}
    for case in parsed.get("cases", []):
        if isinstance(case, dict):
            status = str(case.get("status", "UNKNOWN")).upper()
            counts[status] = counts.get(status, 0) + 1
    lines = [
        f"# UltraQA Worker Summary - {document}",
        "",
        f"- Attempts: {len(attempts)}",
        f"- Progress JSON: `{progress_json}`",
        f"- Worker context JSON: `{context_json}`",
        f"- Worker state JSON: `{state_json}`",
        "",
        "## Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Attempts", ""])
    for attempt in attempts:
        lines.append(
            f"- attempt {attempt.get('attempt')}: exit={attempt.get('exit_code')} timeout={attempt.get('timed_out')} duration={attempt.get('duration_s')}s"
        )
    return "\n".join(lines) + "\n"


def load_ultraqa_result_json(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.exists():
        return {}, f"missing {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, str(exc)
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        return {}, "top-level object with cases[] is required"
    return data, None


def ultraqa_results_to_test_results(
    doc_tests: list[dict[str, Any]],
    parsed: dict[str, Any],
    duration: float,
    exit_code: int,
    stdout_path: Path,
    stderr_path: Path,
    final_md: Path,
    result_json: Path,
) -> list[TestResult]:
    by_id = {str(case.get("id")): case for case in parsed.get("cases", []) if isinstance(case, dict)}
    results: list[TestResult] = []
    for test in doc_tests:
        case = by_id.get(test["id"])
        if not case:
            results.append(
                TestResult(
                    id=test["id"],
                    title=test["title"],
                    lane="ultraqa",
                    status="BLOCKED",
                    duration_s=duration,
                    exit_code=exit_code,
                    stdout_path=str(stdout_path),
                    stderr_path=str(stderr_path),
                    failures=[
                        f"ultraqa result missing case {test['id']}; case was not executed, not a product failure",
                        f"Final: {final_md}",
                        f"Result JSON: {result_json}",
                    ],
                )
            )
            continue
        status = str(case.get("status", "FAIL")).upper()
        if status not in {"PASS", "FAIL", "BLOCKED", "SKIPPED", "INFRA"}:
            status = "FAIL"
        failures = normalize_ultraqa_failures(case)
        evidence = normalize_ultraqa_evidence(case)
        if status != "PASS" and evidence:
            failures.extend(f"Evidence: {item}" for item in evidence)
        if status != "PASS":
            failures.extend([f"Final: {final_md}", f"Result JSON: {result_json}"])
        results.append(
            TestResult(
                id=test["id"],
                title=test["title"],
                lane="ultraqa",
                status=status,
                duration_s=float(case.get("duration_s") or duration),
                exit_code=exit_code,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                failures=failures,
            )
        )
    return results


def normalize_ultraqa_failures(case: dict[str, Any]) -> list[str]:
    failures = case.get("failures", [])
    if isinstance(failures, str):
        failures = [failures]
    if not isinstance(failures, list):
        failures = [str(failures)]
    summary = case.get("summary")
    result = [str(item) for item in failures if item]
    if summary and case.get("status") != "PASS":
        result.insert(0, str(summary))
    return result


def normalize_ultraqa_evidence(case: dict[str, Any]) -> list[str]:
    evidence = case.get("evidence", [])
    if isinstance(evidence, str):
        return [evidence]
    if isinstance(evidence, list):
        return [str(item) for item in evidence if item]
    return []


def group_tests_by_document(tests: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for test in tests:
        grouped.setdefault(test["feature"], []).append(test)
    return grouped


def build_manifest(
    tests: list[dict[str, Any]],
    run_id: str,
    output_dir: Path,
    config: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    manifest_tests = [build_manifest_entry(test, output_dir, config, args) for test in tests]
    return {
        "run_id": run_id,
        "generated_at": current_kst_iso(),
        "environment": redacted_environment(config),
        "tests": manifest_tests,
    }


def build_manifest_entry(
    test: dict[str, Any],
    output_dir: Path,
    config: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    status = test["status"]
    if status != "Ready" and status not in {"Needs selector", "Needs source confirmation", "Design target"}:
        return skipped(test, f"unsupported automation status: {status}", "BLOCKED")

    target = test["target"]
    if MOCK_TARGET_RE.search(target):
        return skipped(test, "mock/unit target is not live functional execution; regenerate TC", "BLOCKED")
    if MUTATING_RE.search(test["section"]) and "mongodb" not in test["section"].casefold():
        return skipped(test, "mutating live TC is missing MongoDB consistency/cleanup predicate", "BLOCKED")

    tc_id = test["tc_id"]
    if tc_id.startswith("API-") or "curl" in target.casefold():
        entry = curl_entry(test, config)
        if entry:
            return entry
    if "playwright" in target.casefold() or tc_id.startswith(("UI-", "INT-", "TIMING-")):
        entry = playwright_entry(test, output_dir, config)
        if entry:
            return entry
    if status == "Design target":
        return skipped(test, "design target has no live executable target in TC", "BLOCKED")
    if status == "Needs selector":
        return skipped(test, "selector gap and no live executable command could be derived from TC", "BLOCKED")
    if status == "Needs source confirmation":
        return skipped(test, "source confirmation gap and no live executable command could be derived from TC", "BLOCKED")
    return skipped(test, "no live executable command could be derived from TC", "BLOCKED")


def curl_entry(test: dict[str, Any], config: dict[str, Any]) -> dict[str, Any] | None:
    method = normalize_method(test.get("method") or "")
    path = normalize_api_path(test.get("api_path") or "")
    if not method or not path:
        return None
    auth = config.get("auth", {})
    body = request_to_json(test.get("request") or "")
    body_arg = f" -d '{body}'" if body else ""
    auth_prefix = ""
    auth_header = ""
    if auth.get("required", False):
        token_env = auth.get("tokenEnv", "FUNC_TC_TOKEN")
        auth_prefix = f'if [ -z "${{{token_env}:-}}" ]; then echo "{token_env} is required for live curl API"; exit 42; fi; '
        auth_header = f'-H "Authorization: Bearer ${token_env}" '
    command = [
        "bash",
        "-lc",
        (
            f"{auth_prefix}"
            f'curl -sS -X {method} "$FUNC_TC_API_URL{path}" '
            f'{auth_header}-H "Content-Type: application/json"{body_arg} '
            '-w "\\n%{http_code}"'
        ),
    ]
    expected_status = extract_http_status(test.get("response") or "") or 200
    return base_entry(
        test,
        lane="api",
        command=command,
        cwd=DOCS_ROOT,
        timeout=45,
        config=config,
        expect={"exit_code": 0, "http_status": expected_status},
    )


def playwright_entry(test: dict[str, Any], output_dir: Path, config: dict[str, Any]) -> dict[str, Any] | None:
    test_file = test.get("test_file")
    if not test_file:
        return skipped(test, "Playwright spec path not specified in TC; use --engine ultraqa to drive Playwright directly from TC context", "BLOCKED")
    resolved = resolve_repo_file(test_file)
    if not resolved or not resolved.exists():
        return skipped(test, f"Playwright spec file does not exist: {test_file} — use --engine ultraqa to drive Playwright directly from TC context (TC body becomes the contract; selectors discovered live)", "BLOCKED")
    if not is_playwright_spec(resolved):
        return skipped(test, f"not a Playwright live spec: {test_file}", "BLOCKED")
    repo = repo_for_path(resolved)
    if not repo:
        return skipped(test, f"cannot determine repo for {resolved}", "BLOCKED")
    marker = re.sub(r"[^A-Za-z0-9_.-]+", "_", test["id"])
    rel = resolved.relative_to(repo)
    log_prefix = log_sidecar_prefix(config, output_dir, marker)
    log_suffix = log_sidecar_suffix(config)
    command = [
        "bash",
        "-lc",
        (
            f"{log_prefix}"
            f'TEST_MARKER="{marker}" PLAYWRIGHT_HTML_REPORT="{output_dir}/playwright-report/{marker}" '
            f"npx playwright test {rel} --trace on; STATUS=$?; "
            f"{log_suffix}"
            "exit $STATUS"
        ),
    ]
    lane = "ui-api" if has_integration_evidence(test["section"]) else "ui"
    return base_entry(test, lane=lane, command=command, cwd=repo, timeout=300, config=config)


def log_sidecar_prefix(config: dict[str, Any], output_dir: Path, marker: str) -> str:
    app_log = config.get("logs", {}).get("app", {})
    mode = app_log.get("mode", "none")
    log_dir = output_dir / "logs"
    log_file = log_dir / f"app-{marker}.log"
    if mode == "file" and app_log.get("filePath"):
        return f'mkdir -p "{log_dir}"; (timeout 360s tail -F "{app_log["filePath"]}" > "{log_file}" 2>&1) & LOG_PID=$!; '
    if mode == "docker" and app_log.get("dockerContainer"):
        container = app_log["dockerContainer"]
        return f'mkdir -p "{log_dir}"; (timeout 360s docker logs -f "{container}" > "{log_file}" 2>&1) & LOG_PID=$!; '
    if mode == "command" and app_log.get("command"):
        command = app_log["command"]
        return f'mkdir -p "{log_dir}"; (timeout 360s bash -lc {json.dumps(command)} > "{log_file}" 2>&1) & LOG_PID=$!; '
    return ""


def log_sidecar_suffix(config: dict[str, Any]) -> str:
    mode = config.get("logs", {}).get("app", {}).get("mode", "none")
    return 'if [ -n "${LOG_PID:-}" ]; then kill "$LOG_PID" 2>/dev/null || true; fi; ' if mode != "none" else ""


def has_integration_evidence(section: str) -> bool:
    text = section.casefold()
    return "network" in text or "api" in text or "mongodb" in text or "통합" in section


def base_entry(
    test: dict[str, Any],
    lane: str,
    command: list[str],
    cwd: Path,
    timeout: int,
    config: dict[str, Any],
    expect: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": test["id"],
        "title": test["title"],
        "lane": lane,
        "command": command,
        "cwd": str(cwd),
        "timeout": timeout,
        "expect": expect or {"exit_code": 0},
        "env": default_env(config),
    }


def skipped(test: dict[str, Any], reason: str, status: str) -> dict[str, Any]:
    return {
        "id": test["id"],
        "title": test["title"],
        "lane": infer_lane(test),
        "skip": True,
        "skip_status": status,
        "skip_reason": reason,
    }


def default_env(config: dict[str, Any]) -> dict[str, str]:
    env_cfg = config.get("environment", {})
    mongo = config.get("mongodb", {})
    auth = config.get("auth", {})
    env = {
        "FUNC_TC_APP_URL": env_cfg.get("appUrl", ""),
        "FUNC_TC_API_URL": env_cfg.get("apiBaseUrl", ""),
        "FUNC_TC_AUX_URL": env_cfg.get("auxUrl", ""),
        "FUNC_TC_STORAGE_STATE": auth.get("storageStatePath", ""),
        "TC_ENVIRONMENT_TYPE": env_cfg.get("type", ""),
        "TC_TEST_LIVE_ONLY": "1",
        "MONGO_DATABASE": mongo.get("database", ""),
        "MONGOSH_COMMAND": mongo.get("mongoshCommand", "mongosh"),
    }
    uri_env = mongo.get("uriEnv", "MONGO_URI")
    if uri_env and os.environ.get(uri_env):
        env["MONGO_URI"] = os.environ[uri_env]
    return env


def redacted_environment(config: dict[str, Any]) -> dict[str, Any]:
    env = config.get("environment", {}).copy()
    mongo = config.get("mongodb", {})
    return {
        "environment": env,
        "mongodb": {
            "uriEnv": mongo.get("uriEnv", "MONGO_URI"),
            "database": mongo.get("database", ""),
            "collections": mongo.get("collections", {}),
        },
        "logs": config.get("logs", {}),
        "auth": {
            "required": config.get("auth", {}).get("required", False),
            "usernameEnv": config.get("auth", {}).get("usernameEnv", "FUNC_TC_USER"),
            "passwordEnv": config.get("auth", {}).get("passwordEnv", "FUNC_TC_PASSWORD"),
            "tokenEnv": config.get("auth", {}).get("tokenEnv", "FUNC_TC_TOKEN"),
        },
    }


def find_value(section: str, label: str) -> str | None:
    match = re.search(rf"^-\s+{re.escape(label)}:\s*(.+)$", section, re.MULTILINE)
    return match.group(1).strip() if match else None


def extract_test_file(section: str) -> str | None:
    patterns = [
        r"대상 테스트 파일\s*`([^`]+)`",
        r"대상 테스트 파일:\s*`([^`]+)`",
        r"대상 테스트 파일\s+`([^`]+)`",
    ]
    for pattern in patterns:
        match = re.search(pattern, section)
        if match:
            return match.group(1)
    return None


def extract_inline(section: str, label: str) -> str | None:
    match = re.search(rf"{re.escape(label)}\s*`([^`]+)`", section)
    if match:
        return match.group(1)
    match = re.search(rf"{re.escape(label)}\s*[:：]\s*([^;\n]+)", section)
    if match:
        return match.group(1).strip()
    return None


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


def infer_lane(test: dict[str, Any]) -> str:
    target = test.get("target", "").casefold()
    tc_id = test.get("tc_id", "")
    if "playwright" in target or tc_id.startswith(("UI-", "TIMING-")):
        return "ui"
    if tc_id.startswith("INT-"):
        return "ui-api"
    if "curl" in target or tc_id.startswith("API-"):
        return "api"
    if MOCK_TARGET_RE.search(test.get("target", "")):
        return "blocked"
    return "api"


def resolve_repo_file(path_text: str) -> Path | None:
    path_text = path_text.strip()
    path = Path(path_text)
    if path.is_absolute():
        return path
    parts = path.parts
    if parts and parts[0] in REPO_ROOTS:
        return REPO_ROOTS[parts[0]] / Path(*parts[1:])
    candidate = DOCS_ROOT / path
    if candidate.exists():
        return candidate
    for repo in REPO_ROOTS.values():
        candidate = repo / path
        if candidate.exists():
            return candidate
    return None


def is_playwright_spec(path: Path) -> bool:
    return bool(PLAYWRIGHT_SPEC_RE.search(path.name))


def repo_for_path(path: Path) -> Path | None:
    resolved = path.resolve()
    for repo in REPO_ROOTS.values():
        try:
            resolved.relative_to(repo)
            return repo
        except ValueError:
            continue
    return None


def normalize_method(value: str) -> str | None:
    value = value.upper()
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        if method in value:
            return method
    return None


def normalize_api_path(value: str) -> str | None:
    match = re.search(r"(/api/[A-Za-z0-9_./{}-]+)", value)
    if not match:
        return None
    return match.group(1)


def request_to_json(value: str) -> str | None:
    value = value.strip()
    match = re.search(r"(\{.*\})", value)
    if not match:
        return None
    return match.group(1).replace("'", '"')


def extract_http_status(value: str) -> int | None:
    match = re.search(r"HTTP\s+(\d{3})", value)
    return int(match.group(1)) if match else None


def print_summary(manifest: dict[str, Any]) -> None:
    counts: dict[str, int] = {}
    for test in manifest["tests"]:
        key = test.get("skip_status") if test.get("skip") else f"RUN:{test.get('lane', 'unknown')}"
        counts[key] = counts.get(key, 0) + 1
    print("SUMMARY=" + json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
