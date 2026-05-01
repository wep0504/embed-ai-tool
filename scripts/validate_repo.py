#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
import argparse
import json
from pathlib import Path
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    # Keep compatibility with environments that do not support reconfigure().
    pass


REQUIRED_FILES = [
    ".gitignore",
    "README.md",
    "CONTRIBUTING.md",
    "shared/contracts.md",
    "shared/failure-taxonomy.md",
    "shared/platform-compatibility.md",
    "shared/references/tool-detection.md",
    "shared/references/acceptance-scenarios.md",
    "templates/skill-template/SKILL.md",
    "templates/skill-template/CHECKLIST.md",
    "templates/skill-template/SCENARIOS.md",
]

REQUIRED_SKILLS = [
    "build-cmake",
    "flash-openocd",
    "serial-monitor",
    "debug-gdb-openocd",
    "peripheral-driver",
    "flash-jlink",
    "debug-jlink",
    "memory-analysis",
    "rtos-debug",
    "static-analysis",
]

REQUIRED_SECTIONS = [
    "## 适用场景",
    "## 必要输入",
    "## 自动探测",
    "## 执行步骤",
    "## 失败分流",
    "## 平台说明",
    "## 输出约定",
    "## 交接关系",
]

REQUIRED_SKILL_SNIPPETS = [
    "显式输入 > 工作区线索 > 历史上下文 > 默认值",
    "ambiguous-context",
]

TYPE_RULES = {
    "build-": {
        "section": "## 失败分流",
        "keywords": ["构建", "编译", "产物", "日志"],
        "description": "build skills should include compile evidence keywords",
    },
    "flash-": {
        "section": "## 失败分流",
        "keywords": ["烧录", "端口", "探针", "校验"],
        "description": "flash skills should include flashing evidence keywords",
    },
    "debug-": {
        "section": "## 失败分流",
        "keywords": ["调试", "回溯", "寄存器", "断点"],
        "description": "debug skills should include debug evidence keywords",
    },
}

EXACT_TYPE_RULES = {
    "serial-monitor": {
        "section": "## 失败分流",
        "keywords": ["串口", "日志", "收发"],
        "description": "serial-monitor should include serial evidence keywords",
    },
    "workflow": {
        "section": "## 失败分流",
        "keywords": ["步骤", "子命令", "日志", "上游输入"],
        "description": "workflow should include pipeline step evidence keywords",
    },
    "memory-analysis": {
        "section": "## 失败分流",
        "keywords": ["分析", "证据", "判定"],
        "description": "memory-analysis should include analysis evidence keywords",
    },
    "peripheral-driver": {
        "section": "## 失败分流",
        "keywords": ["证据", "重试", "ambiguous-context"],
        "description": "peripheral-driver should include evidence and ambiguity handling",
    },
    "static-analysis": {
        "section": "## 失败分流",
        "keywords": ["分析", "日志", "证据"],
        "description": "static-analysis should include static check evidence keywords",
    },
    "rtos-debug": {
        "section": "## 失败分流",
        "keywords": ["调试", "回溯", "寄存器"],
        "description": "rtos-debug should include debug evidence keywords",
    },
}


def fail(message: str, failures: list[str], hint: str | None = None) -> None:
    if hint:
        failures.append(f"{message} | fix: {hint}")
        return
    failures.append(message)


