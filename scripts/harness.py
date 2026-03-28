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
from concurrent.futures import ThreadPoolExecutor, as_completed


ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "templates"
SPECS_DIR = ROOT / "specs"
CONFIG_PATH = ROOT / ".aiharness" / "config.json"
ORCHESTRATOR_PATH = ROOT / ".aiharness" / "orchestrator.json"
EXEC_PLANS_DIR = ROOT / "docs" / "exec-plans"
EXEC_PLANS_ACTIVE_DIR = EXEC_PLANS_DIR / "active"
EXEC_PLANS_COMPLETED_DIR = EXEC_PLANS_DIR / "completed"
EXECUTION_INDEX_JSON = EXEC_PLANS_DIR / "execution-index.json"
EXECUTION_INDEX_MD = EXEC_PLANS_DIR / "execution-index.md"

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
    "intake": {
        "github": {
            "enabled": True,
            "preferred_reader": "gh"
        }
    }
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


@dataclass(frozen=True)
class ReviewFinding:
    priority: str
    title: str
    summary: str
    files: tuple[str, ...]
    source: str


def orchestrator_config() -> dict[str, Any]:
    if not ORCHESTRATOR_PATH.exists():
        return {"team": {"enabled": False, "agents": []}}
    return read_json(ORCHESTRATOR_PATH)


def orchestrator_providers() -> dict[str, Any]:
    return orchestrator_config().get("providers", {})


def count_task_items(tasks_path: Path) -> int:
    if not tasks_path.exists():
        return 0
    count = 0
    for line in tasks_path.read_text().splitlines():
        stripped = line.strip()
        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            count += 1
    return count


def infer_subsystems(changed_files: list[str]) -> list[str]:
    subsystems: set[str] = set()
    for path in changed_files:
        parts = [part for part in path.split("/") if part and part not in {".", ".."}]
        if not parts:
            continue
        if parts[0] in {"src", "app", "server", "api", "web", "frontend", "backend"} and len(parts) > 1:
            subsystems.add("/".join(parts[:2]))
        else:
            subsystems.add(parts[0])
    return sorted(subsystems)


def team_signals(spec: SpecPaths, changed_files: list[str]) -> dict[str, Any]:
    orchestrator = orchestrator_config().get("team", {})
    risk_categories = collect_risks(changed_files)
    subsystems = infer_subsystems(changed_files)
    task_count = count_task_items(spec.tasks)
    triggers = orchestrator.get("triggers", {})
    signals = {
        "risk_category_count": len(risk_categories),
        "risk_categories": sorted(risk_categories.keys()),
        "subsystem_count": len(subsystems),
        "subsystems": subsystems,
        "task_count": task_count,
        "parallel_review_verify": bool(configured_or_discovered_commands("review") or configured_or_discovered_commands("verify")),
    }
    score = 0
    reasons: list[str] = []
    if triggers.get("high_risk_categories", True) and signals["risk_category_count"] > 0:
        score += 1
        reasons.append("命中高风险改动类别")
    if signals["subsystem_count"] >= triggers.get("subsystems_threshold", 3):
        score += 1
        reasons.append("涉及的子系统数量超过阈值")
    if signals["task_count"] >= triggers.get("task_count_threshold", 4):
        score += 1
        reasons.append("任务切片数量超过阈值")
    if triggers.get("requires_review_and_verify_parallel", True) and signals["parallel_review_verify"]:
        score += 1
        reasons.append("存在 review/verify 并行价值")
    signals["score"] = score
    signals["reasons"] = reasons
    signals["threshold"] = orchestrator.get("auto_enable_threshold", 2)
    signals["should_enable_team"] = score >= signals["threshold"]
    return signals


def team_plan_content(spec: SpecPaths, signals: dict[str, Any], agents: list[dict[str, Any]]) -> str:
    lines = [
        "# Team Orchestration",
        "",
        "## 结论",
        "",
        f"- 是否启用 agents team：{'是' if signals['should_enable_team'] else '否'}",
        f"- 评分：{signals['score']} / 阈值 {signals['threshold']}",
        "",
        "## 触发原因",
        "",
    ]
    if signals["reasons"]:
        lines.extend(f"- {reason}" for reason in signals["reasons"])
    else:
        lines.append("- 当前未达到自动启用条件。")
    lines.extend(
        [
            "",
            "## 信号",
            "",
            f"- 高风险类别：{', '.join(signals['risk_categories']) or '无'}",
            f"- 子系统：{', '.join(signals['subsystems']) or '无'}",
            f"- 任务数：{signals['task_count']}",
            f"- 并行 review/verify：{'是' if signals['parallel_review_verify'] else '否'}",
            "",
            "## Agent 计划",
            "",
        ]
    )
    for agent in agents:
        output = spec.root / agent["output"]
        lines.append(f"- `{agent['name']}`：{agent['role']}")
        lines.append(f"  provider：{', '.join(agent.get('providers', [])) or '未配置'}")
        lines.append(f"  stage：{agent.get('stage', 0)}")
        lines.append(f"  输入：{', '.join(agent.get('inputs', []))}")
        lines.append(f"  输出：`{output.relative_to(ROOT)}`")
    return "\n".join(lines) + "\n"


