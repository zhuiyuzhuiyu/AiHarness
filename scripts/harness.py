#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
SPECS_DIR = ROOT / "specs"
CONFIG_PATH = ROOT / ".aiharness" / "config.json"

PROJECT_DOC_CANDIDATES = [
    ".docs/ARCHITECTURE.md",
    ".docs/SECURITY.md",
    ".docs/CODING_GUIDELINES.md",
    ".docs/docs.md",
    "ARCHITECTURE.md",
    "SECURITY.md",
    "CODING_GUIDELINES.md",
    "docs.md",
]

RISK_PATTERNS = {
    "security": [
        "auth",
        "permission",
        "secret",
        "token",
        "oauth",
        "security",
        "credential",
        "session",
        "privacy",
    ],
    "billing": [
        "billing",
        "payment",
        "invoice",
        "refund",
        "subscription",
    ],
    "migration": [
        "migration",
        "schema",
        "ddl",
        "seed",
        "backfill",
        "database",
        "db/",
    ],
    "infrastructure": [
        "deploy",
        "terraform",
        "infra",
        "k8s",
        "helm",
        "docker",
        "cloudbuild",
        ".github/workflows",
    ],
}

DOC_UPDATE_HINTS = {
    "README.md": ["README.md"],
    ".docs/ARCHITECTURE.md": [
        "src/",
        "app/",
        "server/",
        "api/",
        "services/",
        "workers/",
        "infra/",
    ],
    ".docs/SECURITY.md": [
        "auth",
        "permission",
        "secret",
        "oauth",
        "token",
        "middleware",
    ],
    ".docs/CODING_GUIDELINES.md": [
        "lint",
        "eslint",
        "prettier",
        "formatter",
        "tsconfig",
        "pyproject.toml",
    ],
    ".docs/docs.md": [
        "docs/",
        "features/",
        "pages/",
        "routes/",
    ],
}


DEFAULT_CONFIG: dict[str, Any] = {
    "language": {
        "default": "zh-CN",
        "fallback": "zh-CN",
        "instruction": "默认使用中文编写 skill 描述、命令说明、测试报告、review 结论和对用户的回答，除非用户明确要求其他语言。",
    },
    "review": {
        "commands": [
            {
                "name": "example-review",
                "enabled": False,
                "command": "npm run lint",
                "description": "示例 review 命令。按项目替换成真实 lint/typecheck/review 命令。",
            }
        ]
    },
    "verify": {
        "commands": [
            {
                "name": "example-unit",
                "enabled": False,
                "command": "npm test",
                "description": "示例单元测试命令。按项目替换成真实 jest/pytest 命令。",
            },
            {
                "name": "example-e2e",
                "enabled": False,
                "command": "npx playwright test",
                "description": "示例 e2e 命令。按项目替换成真实 Playwright 命令。",
            },
        ]
    },
}


@dataclass(frozen=True)
class SpecPaths:
    root: Path
    requirements: Path
    design: Path
    tasks: Path
    review: Path
    test_report: Path
    handoff: Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValueError("slug cannot be empty")
    return slug


def spec_dir(slug: str, stamp: str) -> SpecPaths:
    root = SPECS_DIR / slug / stamp
    return SpecPaths(
        root=root,
        requirements=root / "requirements.md",
        design=root / "design.md",
        tasks=root / "tasks.md",
        review=root / "review.md",
        test_report=root / "test-report.md",
        handoff=root / "handoff.md",
    )


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with path.open() as f:
        return json.load(f)


def config() -> dict[str, Any]:
    return read_json(CONFIG_PATH)


def language_instruction() -> str:
    return config().get("language", {}).get("instruction", DEFAULT_CONFIG["language"]["instruction"])