def validate_required_files(root: Path, failures: list[str]) -> None:
    for relative_path in REQUIRED_FILES:
        if not (root / relative_path).is_file():
            fail(
                f"missing file: {relative_path}",
                failures,
                f"create or restore '{relative_path}'",
            )


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return {}

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def section_content(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(heading)}\s*\r?\n(.*?)(?=^##\s+|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1)


def validate_skill(skill_dir: Path, failures: list[str]) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        fail(
            f"missing file: {skill_md.relative_to(skill_dir.parent.parent)}",
            failures,
            "add a SKILL.md file in this skill directory",
        )
        return

    text = skill_md.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    expected_name = skill_dir.name

    if frontmatter.get("name") != expected_name:
        fail(
            f"{skill_md.relative_to(skill_dir.parent.parent)} frontmatter name should be '{expected_name}'",
            failures,
            f"set frontmatter 'name: {expected_name}' to match directory name",
        )

    if not frontmatter.get("description"):
        fail(
            f"{skill_md.relative_to(skill_dir.parent.parent)} missing frontmatter description",
            failures,
            "add a one-sentence trigger description in frontmatter",
        )

    for heading in REQUIRED_SECTIONS:
        if heading not in text:
            fail(
                f"{skill_md.relative_to(skill_dir.parent.parent)} missing section: {heading}",
                failures,
                f"add section heading '{heading}' to SKILL.md",
            )


def validate_template_skill(root: Path, failures: list[str]) -> None:
    template_skill = root / "templates" / "skill-template" / "SKILL.md"
    if not template_skill.is_file():
        fail(
            "missing file: templates/skill-template/SKILL.md",
            failures,
            "restore the skill template file at templates/skill-template/SKILL.md",
        )
        return

    text = template_skill.read_text(encoding="utf-8")

    for snippet in REQUIRED_SKILL_SNIPPETS:
        if snippet not in text:
            fail(
                f"{template_skill.relative_to(root)} missing required content: {snippet}",
                failures,
                "update template wording to include this required convention",
            )

    detection_section = section_content(text, "## 自动探测")
    output_section = section_content(text, "## 输出约定")
    failure_section = section_content(text, "## 失败分流")
    handoff_section = section_content(text, "## 交接关系")

    if not detection_section:
        fail(
            f"{template_skill.relative_to(root)} missing or invalid section body: ## 自动探测",
            failures,
            "add concrete detection order and fallback rules under ## 自动探测",
        )
    if not output_section:
        fail(
            f"{template_skill.relative_to(root)} missing or invalid section body: ## 输出约定",
            failures,
            "define status/summary/evidence/next_actions under ## 输出约定",
        )
    if not failure_section:
        fail(
            f"{template_skill.relative_to(root)} missing or invalid section body: ## 失败分流",
            failures,
            "document failure categories and recovery behavior under ## 失败分流",
        )
    if not handoff_section:
        fail(
            f"{template_skill.relative_to(root)} missing or invalid section body: ## 交接关系",
            failures,
            "describe downstream handoff and no-handoff termination conditions",
        )

    required_output_fields = ["`status`", "`summary`", "`evidence`", "`next_actions`"]
    for field in required_output_fields:
        if field not in output_section:
            fail(
                f"{template_skill.relative_to(root)} missing required output field in ## 输出约定: {field}",
                failures,
                f"add {field} in ## 输出约定",
            )

    if "最大重试次数" not in failure_section and "重试" not in failure_section:
        fail(
            f"{template_skill.relative_to(root)} should define retry strategy for recoverable failures",
            failures,
            "add retry count, retry interval, and post-limit state in ## 失败分流",
        )

    if "不交接" not in handoff_section and "直接结束" not in handoff_section:
        fail(
            f"{template_skill.relative_to(root)} should define no-handoff termination condition",
            failures,
            "add explicit no-handoff direct-termination condition in ## 交接关系",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate repository skill specs and shared templates.")
    parser.add_argument(
        "--strict-skills",
        action="store_true",
        help="deprecated alias of '--strict-skills-mode error'",
    )
    parser.add_argument(
        "--strict-skills-mode",
        choices=["off", "warn", "error"],
        default="off",
        help="apply template-level conventions to all skills/*/SKILL.md",
    )
    parser.add_argument(
        "--suggest-patches",
        action="store_true",
        help="print minimal migration snippets for strict-skill issues",
    )
    parser.add_argument(
        "--suggest-patches-format",
        choices=["markdown", "json"],
        default="markdown",
        help="output format for --suggest-patches",
    )
    parser.add_argument(
        "--suggest-patches-output",
        help="optional file path to write patch suggestions",
    )
    return parser.parse_args()


def validate_skill_strict(skill_dir: Path, failures: list[str]) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return

    skill_name = skill_dir.name
    text = skill_md.read_text(encoding="utf-8")
    for snippet in REQUIRED_SKILL_SNIPPETS:
        if snippet not in text:
            fail(
                f"{skill_md.relative_to(skill_dir.parent.parent)} missing strict content: {snippet}",
                failures,
                "migrate this skill to the latest template conventions",
            )

    # Type-specific content rules in strict mode.
    matched_rule: dict[str, object] | None = None
    for prefix, rule in TYPE_RULES.items():
        if skill_name.startswith(prefix):
            matched_rule = rule
            break
    if not matched_rule:
        matched_rule = EXACT_TYPE_RULES.get(skill_name)

    if matched_rule:
        section_name = str(matched_rule["section"])
        section = section_content(text, section_name)
        keywords = list(matched_rule["keywords"])
        missing_keywords = [kw for kw in keywords if kw not in section]
        if missing_keywords:
            fail(
                f"{skill_md.relative_to(skill_dir.parent.parent)} missing strict type keywords in {section_name}: "
                + ", ".join(missing_keywords),
                failures,
                f"add type-specific evidence language for {skill_name}: {matched_rule['description']}",
            )


def parse_strict_issue(issue: str) -> tuple[str, str]:
    issue_main = issue.split("| fix:", 1)[0].strip()
    for marker in (" missing strict content: ", " missing strict type keywords in "):
        parts = issue_main.split(marker, 1)
        if len(parts) == 2:
            skill_path = parts[0].strip()
            rule_key = parts[1].strip()
            return skill_path, rule_key
    return "unknown", issue_main


def print_strict_summary(strict_issues: list[str]) -> None:
    by_rule: Counter[str] = Counter()
    by_skill: Counter[str] = Counter()

    for issue in strict_issues:
        skill_path, rule_key = parse_strict_issue(issue)
        by_rule[rule_key] += 1
        by_skill[skill_path] += 1

    print("Strict summary by rule:")
    for rule_key, count in by_rule.most_common():
        print(f"- {rule_key}: {count}")

    print("Strict summary by skill:")
    for skill_path, count in by_skill.most_common():
        print(f"- {skill_path}: {count}")


def render_suggestion(rule_key: str) -> list[str]:
    if rule_key == "显式输入 > 工作区线索 > 历史上下文 > 默认值":
        return [
            "## 自动探测",
            "- 统一优先级：`显式输入 > 工作区线索 > 历史上下文 > 默认值`。",
        ]
    if rule_key == "ambiguous-context":
        return [
            "## 自动探测",
            "- 若多个候选同样合理且选择错误会破坏流程，标记为 `ambiguous-context` 并停止猜测。",
        ]
    return [f"- 请补齐严格规则内容：{rule_key}"]


def build_patch_suggestions(strict_issues: list[str]) -> dict[str, list[str]]:
    by_skill_rules: dict[str, set[str]] = {}
    for issue in strict_issues:
        skill_path, rule_key = parse_strict_issue(issue)
        if skill_path == "unknown":
            continue
        by_skill_rules.setdefault(skill_path, set()).add(rule_key)

    suggestions: dict[str, list[str]] = {}
    for skill_path in sorted(by_skill_rules):
        lines: list[str] = []
        for rule_key in sorted(by_skill_rules[skill_path]):
            lines.extend(render_suggestion(rule_key))
        suggestions[skill_path] = lines
    return suggestions


def build_patch_suggestion_items(strict_issues: list[str]) -> list[dict[str, object]]:
    by_skill_rules: dict[str, set[str]] = {}
    for issue in strict_issues:
        skill_path, rule_key = parse_strict_issue(issue)
        if skill_path == "unknown":
            continue
        by_skill_rules.setdefault(skill_path, set()).add(rule_key)

    items: list[dict[str, object]] = []
    for skill_path in sorted(by_skill_rules):
        for rule_key in sorted(by_skill_rules[skill_path]):
            items.append(
                {
                    "skill_path": skill_path,
                    "rule": rule_key,
                    "snippet_lines": render_suggestion(rule_key),
                }
            )
    return items


def render_patch_suggestions(strict_issues: list[str], output_format: str) -> str:
    suggestion_items = build_patch_suggestion_items(strict_issues)
    if not suggestion_items:
        return ""

    if output_format == "json":
        return "Suggested migration snippets (json):\n" + json.dumps(
            suggestion_items, ensure_ascii=False, indent=2
        )

    suggestions = build_patch_suggestions(strict_issues)
    lines: list[str] = ["Suggested migration snippets:"]
    for skill_path in sorted(suggestions):
        lines.append(f"- {skill_path}")
        for line in suggestions[skill_path]:
            lines.append(f"  {line}")
    return "\n".join(lines)


def emit_patch_suggestions(
    strict_issues: list[str], output_format: str, output_path: str | None
) -> None:
    content = render_patch_suggestions(strict_issues, output_format)
    if not content:
        return

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content + "\n", encoding="utf-8")
        print(f"Suggested migration snippets written to: {output_file}")
        return

    print(content)


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    failures: list[str] = []
    strict_issues: list[str] = []

    strict_mode = args.strict_skills_mode
    if args.strict_skills:
        strict_mode = "error"

    validate_required_files(root, failures)
    validate_template_skill(root, failures)

    discovered_skill_dirs = sorted((root / "skills").glob("*/SKILL.md"))
    discovered_skill_names = {p.parent.name for p in discovered_skill_dirs}

    for required_skill in REQUIRED_SKILLS:
        if required_skill not in discovered_skill_names:
            fail(
                f"missing required skill: skills/{required_skill}/SKILL.md",
                failures,
                f"add required skill directory and SKILL.md for '{required_skill}'",
            )

    for skill_md in discovered_skill_dirs:
        skill_dir = skill_md.parent
        validate_skill(skill_dir, failures)
        if strict_mode != "off":
            validate_skill_strict(skill_dir, strict_issues)

    if strict_mode == "error" and strict_issues:
        print_strict_summary(strict_issues)
        if args.suggest_patches:
            emit_patch_suggestions(
                strict_issues,
                args.suggest_patches_format,
                args.suggest_patches_output,
            )
        failures.extend(strict_issues)

    if failures:
        print("Repository validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    if strict_mode == "warn" and strict_issues:
        print("Repository validation passed with strict warnings:")
        for issue in strict_issues:
            print(f"- {issue}")
        print_strict_summary(strict_issues)
        if args.suggest_patches:
            emit_patch_suggestions(
                strict_issues,
                args.suggest_patches_format,
                args.suggest_patches_output,
            )
        print(f"Validated {len(discovered_skill_dirs)} skills and {len(REQUIRED_FILES)} shared files.")
        return 0

    print("Repository validation passed.")
    print(f"Validated {len(discovered_skill_dirs)} skills and {len(REQUIRED_FILES)} shared files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