def agent_prompt_content(spec: SpecPaths, agent: dict[str, Any], signals: dict[str, Any]) -> str:
    return (
        f"# {agent['name']}\n\n"
        f"## 角色\n\n{agent['role']}\n\n"
        "## 语言约束\n\n"
        f"- {language_instruction()}\n\n"
        "## 输入\n\n"
        + "\n".join(f"- {item}" for item in agent.get("inputs", []))
        + "\n\n## Provider 候选\n\n"
        + "\n".join(f"- {item}" for item in agent.get("providers", []))
        + "\n\n## 当前信号\n\n"
        f"- 高风险类别：{', '.join(signals['risk_categories']) or '无'}\n"
        f"- 子系统：{', '.join(signals['subsystems']) or '无'}\n"
        f"- 任务数：{signals['task_count']}\n"
        f"- 需求文档：`{spec.requirements.relative_to(ROOT)}`\n"
        f"- 设计文档：`{spec.design.relative_to(ROOT)}`\n"
        f"- 任务文档：`{spec.tasks.relative_to(ROOT)}`\n"
    )


def provider_health(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    command = payload.get("command", name)
    exists = shell(["zsh", "-lc", f"command -v {command}"]).returncode == 0
    if not exists:
        return {"provider": name, "available": False, "reason": "command-not-found"}
    auth_check = payload.get("auth_check")
    if isinstance(auth_check, list) and auth_check:
        result = shell(auth_check)
        if result.returncode != 0:
            return {
                "provider": name,
                "available": False,
                "reason": "auth-check-failed",
                "stderr": truncate(result.stderr or result.stdout or "provider health check failed"),
            }
    return {"provider": name, "available": True, "reason": "ok"}


def provider_run_command(provider_name: str, provider: dict[str, Any], prompt_path: Path, output_path: Path) -> list[str]:
    model = provider.get("model", "")
    if provider_name == "codex":
        command = [
            provider["command"],
            "exec",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "-C",
            str(ROOT),
            "-o",
            str(output_path),
            "-",
        ]
        if model:
            command.extend(["-m", model])
        return command
    if provider_name == "gemini":
        command = [
            provider["command"],
            "-p",
            "",
            "-o",
            "text",
        ]
        if model:
            command.extend(["-m", model])
        return command
    return [provider["command"]]


def execute_provider(provider_name: str, provider: dict[str, Any], prompt_path: Path, output_path: Path) -> dict[str, Any]:
    command = provider_run_command(provider_name, provider, prompt_path, output_path)
    prompt_text = prompt_path.read_text()

    if provider_name == "gemini":
        command[command.index("")] = prompt_text
        result = shell(command)
    else:
        result = subprocess.run(
            command,
            cwd=ROOT,
            input=prompt_text,
            capture_output=True,
            text=True,
            check=False,
        )

    if provider_name == "gemini" and result.returncode == 0:
        output_path.write_text(result.stdout)
    return {
        "provider": provider_name,
        "command": command,
        "returncode": result.returncode,
        "stdout": truncate(result.stdout, 500),
        "stderr": truncate(result.stderr, 500),
        "output": str(output_path.relative_to(ROOT)),
        "status": "passed" if result.returncode == 0 else "failed",
    }


def build_team_run_plan(spec: SpecPaths, agents: list[dict[str, Any]]) -> dict[str, Any]:
    providers = orchestrator_providers()
    health = {name: provider_health(name, payload) for name, payload in providers.items()}
    plan_agents: list[dict[str, Any]] = []
    for agent in agents:
        prompt_path = spec.root / agent["output"]
        planned_providers = []
        for provider_name in agent.get("providers", []):
            provider_state = health.get(provider_name, {"provider": provider_name, "available": False, "reason": "unknown"})
            planned_providers.append(
                {
                    "provider": provider_name,
                    "available": provider_state["available"],
                    "reason": provider_state["reason"],
                    "result_path": str((prompt_path.parent / f"{prompt_path.stem}.{provider_name}.result.md").relative_to(ROOT)),
                }
            )
        plan_agents.append(
            {
                "name": agent["name"],
                "stage": agent.get("stage", 0),
                "prompt_path": str(prompt_path.relative_to(ROOT)),
                "providers": planned_providers,
            }
        )
    return {"providers": health, "agents": plan_agents}


def run_team_plan(spec: SpecPaths, plan: dict[str, Any]) -> list[dict[str, Any]]:
    providers = orchestrator_providers()
    executions: list[dict[str, Any]] = []
    stages = sorted({agent["stage"] for agent in plan["agents"]})
    for stage in stages:
        batch = [agent for agent in plan["agents"] if agent["stage"] == stage]
        jobs = []
        with ThreadPoolExecutor(max_workers=max(1, len(batch) * 2)) as executor:
            for agent in batch:
                prompt_path = ROOT / agent["prompt_path"]
                for provider_state in agent["providers"]:
                    if not provider_state["available"]:
                        executions.append(
                            {
                                "agent": agent["name"],
                                "provider": provider_state["provider"],
                                "status": "skipped",
                                "reason": provider_state["reason"],
                                "output": provider_state["result_path"],
                            }
                        )
                        continue
                    output_path = ROOT / provider_state["result_path"]
                    jobs.append(
                        executor.submit(
                            execute_provider,
                            provider_state["provider"],
                            providers[provider_state["provider"]],
                            prompt_path,
                            output_path,
                        )
                    )
            for future in as_completed(jobs):
                executions.append(future.result())
    return executions


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


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


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


def move_path(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    src.replace(dest)


def load_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text().rstrip() + "\n"


def shell(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def project_docs() -> list[str]:
    return [candidate for candidate in PROJECT_DOC_CANDIDATES if (ROOT / candidate).exists()]


def git_changed_files() -> list[str]:
    result = shell(["git", "-C", str(ROOT), "status", "--short"])
    changed: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        changed.append(line[3:].strip())
    return changed


def git_diff_name_only() -> list[str]:
    result = shell(["git", "-C", str(ROOT), "diff", "--name-only", "HEAD"])
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_diff_stats() -> list[dict[str, Any]]:
    result = shell(["git", "-C", str(ROOT), "diff", "--numstat", "HEAD"])
    stats: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        try:
            add_count = int(added)
        except ValueError:
            add_count = 0
        try:
            del_count = int(deleted)
        except ValueError:
            del_count = 0
        stats.append({"path": path, "added": add_count, "deleted": del_count, "total": add_count + del_count})
    return stats


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


def parse_github_issue_url(source: str) -> dict[str, str] | None:
    pattern = re.compile(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)")
    match = pattern.search(source)
    if not match:
        return None
    owner, repo, number = match.groups()
    return {"owner": owner, "repo": repo, "number": number}


def load_github_issue(source: str) -> dict[str, Any] | None:
    parsed = parse_github_issue_url(source)
    if not parsed:
        return None
    if not config().get("intake", {}).get("github", {}).get("enabled", True):
        return None

    result = shell(
        [
            "gh",
            "issue",
            "view",
            parsed["number"],
            "--repo",
            f"{parsed['owner']}/{parsed['repo']}",
            "--json",
            "title,body,labels,assignees,comments,state,url",
        ]
    )
    if result.returncode != 0:
        return {
            "type": "github-issue",
            "url": source,
            "error": result.stderr.strip() or "gh issue view failed",
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "type": "github-issue",
            "url": source,
            "error": "invalid gh output",
        }

    labels = [item.get("name", "") for item in payload.get("labels", []) if item.get("name")]
    assignees = [item.get("login", "") for item in payload.get("assignees", []) if item.get("login")]
    comments = payload.get("comments", [])[:5]
    return {
        "type": "github-issue",
        "url": payload.get("url", source),
        "title": payload.get("title", ""),
        "body": payload.get("body", "").strip(),
        "state": payload.get("state", ""),
        "labels": labels,
        "assignees": assignees,
        "comments": [
            {
                "author": item.get("author", {}).get("login", "unknown"),
                "body": item.get("body", "").strip(),
            }
            for item in comments
        ],
    }


def intake_content(title: str, source: str, source_details: dict[str, Any] | None = None) -> str:
    frontmatter = format_frontmatter(title, source, project_docs())
    body = load_template("requirements.template.md")
    body += f"\n## 语言约束\n\n- {language_instruction()}\n"
    body += f"\n## 备注\n\n- 需求标题：{title}\n- 需求来源：{source}\n"
    if source_details:
        body += "\n## 来源解析\n\n"
        body += f"- 类型：{source_details.get('type', 'unknown')}\n"
        body += f"- URL：{source_details.get('url', source)}\n"
        if source_details.get("state"):
            body += f"- 状态：{source_details['state']}\n"
        if source_details.get("labels"):
            body += f"- 标签：{', '.join(source_details['labels'])}\n"
        if source_details.get("assignees"):
            body += f"- 负责人：{', '.join(source_details['assignees'])}\n"
        if source_details.get("error"):
            body += f"- 读取错误：{source_details['error']}\n"
        if source_details.get("body"):
            body += f"\n## 来源正文\n\n{source_details['body']}\n"
        if source_details.get("comments"):
            body += "\n## 来源评论摘要\n\n"
            for comment in source_details["comments"]:
                if not comment["body"]:
                    continue
                body += f"- `{comment['author']}`: {comment['body'][:300]}\n"
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


def candidate_command(name: str, command: str, description: str, section: str) -> dict[str, Any]:
    return {
        "name": name,
        "enabled": False,
        "command": command,
        "description": description,
        "section": section,
    }


def detect_npm_commands() -> list[dict[str, Any]]:
    package_json = ROOT / "package.json"
    if not package_json.exists():
        return []
    payload = json.loads(package_json.read_text())
    scripts = payload.get("scripts", {})
    detected: list[dict[str, Any]] = []
    if "lint" in scripts:
        detected.append(candidate_command("lint", "npm run lint", "JavaScript/TypeScript lint 检查。", "review"))
    if "typecheck" in scripts:
        detected.append(candidate_command("typecheck", "npm run typecheck", "TypeScript 类型检查。", "review"))
    elif "tsc" in scripts:
        detected.append(candidate_command("tsc", "npm run tsc", "TypeScript 编译检查。", "review"))
    if "test" in scripts:
        detected.append(candidate_command("npm-test", "npm test -- --runInBand", "Node 测试命令。", "verify"))
    if "test:unit" in scripts:
        detected.append(candidate_command("unit", "npm run test:unit", "项目定义的单元测试。", "verify"))
    if "test:e2e" in scripts:
        detected.append(candidate_command("e2e", "npm run test:e2e", "项目定义的端到端测试。", "verify"))
    if "playwright" in scripts:
        detected.append(candidate_command("playwright", "npm run playwright", "项目定义的 Playwright 测试。", "verify"))
    return detected


def detect_pytest_commands() -> list[dict[str, Any]]:
    files = ["pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml"]
    if not any((ROOT / item).exists() for item in files):
        return []
    return [
        candidate_command("pytest-quick", "pytest -q", "Python 快速回归测试。", "review"),
        candidate_command("pytest", "pytest", "Python 测试。", "verify"),
    ]


def detect_playwright_commands() -> list[dict[str, Any]]:
    candidates = [
        "playwright.config.ts",
        "playwright.config.js",
        "playwright.config.mjs",
        "playwright.config.cjs",
    ]
    if any((ROOT / item).exists() for item in candidates):
        return [candidate_command("playwright", "npx playwright test", "Playwright 端到端测试。", "verify")]
    return []


def discovered_commands() -> dict[str, list[dict[str, Any]]]:
    review: list[dict[str, Any]] = []
    verify: list[dict[str, Any]] = []
    for item in detect_npm_commands() + detect_pytest_commands() + detect_playwright_commands():
        target = review if item["section"] == "review" else verify
        trimmed = {k: v for k, v in item.items() if k != "section"}
        if not any(existing["command"] == trimmed["command"] for existing in target):
            target.append(trimmed)
    return {"review": review, "verify": verify}


def configured_or_discovered_commands(section: str) -> list[dict[str, Any]]:
    configured = enabled_command_specs(section)
    if configured:
        return configured
    return discovered_commands().get(section, [])


def truncate(text: str, limit: int = 220) -> str:
    stripped = " ".join(text.split())
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3] + "..."


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
    for entry in configured_or_discovered_commands(section):
        outcome = run_shell_command(entry["command"])
        outcome["name"] = entry.get("name", entry["command"])
        outcome["description"] = entry.get("description", "")
        outcome["auto_discovered"] = not entry.get("enabled", False)
        results.append(outcome)
    return results


def synthesize_review_findings(
    spec: SpecPaths,
    changed_files: list[str],
    risk_findings: dict[str, list[str]],
    doc_hints: dict[str, list[str]],
    command_results: list[dict[str, Any]],
) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []

    for required_path, label in (
        (spec.requirements, "需求文档"),
        (spec.design, "设计文档"),
        (spec.tasks, "任务文档"),
    ):
        if not required_path.exists():
            findings.append(
                ReviewFinding(
                    priority="P1",
                    title=f"{label}缺失",
                    summary=f"`{required_path.relative_to(ROOT)}` 不存在，当前 diff 缺少完整的 spec 上下文，继续开发或审查风险较高。",
                    files=(str(required_path.relative_to(ROOT)),),
                    source="spec",
                )
            )

    for result in command_results:
        if result["returncode"] == 0:
            continue
        details = result["stderr"] or result["stdout"] or "命令返回非零退出码，但没有输出。"
        findings.append(
            ReviewFinding(
                priority="P1",
                title=f"Review 命令失败：{result['name']}",
                summary=f"`{result['command']}` 执行失败。关键信息：{truncate(details)}",
                files=tuple(changed_files[:5]),
                source="command",
            )
        )

    risk_priority = {
        "security": "P1",
        "billing": "P1",
        "migration": "P1",
        "infrastructure": "P2",
    }
    risk_summary = {
        "security": "当前改动触达鉴权、密钥或安全边界相关文件，应补充权限与回归验证。",
        "billing": "当前改动触达计费、支付或退款相关文件，应补充业务正确性和对账验证。",
        "migration": "当前改动触达迁移或数据库结构相关文件，应补充回滚与数据安全检查。",
        "infrastructure": "当前改动触达部署或基础设施文件，应确认环境影响和发布策略。",
    }
    for risk, files in risk_findings.items():
        findings.append(
            ReviewFinding(
                priority=risk_priority.get(risk, "P2"),
                title=f"高风险改动：{risk}",
                summary=risk_summary.get(risk, "当前改动涉及高风险区域，应补充专项 review。"),
                files=tuple(files[:5]),
                source="risk",
            )
        )

    for doc_path, files in doc_hints.items():
        findings.append(
            ReviewFinding(
                priority="P3",
                title=f"文档可能需要同步：{doc_path}",
                summary=f"当前变更涉及 {', '.join(files[:3])}，按规则应检查 `{doc_path}` 是否需要更新。",
                files=tuple(files[:5]),
                source="docs",
            )
        )

    stats = git_diff_stats()
    large_changes = [item["path"] for item in stats if item["total"] >= 200]
    if large_changes:
        findings.append(
            ReviewFinding(
                priority="P2",
                title="大体量改动需要拆分审查",
                summary=f"以下文件 diff 较大：{', '.join(large_changes[:5])}。建议拆分提交或补充更细粒度验证，降低 review 漏检风险。",
                files=tuple(large_changes[:5]),
                source="diff",
            )
        )

    if changed_files and not command_results:
        findings.append(
            ReviewFinding(
                priority="P2",
                title="未执行任何自动审查命令",
                summary="当前存在代码变更，但没有启用或发现可执行的 review 命令。至少应补一条 lint、typecheck 或快速回归检查。",
                files=tuple(changed_files[:5]),
                source="command",
            )
        )

    findings.sort(key=lambda item: (item.priority, item.title))
    return findings


def review_content(
    spec: SpecPaths,
    risk_findings: dict[str, list[str]],
    command_results: list[dict[str, Any]],
    findings: list[ReviewFinding],
) -> str:
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
        lines.append("- 当前未启用也未发现可执行的 review 命令。")
    else:
        for result in command_results:
            mode = "自动发现" if result.get("auto_discovered") else "配置启用"
            lines.append(f"- `{result['name']}`: {result['status']} (`{result['command']}`，{mode})")
    lines.extend(["", "## 风险提示", ""])
    if not risk_findings:
        lines.append("- 当前没有命中文件级风险规则。")
    else:
        for risk, files in risk_findings.items():
            lines.append(f"- `{risk}`: {', '.join(files)}")
    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("- 当前没有生成结构化 findings。")
    else:
        for item in findings:
            file_refs = ", ".join(item.files) if item.files else "无"
            lines.append(f"- `{item.priority}` {item.title}")
            lines.append(f"  来源：{item.source}；关联文件：{file_refs}；说明：{item.summary}")
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
        lines.append("- 当前未启用也未发现可执行的 verify 命令。")
    else:
        for result in command_results:
            mode = "自动发现" if result.get("auto_discovered") else "配置启用"
            lines.append(f"- `{result['name']}`: {result['status']} (`{result['command']}`，{mode})")
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


def exec_plan_name(slug: str, stamp: str) -> str:
    return f"{slug}-{stamp}.md"


def active_exec_plan_path(slug: str, stamp: str) -> Path:
    return EXEC_PLANS_ACTIVE_DIR / exec_plan_name(slug, stamp)


def completed_exec_plan_path(slug: str, stamp: str) -> Path:
    return EXEC_PLANS_COMPLETED_DIR / exec_plan_name(slug, stamp)


def execution_index_payload() -> list[dict[str, Any]]:
    if not EXECUTION_INDEX_JSON.exists():
        return []
    try:
        return json.loads(EXECUTION_INDEX_JSON.read_text())
    except json.JSONDecodeError:
        return []


def write_execution_index(entries: list[dict[str, Any]]) -> None:
    EXECUTION_INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    EXECUTION_INDEX_JSON.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")

    lines = [
        "# Execution Index",
        "",
        "| 日期 | 命令 | slug | stamp | 状态 | 备注 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in entries[-100:]:
        lines.append(
            f"| {item['date']} | `{item['command']}` | `{item['slug']}` | `{item['stamp']}` | `{item['status']}` | {item.get('note', '')} |"
        )
    EXECUTION_INDEX_MD.write_text("\n".join(lines) + "\n")


def record_execution_event(command: str, slug: str, stamp: str, status: str, note: str = "") -> None:
    entries = execution_index_payload()
    entries.append(
        {
            "date": date.today().isoformat(),
            "command": command,
            "slug": slug,
            "stamp": stamp,
            "status": status,
            "note": note,
        }
    )
    write_execution_index(entries)


def exec_plan_content(spec: SpecPaths, signals: dict[str, Any], status: str) -> str:
    return (
        "# Execution Plan\n\n"
        f"## slug\n\n- `{spec.root.parent.name}`\n\n"
        f"## stamp\n\n- `{spec.root.name}`\n\n"
        f"## status\n\n- `{status}`\n\n"
        "## links\n\n"
        f"- requirements: `{spec.requirements.relative_to(ROOT)}`\n"
        f"- design: `{spec.design.relative_to(ROOT)}`\n"
        f"- tasks: `{spec.tasks.relative_to(ROOT)}`\n"
        f"- orchestration: `{(spec.root / 'orchestration.md').relative_to(ROOT)}`\n\n"
        "## signals\n\n"
        f"- 风险类别：{', '.join(signals['risk_categories']) or '无'}\n"
        f"- 子系统：{', '.join(signals['subsystems']) or '无'}\n"
        f"- 任务数：{signals['task_count']}\n"
        f"- 是否启用 team：{'是' if signals['should_enable_team'] else '否'}\n"
    )


def run_or_fail(func, args: argparse.Namespace) -> dict[str, Any]:
    code = func(args)
    if code not in (0, 2):
        raise RuntimeError(f"{func.__name__} failed with exit code {code}")
    return {"step": func.__name__, "exit_code": code}


def cmd_spec_intake(args: argparse.Namespace) -> int:
    source_details = load_github_issue(args.source)
    title = source_details.get("title") if source_details and source_details.get("title") else args.title
    if not title:
        print("missing title: provide --title or a readable GitHub issue URL in --source", file=sys.stderr)
        return 1
    slug = slugify(args.slug or title)
    spec = spec_dir(slug, build_stamp(args.date, args.iteration))
    write_text(spec.requirements, intake_content(title, args.source, source_details), force=args.force)
    print_json(
        {
            "command": "spec-intake",
            "spec_root": str(spec.root.relative_to(ROOT)),
            "requirements": str(spec.requirements.relative_to(ROOT)),
            "project_docs": project_docs(),
            "language": config().get("language", {}).get("default", "zh-CN"),
            "resolved_title": title,
            "source_details": source_details or {},
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
    changed = git_changed_files() or git_diff_name_only()
    findings = collect_risks(changed)
    doc_hints = doc_drift_hints(changed)
    command_results = execute_configured_commands("review")
    structured_findings = synthesize_review_findings(spec, changed, findings, doc_hints, command_results)
    write_text(spec.review, review_content(spec, findings, command_results, structured_findings), force=args.force)
    failed = [result for result in command_results if result["returncode"] != 0]
    print_json(
        {
            "command": "spec-review",
            "review": str(spec.review.relative_to(ROOT)),
            "changed_files": changed,
            "risk_findings": findings,
            "doc_drift_hints": doc_hints,
            "command_results": command_results,
            "findings": [
                {
                    "priority": item.priority,
                    "title": item.title,
                    "summary": item.summary,
                    "files": list(item.files),
                    "source": item.source,
                }
                for item in structured_findings
            ],
            "failed": [result["name"] for result in failed],
        }
    )
    high_priority = [item for item in structured_findings if item.priority in {"P1", "P2"}]
    return 1 if failed or high_priority else 0


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
        "discovered_commands": discovered_commands().get("verify", []),
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


def cmd_discover_commands(args: argparse.Namespace) -> int:
    discovered = discovered_commands()
    if args.apply:
        current = config()
        current.setdefault("review", {})["commands"] = discovered["review"]
        current.setdefault("verify", {})["commands"] = discovered["verify"]
        save_json(CONFIG_PATH, current)
    print_json(
        {
            "command": "discover-commands",
            "applied": args.apply,
            "discovered": discovered,
            "config_path": str(CONFIG_PATH.relative_to(ROOT)),
        }
    )
    return 0


def cmd_spec_team(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    changed_files = git_changed_files() or git_diff_name_only()
    orchestrator = orchestrator_config().get("team", {})
    agents = orchestrator.get("agents", [])
    signals = team_signals(spec, changed_files)

    team_plan = spec.root / "orchestration.md"
    write_text(team_plan, team_plan_content(spec, signals, agents), force=args.force)

    generated_outputs: list[str] = [str(team_plan.relative_to(ROOT))]
    for agent in agents:
        output_path = spec.root / agent["output"]
        write_text(output_path, agent_prompt_content(spec, agent, signals), force=args.force)
        generated_outputs.append(str(output_path.relative_to(ROOT)))

    exec_plan_path = active_exec_plan_path(spec.root.parent.name, spec.root.name)
    write_text(exec_plan_path, exec_plan_content(spec, signals, "active"), force=True)
    generated_outputs.append(str(exec_plan_path.relative_to(ROOT)))

    print_json(
        {
            "command": "spec-team",
            "team_enabled": signals["should_enable_team"],
            "signals": signals,
            "outputs": generated_outputs,
        }
    )
    return 0 if signals["should_enable_team"] else 2


def cmd_spec_run_team(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    orchestrator = orchestrator_config().get("team", {})
    agents = orchestrator.get("agents", [])
    run_plan = build_team_run_plan(spec, agents)
    run_plan_path = spec.root / "agent-results" / "run-plan.json"
    run_plan_path.parent.mkdir(parents=True, exist_ok=True)
    run_plan_path.write_text(json.dumps(run_plan, indent=2, ensure_ascii=False) + "\n")

    executions: list[dict[str, Any]] = []
    if args.execute:
        executions = run_team_plan(spec, run_plan)

    print_json(
        {
            "command": "spec-run-team",
            "run_plan": str(run_plan_path.relative_to(ROOT)),
            "providers": run_plan["providers"],
            "agents": run_plan["agents"],
            "executions": executions,
        }
    )
    if args.execute:
        failed = [item for item in executions if item.get("status") == "failed"]
        record_execution_event("spec-run-team", spec.root.parent.name, spec.root.name, "failed" if failed else "passed", "provider run")
        return 1 if failed else 0
    record_execution_event("spec-run-team", spec.root.parent.name, spec.root.name, "planned", "provider run plan generated")
    return 0


def cmd_spec_start(args: argparse.Namespace) -> int:
    source_details = load_github_issue(args.source)
    title = source_details.get("title") if source_details and source_details.get("title") else args.title
    if not title:
        print("missing title: provide --title or a readable GitHub issue URL in --source", file=sys.stderr)
        return 1

    slug = slugify(args.slug or title)
    stamp = build_stamp(args.date, args.iteration)
    common = argparse.Namespace(slug=slug, date=args.date, iteration=args.iteration, force=args.force)
    intake_args = argparse.Namespace(
        title=title,
        source=args.source,
        slug=slug,
        date=args.date,
        iteration=args.iteration,
        force=args.force,
    )

    steps = [
        run_or_fail(cmd_spec_intake, intake_args),
        run_or_fail(cmd_spec_design, common),
        run_or_fail(cmd_spec_plan, common),
        run_or_fail(cmd_discover_commands, argparse.Namespace(apply=True)),
    ]

    team_exit = cmd_spec_team(common)
    steps.append({"step": "cmd_spec_team", "exit_code": team_exit})

    print_json(
        {
            "command": "spec-start",
            "slug": slug,
            "stamp": stamp,
            "steps": steps,
        }
    )
    record_execution_event("spec-start", slug, stamp, "completed", "需求接入与计划初始化")
    return 0


def cmd_spec_execute(args: argparse.Namespace) -> int:
    common = argparse.Namespace(slug=args.slug, date=args.date, iteration=args.iteration, force=True)
    steps = [run_or_fail(cmd_spec_build, common)]

    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    signals = team_signals(spec, git_changed_files() or git_diff_name_only())
    should_run_team = args.team or signals["should_enable_team"]

    if should_run_team:
        team_exit = cmd_spec_team(common)
        steps.append({"step": "cmd_spec_team", "exit_code": team_exit})
        run_team_exit = cmd_spec_run_team(
            argparse.Namespace(
                slug=args.slug,
                date=args.date,
                iteration=args.iteration,
                execute=args.execute_team,
            )
        )
        steps.append({"step": "cmd_spec_run_team", "exit_code": run_team_exit})

    post_edit_exit = cmd_hook_post_edit(argparse.Namespace())
    steps.append({"step": "cmd_hook_post_edit", "exit_code": post_edit_exit})

    review_exit = cmd_spec_review(common)
    verify_exit = cmd_spec_verify(common)
    steps.append({"step": "cmd_spec_review", "exit_code": review_exit})
    steps.append({"step": "cmd_spec_verify", "exit_code": verify_exit})

    print_json(
        {
            "command": "spec-execute",
            "slug": args.slug,
            "team_used": should_run_team,
            "steps": steps,
        }
    )
    status = "failed" if review_exit == 1 or verify_exit == 1 else "completed"
    note = "执行阶段完成" if status == "completed" else "review 或 verify 存在阻塞问题"
    record_execution_event("spec-execute", spec.root.parent.name, spec.root.name, status, note)
    return 1 if review_exit == 1 or verify_exit == 1 else 0


def cmd_spec_finish(args: argparse.Namespace) -> int:
    common = argparse.Namespace(slug=args.slug, date=args.date, iteration=args.iteration)
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    pre_close_exit = cmd_hook_pre_close(common)
    close_exit = cmd_spec_close(common)
    active_plan = active_exec_plan_path(spec.root.parent.name, spec.root.name)
    completed_plan = completed_exec_plan_path(spec.root.parent.name, spec.root.name)
    move_path(active_plan, completed_plan)
    print_json(
        {
            "command": "spec-finish",
            "slug": args.slug,
            "steps": [
                {"step": "cmd_hook_pre_close", "exit_code": pre_close_exit},
                {"step": "cmd_spec_close", "exit_code": close_exit},
            ],
            "archived_plan": str(completed_plan.relative_to(ROOT)) if completed_plan.exists() else "",
        }
    )
    record_execution_event("spec-finish", spec.root.parent.name, spec.root.name, "completed", "交付收尾并归档计划")
    return 0 if close_exit == 0 else close_exit


def cmd_spec_archive_plan(args: argparse.Namespace) -> int:
    spec = spec_dir(slugify(args.slug), build_stamp(args.date, args.iteration))
    active_plan = active_exec_plan_path(spec.root.parent.name, spec.root.name)
    completed_plan = completed_exec_plan_path(spec.root.parent.name, spec.root.name)
    move_path(active_plan, completed_plan)
    print_json(
        {
            "command": "spec-archive-plan",
            "slug": spec.root.parent.name,
            "stamp": spec.root.name,
            "archived_plan": str(completed_plan.relative_to(ROOT)) if completed_plan.exists() else "",
        }
    )
    record_execution_event("spec-archive-plan", spec.root.parent.name, spec.root.name, "completed", "手动归档执行计划")
    return 0 if completed_plan.exists() else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="AI Harness command and hook runner")
    sub = root.add_subparsers(dest="command", required=True)

    intake = sub.add_parser("spec-intake", help="Create requirements.md")
    intake.add_argument("--title")
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

    discover = sub.add_parser("discover-commands", help="Discover review and verify commands from the current repo")
    discover.add_argument("--apply", action="store_true")
    discover.set_defaults(func=cmd_discover_commands)

    team = sub.add_parser("spec-team", help="Generate a multi-agent orchestration plan")
    team.add_argument("--slug", required=True)
    team.add_argument("--date")
    team.add_argument("--iteration", default="v1")
    team.add_argument("--force", action="store_true")
    team.set_defaults(func=cmd_spec_team)

    run_team = sub.add_parser("spec-run-team", help="Build or execute provider run plan for agents team")
    run_team.add_argument("--slug", required=True)
    run_team.add_argument("--date")
    run_team.add_argument("--iteration", default="v1")
    run_team.add_argument("--execute", action="store_true")
    run_team.set_defaults(func=cmd_spec_run_team)

    start = sub.add_parser("spec-start", help="Aggregate intake, design, plan, discovery, and optional team setup")
    start.add_argument("--title")
    start.add_argument("--source", default="manual")
    start.add_argument("--slug")
    start.add_argument("--date")
    start.add_argument("--iteration", default="v1")
    start.add_argument("--force", action="store_true")
    start.set_defaults(func=cmd_spec_start)

    execute = sub.add_parser("spec-execute", help="Aggregate build, team planning, review, and verify")
    execute.add_argument("--slug", required=True)
    execute.add_argument("--date")
    execute.add_argument("--iteration", default="v1")
    execute.add_argument("--force", action="store_true")
    execute.add_argument("--team", action="store_true")
    execute.add_argument("--execute-team", action="store_true")
    execute.set_defaults(func=cmd_spec_execute)

    finish = sub.add_parser("spec-finish", help="Aggregate pre-close and close")
    finish.add_argument("--slug", required=True)
    finish.add_argument("--date")
    finish.add_argument("--iteration", default="v1")
    finish.set_defaults(func=cmd_spec_finish)

    archive = sub.add_parser("spec-archive-plan", help="Archive an active execution plan into completed")
    archive.add_argument("--slug", required=True)
    archive.add_argument("--date")
    archive.add_argument("--iteration", default="v1")
    archive.set_defaults(func=cmd_spec_archive_plan)

    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
