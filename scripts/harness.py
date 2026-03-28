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
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
SPECS_DIR = ROOT / "specs"

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


def read_text(path: Path) -> str:
    return path.read_text() if path.exists() else ""


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
    lines.append("---\n")
    return "\n".join(lines)


def intake_content(title: str, source: str) -> str:
    frontmatter = format_frontmatter(title, source, project_docs())
    body = load_template("requirements.template.md")
    body += f"\n## Notes\n\n- Requirement title: {title}\n- Requirement source: {source}\n"
    return frontmatter + body


def design_content(spec: SpecPaths) -> str:
    frontmatter = format_frontmatter("Design", str(spec.requirements.relative_to(ROOT)), project_docs())
    body = load_template("design.template.md")
    body += (
        "\n## Inputs\n\n"
        f"- Requirements: `{spec.requirements.relative_to(ROOT)}`\n"
        f"- Project docs loaded: {', '.join(project_docs()) or 'none-found'}\n"
    )
    return frontmatter + body


def tasks_content(spec: SpecPaths) -> str:
    frontmatter = format_frontmatter("Tasks", str(spec.design.relative_to(ROOT)), project_docs())
    body = load_template("tasks.template.md")
    body += (
        "\n## Suggested Execution Order\n\n"
        "1. Implement the smallest reviewable slice.\n"
        "2. Run targeted validation.\n"
        "3. Send the diff through review.\n"
        "4. Fix accepted findings.\n"
    )
    return frontmatter + body


def review_content(spec: SpecPaths, findings: dict[str, list[str]]) -> str:
    lines = [
        "# Review",
        "",
        "## Summary",
        "",
        "- Reviewer: pending",
        f"- Requirements: `{spec.requirements.relative_to(ROOT)}`",
        f"- Design: `{spec.design.relative_to(ROOT)}`",
        f"- Tasks: `{spec.tasks.relative_to(ROOT)}`",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.append("- No automated risk findings yet.")
    else:
        for risk, files in findings.items():
            lines.append(f"- `{risk}`: {', '.join(files)}")
    lines.extend(["", "## Disposition", "", "- Pending review"])
    return "\n".join(lines) + "\n"


def test_report_content(changed_files: list[str]) -> str:
    lines = [
        "# Test Report",
        "",
        "## Planned Commands",
        "",
        "- Add project-specific test commands here.",
        "",
        "## Changed Files",
        "",
    ]
    if changed_files:
        lines.extend(f"- `{path}`" for path in changed_files)
    else:
        lines.append("- No changed files detected.")
    lines.extend(["", "## Results", "", "- Pending execution"])
    return "\n".join(lines) + "\n"


def handoff_content(spec: SpecPaths) -> str:
    return (
        "# Handoff\n\n"
        "## Delivered Behavior\n\n"
        "- Pending summary\n\n"
        "## References\n\n"
        f"- Requirements: `{spec.requirements.relative_to(ROOT)}`\n"
        f"- Design: `{spec.design.relative_to(ROOT)}`\n"
        f"- Tasks: `{spec.tasks.relative_to(ROOT)}`\n"
        f"- Review: `{spec.review.relative_to(ROOT)}`\n"
        f"- Test report: `{spec.test_report.relative_to(ROOT)}`\n\n"
        "## Follow-up\n\n"
        "- Pending follow-up items\n"
    )


def print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2))


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


def cmd_spec_review(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    changed = git_changed_files()
    findings = collect_risks(changed)
    ensure_file(spec.review, review_content(spec, findings))
    print_json(
        {
            "command": "spec-review",
            "review": str(spec.review.relative_to(ROOT)),
            "changed_files": changed,
            "risk_findings": findings,
        }
    )
    return 0


def cmd_spec_build(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    if not spec.tasks.exists():
        print(f"missing tasks: {spec.tasks.relative_to(ROOT)}", file=sys.stderr)
        return 1
    payload = {
        "command": "spec-build",
        "tasks": str(spec.tasks.relative_to(ROOT)),
        "next_step": "Implement the highest-priority slice and run ./hooks/post-edit/run after edits.",
    }
    print_json(payload)
    return 0


def cmd_spec_verify(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    changed = git_changed_files()
    ensure_file(spec.test_report, test_report_content(changed))
    print_json(
        {
            "command": "spec-verify",
            "test_report": str(spec.test_report.relative_to(ROOT)),
            "changed_files": changed,
        }
    )
    return 0


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
    }
    if not docs:
        payload["message"] = "No project docs found under .docs/ or repo root."
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
        payload["message"] = "No diff detected."
    print_json(payload)
    return 0 if changed else 2


def cmd_hook_pre_verify(_: argparse.Namespace) -> int:
    changed = git_changed_files()
    verification_plan = {
        "targeted": ["Run unit/spec tests for changed modules first."],
        "broader": ["Run integration tests if changed files cross module boundaries."],
        "browser": ["Add Playwright or remote debugging when UI files changed."]
        if any(part in path.lower() for path in changed for part in ("ui", "page", "component", "frontend"))
        else [],
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

    review = sub.add_parser("spec-review", help="Create review.md if missing")
    review.add_argument("--slug", required=True)
    review.add_argument("--date")
    review.add_argument("--iteration", default="v1")
    review.set_defaults(func=cmd_spec_review)

    verify = sub.add_parser("spec-verify", help="Create test-report.md if missing")
    verify.add_argument("--slug", required=True)
    verify.add_argument("--date")
    verify.add_argument("--iteration", default="v1")
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

    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