def write_text(path: Path, content: str, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists. Pass --force to overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def ensure_file(path: Path, content: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def load_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text().rstrip() + "\n"


def project_docs() -> list[str]:
    return [candidate for candidate in PROJECT_DOC_CANDIDATES if (ROOT / candidate).exists()]


def git_changed_files() -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    changed: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        changed.append(line[3:].strip())
    return changed


def collect_risks(changed_files: Iterable[str]) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {}
    for rel_path in changed_files:
        lower = rel_path.lower()
        for risk, patterns in RISK_PATTERNS.items():
            if any(pattern in lower for pattern in patterns):
                findings.setdefault(risk, []).append(rel_path)
    return findings


def doc_drift_hints(changed_files: Iterable[str]) -> dict[str, list[str]]:
    hints: dict[str, list[str]] = {}
    for rel_path in changed_files:
        lower = rel_path.lower()
        for doc, patterns in DOC_UPDATE_HINTS.items():
            if any(pattern.lower() in lower for pattern in patterns):
                hints.setdefault(doc, []).append(rel_path)
    return hints


def format_frontmatter(title: str, source: str, docs: list[str]) -> str:
    lines = [
        "---",
        f"title: {title}",
        f"source: {source}",
        f"generated_on: {date.today().isoformat()}",
        "project_docs:",
    ]
    if docs:
        lines.extend(f"  - {entry}" for entry in docs)
    else:
        lines.append("  - none-found")
    lines.extend(
        [
            "language:",
            f"  - {config().get('language', {}).get('default', 'zh-CN')}",
            "---\n",
        ]
    )
    return "\n".join(lines)


def intake_content(title: str, source: str) -> str:
    frontmatter = format_frontmatter(title, source, project_docs())
    body = load_template("requirements.template.md")
    body += f"\n## 语言约束\n\n- {language_instruction()}\n"
    body += f"\n## 备注\n\n- 需求标题：{title}\n- 需求来源：{source}\n"
    return frontmatter + body


def design_content(spec: SpecPaths) -> str:
    frontmatter = format_frontmatter("设计", str(spec.requirements.relative_to(ROOT)), project_docs())
    body = load_template("design.template.md")
    body += (
        "\n## 输入\n\n"
        f"- 需求文档：`{spec.requirements.relative_to(ROOT)}`\n"
        f"- 已加载项目文档：{', '.join(project_docs()) or 'none-found'}\n"
        f"- 语言约束：{language_instruction()}\n"
    )
    return frontmatter + body


def tasks_content(spec: SpecPaths) -> str:
    frontmatter = format_frontmatter("任务拆解", str(spec.design.relative_to(ROOT)), project_docs())
    body = load_template("tasks.template.md")
    body += (
        "\n## 建议执行顺序\n\n"
        "1. 先做最小可 review 的切片。\n"
        "2. 先跑最小验证，再扩大测试范围。\n"
        "3. review 后修复确认问题。\n"
        "4. 收尾时补文档和交付记录。\n"
    )
    return frontmatter + body


def command_specs(section: str) -> list[dict[str, Any]]:
    entries = config().get(section, {}).get("commands", [])
    return [entry for entry in entries if isinstance(entry, dict)]


def enabled_command_specs(section: str) -> list[dict[str, Any]]:
    return [entry for entry in command_specs(section) if entry.get("enabled")]


def run_shell_command(command: str) -> dict[str, Any]:
    result = subprocess.run(
        command,
        shell=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "status": "passed" if result.returncode == 0 else "failed",
    }


def execute_configured_commands(section: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for entry in enabled_command_specs(section):
        outcome = run_shell_command(entry["command"])
        outcome["name"] = entry.get("name", entry["command"])
        outcome["description"] = entry.get("description", "")
        results.append(outcome)
    return results


def review_content(spec: SpecPaths, findings: dict[str, list[str]], command_results: list[dict[str, Any]]) -> str:
    lines = [
        "# Review",
        "",
        "## 摘要",
        "",
        "- 审查人：待补充",
        f"- 需求文档：`{spec.requirements.relative_to(ROOT)}`",
        f"- 设计文档：`{spec.design.relative_to(ROOT)}`",
        f"- 任务文档：`{spec.tasks.relative_to(ROOT)}`",
        f"- 语言约束：{language_instruction()}",
        "",
        "## 自动审查结果",
        "",
    ]
    if not command_results:
        lines.append("- 当前未启用真实 review 命令，请在 `.aiharness/config.json` 中开启。")
    else:
        for result in command_results:
            lines.append(f"- `{result['name']}`: {result['status']} (`{result['command']}`)")
    lines.extend(["", "## 风险提示", ""])
    if not findings:
        lines.append("- 当前没有命中文件级风险规则。")
    else:
        for risk, files in findings.items():
            lines.append(f"- `{risk}`: {', '.join(files)}")
    lines.extend(["", "## 处置", "", "- 待补充人工 review 结论"])
    return "\n".join(lines) + "\n"


def test_report_content(changed_files: list[str], command_results: list[dict[str, Any]]) -> str:
    lines = [
        "# 测试报告",
        "",
        "## 语言约束",
        "",
        f"- {language_instruction()}",
        "",
        "## 已执行命令",
        "",
    ]
    if not command_results:
        lines.append("- 当前未启用真实 verify 命令，请在 `.aiharness/config.json` 中开启。")
    else:
        for result in command_results:
            lines.append(f"- `{result['name']}`: {result['status']} (`{result['command']}`)")
    lines.extend(["", "## 变更文件", ""])
    if changed_files:
        lines.extend(f"- `{path}`" for path in changed_files)
    else:
        lines.append("- 当前未检测到变更文件。")
    lines.extend(["", "## 结果说明", "", "- 待补充测试结论"])
    return "\n".join(lines) + "\n"


def handoff_content(spec: SpecPaths) -> str:
    return (
        "# 交付说明\n\n"
        "## 交付内容\n\n"
        "- 待补充\n\n"
        "## 语言约束\n\n"
        f"- {language_instruction()}\n\n"
        "## 关联文档\n\n"
        f"- 需求文档：`{spec.requirements.relative_to(ROOT)}`\n"
        f"- 设计文档：`{spec.design.relative_to(ROOT)}`\n"
        f"- 任务文档：`{spec.tasks.relative_to(ROOT)}`\n"
        f"- Review：`{spec.review.relative_to(ROOT)}`\n"
        f"- 测试报告：`{spec.test_report.relative_to(ROOT)}`\n\n"
        "## 后续事项\n\n"
        "- 待补充\n"
    )


def print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def build_stamp(explicit_date: str | None, iteration: str) -> str:
    base = explicit_date or date.today().isoformat()
    return f"{base}-{iteration}"


def cmd_spec_intake(args: argparse.Namespace) -> int:
    slug = slugify(args.slug or args.title)
    spec = spec_dir(slug, build_stamp(args.date, args.iteration))
    write_text(spec.requirements, intake_content(args.title, args.source), force=args.force)
    print_json(
        {
            "command": "spec-intake",
            "spec_root": str(spec.root.relative_to(ROOT)),
            "requirements": str(spec.requirements.relative_to(ROOT)),
            "project_docs": project_docs(),
            "language": config().get("language", {}).get("default", "zh-CN"),
        }
    )
    return 0


def cmd_spec_design(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    if not spec.requirements.exists():
        print(f"missing requirements: {spec.requirements.relative_to(ROOT)}", file=sys.stderr)
        return 1
    write_text(spec.design, design_content(spec), force=args.force)
    print_json({"command": "spec-design", "design": str(spec.design.relative_to(ROOT))})
    return 0


def cmd_spec_plan(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    if not spec.design.exists():
        print(f"missing design: {spec.design.relative_to(ROOT)}", file=sys.stderr)
        return 1
    write_text(spec.tasks, tasks_content(spec), force=args.force)
    print_json({"command": "spec-plan", "tasks": str(spec.tasks.relative_to(ROOT))})
    return 0


def cmd_spec_build(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    if not spec.tasks.exists():
        print(f"missing tasks: {spec.tasks.relative_to(ROOT)}", file=sys.stderr)
        return 1
    payload = {
        "command": "spec-build",
        "tasks": str(spec.tasks.relative_to(ROOT)),
        "next_step": "按 tasks.md 先实现最高优先级切片，改完后执行 ./hooks/post-edit/run。",
        "language": config().get("language", {}).get("default", "zh-CN"),
    }
    print_json(payload)
    return 0


def cmd_spec_review(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    changed = git_changed_files()
    findings = collect_risks(changed)
    command_results = execute_configured_commands("review")
    write_text(spec.review, review_content(spec, findings, command_results), force=args.force)
    failed = [result for result in command_results if result["returncode"] != 0]
    print_json(
        {
            "command": "spec-review",
            "review": str(spec.review.relative_to(ROOT)),
            "changed_files": changed,
            "risk_findings": findings,
            "command_results": command_results,
            "failed": [result["name"] for result in failed],
        }
    )
    return 1 if failed else 0


def cmd_spec_verify(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    changed = git_changed_files()
    command_results = execute_configured_commands("verify")
    write_text(spec.test_report, test_report_content(changed, command_results), force=args.force)
    failed = [result for result in command_results if result["returncode"] != 0]
    print_json(
        {
            "command": "spec-verify",
            "test_report": str(spec.test_report.relative_to(ROOT)),
            "changed_files": changed,
            "command_results": command_results,
            "failed": [result["name"] for result in failed],
        }
    )
    return 1 if failed else 0


def cmd_spec_close(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    ensure_file(spec.handoff, handoff_content(spec))
    print_json({"command": "spec-close", "handoff": str(spec.handoff.relative_to(ROOT))})
    return 0


def cmd_hook_pre_task(_: argparse.Namespace) -> int:
    docs = project_docs()
    payload = {
        "hook": "pre-task",
        "project_docs": docs,
        "status": "ready" if docs else "warning",
        "language": config().get("language", {}).get("default", "zh-CN"),
    }
    if not docs:
        payload["message"] = "当前仓库未发现 .docs/ 或根目录项目规范文档。"
    print_json(payload)
    return 0 if docs else 2


def cmd_hook_post_edit(_: argparse.Namespace) -> int:
    changed = git_changed_files()
    payload = {
        "hook": "post-edit",
        "changed_files": changed,
        "risk_findings": collect_risks(changed),
        "doc_drift_hints": doc_drift_hints(changed),
    }
    print_json(payload)
    return 0


def cmd_hook_pre_review(_: argparse.Namespace) -> int:
    changed = git_changed_files()
    payload = {
        "hook": "pre-review",
        "changed_files": changed,
        "ready": bool(changed),
    }
    if not changed:
        payload["message"] = "当前没有可 review 的 diff。"
    print_json(payload)
    return 0 if changed else 2


def cmd_hook_pre_verify(_: argparse.Namespace) -> int:
    changed = git_changed_files()
    verification_plan = {
        "targeted": ["优先执行变更模块对应的单测或 spec。"],
        "broader": ["跨模块修改时追加集成测试。"],
        "browser": ["如果改动涉及 UI，再执行 Playwright 或远程调试验证。"]
        if any(part in path.lower() for path in changed for part in ("ui", "page", "component", "frontend"))
        else [],
        "configured_commands": enabled_command_specs("verify"),
    }
    print_json({"hook": "pre-verify", "changed_files": changed, "verification_plan": verification_plan})
    return 0


def cmd_hook_pre_close(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    payload = {
        "hook": "pre-close",
        "review_exists": spec.review.exists(),
        "test_report_exists": spec.test_report.exists(),
        "handoff_exists": spec.handoff.exists(),
        "doc_drift_hints": doc_drift_hints(git_changed_files()),
    }
    print_json(payload)
    return 0


def cmd_show_config(_: argparse.Namespace) -> int:
    print_json(config())
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="AI Harness command and hook runner")
    sub = root.add_subparsers(dest="command", required=True)

    intake = sub.add_parser("spec-intake", help="Create requirements.md")
    intake.add_argument("--title", required=True)
    intake.add_argument("--source", default="manual")
    intake.add_argument("--slug")
    intake.add_argument("--date")
    intake.add_argument("--iteration", default="v1")
    intake.add_argument("--force", action="store_true")
    intake.set_defaults(func=cmd_spec_intake)

    design = sub.add_parser("spec-design", help="Create design.md")
    design.add_argument("--slug", required=True)
    design.add_argument("--date")
    design.add_argument("--iteration", default="v1")
    design.add_argument("--force", action="store_true")
    design.set_defaults(func=cmd_spec_design)

    plan = sub.add_parser("spec-plan", help="Create tasks.md")
    plan.add_argument("--slug", required=True)
    plan.add_argument("--date")
    plan.add_argument("--iteration", default="v1")
    plan.add_argument("--force", action="store_true")
    plan.set_defaults(func=cmd_spec_plan)

    build = sub.add_parser("spec-build", help="Report the next implementation step")
    build.add_argument("--slug", required=True)
    build.add_argument("--date")
    build.add_argument("--iteration", default="v1")
    build.set_defaults(func=cmd_spec_build)

    review = sub.add_parser("spec-review", help="Run configured review commands and write review.md")
    review.add_argument("--slug", required=True)
    review.add_argument("--date")
    review.add_argument("--iteration", default="v1")
    review.add_argument("--force", action="store_true")
    review.set_defaults(func=cmd_spec_review)

    verify = sub.add_parser("spec-verify", help="Run configured verify commands and write test-report.md")
    verify.add_argument("--slug", required=True)
    verify.add_argument("--date")
    verify.add_argument("--iteration", default="v1")
    verify.add_argument("--force", action="store_true")
    verify.set_defaults(func=cmd_spec_verify)

    close = sub.add_parser("spec-close", help="Create handoff.md if missing")
    close.add_argument("--slug", required=True)
    close.add_argument("--date")
    close.add_argument("--iteration", default="v1")
    close.set_defaults(func=cmd_spec_close)

    hook_pre_task = sub.add_parser("hook-pre-task", help="Check docs before task execution")
    hook_pre_task.set_defaults(func=cmd_hook_pre_task)

    hook_post_edit = sub.add_parser("hook-post-edit", help="Inspect risk and doc drift after edits")
    hook_post_edit.set_defaults(func=cmd_hook_post_edit)

    hook_pre_review = sub.add_parser("hook-pre-review", help="Confirm review readiness")
    hook_pre_review.set_defaults(func=cmd_hook_pre_review)

    hook_pre_verify = sub.add_parser("hook-pre-verify", help="Plan verification based on diff")
    hook_pre_verify.set_defaults(func=cmd_hook_pre_verify)

    hook_pre_close = sub.add_parser("hook-pre-close", help="Check closeout artifacts")
    hook_pre_close.add_argument("--slug", required=True)
    hook_pre_close.add_argument("--date")
    hook_pre_close.add_argument("--iteration", default="v1")
    hook_pre_close.set_defaults(func=cmd_hook_pre_close)

    show_config = sub.add_parser("show-config", help="Show the active harness config")
    show_config.set_defaults(func=cmd_show_config)

    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
