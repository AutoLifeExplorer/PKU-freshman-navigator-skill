#!/usr/bin/env python3
"""Validate the V3 skill package using only the Python standard library."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CASES = 26
EXPECTED_ENGINES = {
    "action_brief",
    "decision_panel",
    "map_route",
    "process_guide",
    "time_workbench",
    "checklist_board",
    "editable_artifact",
    "share_media",
}
EXPECTED_RISKS = {"low", "medium", "high"}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def validate_markdown_links(errors: list[str]) -> None:
    pattern = re.compile(r"\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in pattern.findall(text):
            if target.startswith(("http://", "https://", "#")):
                continue
            clean = target.split("#", 1)[0]
            if clean and not (path.parent / clean).exists():
                fail(f"{path.relative_to(ROOT)}: missing linked file {target}", errors)


def main() -> int:
    errors: list[str] = []
    skill = ROOT / "SKILL.md"
    if not skill.exists():
        fail("missing SKILL.md", errors)
    else:
        text = skill.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            fail("SKILL.md must start with YAML frontmatter", errors)
        if not re.search(r"^name:\s*pku-freshman-navigator\s*$", text, re.M):
            fail("unexpected or missing skill name", errors)
        if not re.search(r"^description:\s*\S", text, re.M):
            fail("missing description", errors)
        for phrase in ("一个主输出", "高风险事务", "电脑端默认", "核验模式"):
            if phrase not in text:
                fail(f"SKILL.md missing V3 invariant: {phrase}", errors)

    expected = [
        "references/source-policy.md",
        "references/source-registry.md",
        "references/experience-seed.md",
        "references/scenario-playbooks.md",
        "references/journey-playbooks.md",
        "references/campus-service-playbooks.md",
        "references/output-contracts.md",
        "references/web-ui-spec.md",
        "references/v3-output-system-design.md",
        "references/maintenance.md",
        "assets/examples/freshman-arrival-workbench.html",
        "assets/examples/study-place-decision.html",
        "assets/examples/resource-unlock.html",
        "assets/examples/rule-decision-flow.html",
        "assets/examples/four-year-radar.html",
        "tests/cases.json",
        "tests/TEST_PLAN.md",
    ]
    for relative in expected:
        if not (ROOT / relative).exists():
            fail(f"missing required package file: {relative}", errors)

    validate_markdown_links(errors)

    cases_path = ROOT / "tests/cases.json"
    cases: list[dict[str, object]] = []
    if cases_path.exists():
        try:
            cases = json.loads(cases_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"invalid tests/cases.json: {exc}", errors)
        if len(cases) != EXPECTED_CASES:
            fail(f"expected exactly {EXPECTED_CASES} fixed behavior cases", errors)
        ids = [case.get("id") for case in cases]
        if len(ids) != len(set(ids)):
            fail("duplicate test case ids", errors)
        required = {
            "id",
            "prompt",
            "route",
            "must_search",
            "expected_engine",
            "must_ask",
            "risk",
            "invariants",
        }
        for index, case in enumerate(cases):
            missing = required - set(case)
            if missing:
                fail(f"case {index} missing fields: {sorted(missing)}", errors)
            engine = case.get("expected_engine")
            if engine not in EXPECTED_ENGINES:
                fail(f"case {index} has unknown engine: {engine}", errors)
            risk = case.get("risk")
            if risk not in EXPECTED_RISKS:
                fail(f"case {index} has unknown risk: {risk}", errors)
            invariants = case.get("invariants")
            if not isinstance(invariants, list) or len(invariants) < 3:
                fail(f"case {index} needs at least three meaningful invariants", errors)

        required_routes = {
            "arrival",
            "course",
            "place",
            "campus_life",
            "health_safety",
            "financial_support",
            "digital_service",
            "campus_participation",
            "rule",
            "planning",
            "fallback",
            "limited_scope",
        }
        actual_routes = {str(case.get("route")) for case in cases}
        missing_routes = required_routes - actual_routes
        if missing_routes:
            fail(f"behavior cases missing routes: {sorted(missing_routes)}", errors)

    expected_types = {
        "freshman-arrival-workbench.html": "arrival",
        "study-place-decision.html": "place",
        "resource-unlock.html": "resource",
        "rule-decision-flow.html": "rule",
        "four-year-radar.html": "planning",
    }
    html_paths = sorted((ROOT / "assets/examples").glob("*.html"))
    if len(html_paths) != len(expected_types):
        fail(f"expected exactly {len(expected_types)} HTML examples, found {len(html_paths)}", errors)

    for html_path in html_paths:
        html = html_path.read_text(encoding="utf-8")
        checks = {
            "lang=zh-CN": 'lang="zh-CN"' in html,
            "viewport": 'name="viewport"' in html,
            "semantic main": "<main" in html and "</main>" in html,
            "demo boundary": "演示数据" in html,
            "primary decision": 'data-role="primary-decision"' in html,
            "primary action": 'data-role="primary-action"' in html,
            "noscript fallback": "<noscript>" in html,
            "reduced motion": "prefers-reduced-motion" in html,
            "evidence drawer": "<details" in html and "<summary" in html,
            "status text": any(label in html for label in ("已核实", "经验判断", "待核实")),
        }
        for label, ok in checks.items():
            if not ok:
                fail(f"{html_path.name}: missing {label}", errors)

        expected_type = expected_types.get(html_path.name)
        if expected_type and f'data-example-type="{expected_type}"' not in html:
            fail(f"{html_path.name}: missing example type {expected_type}", errors)

        forbidden = {
            "external script": r"<script[^>]+src=",
            "external stylesheet": r"<link[^>]+stylesheet",
            "CSS import": r"@import\s",
            "tracking storage": r"localStorage|sessionStorage|document\.cookie",
            "V1 global disclaimer": r"信息核验：本回答按|非北京大学官方产品",
        }
        for label, pattern in forbidden.items():
            if re.search(pattern, html, re.I):
                fail(f"{html_path.name}: contains {label}", errors)

    arrival = ROOT / "assets/examples/freshman-arrival-workbench.html"
    if arrival.exists():
        arrival_text = arrival.read_text(encoding="utf-8")
        v3_checks = {
            "V3 marker": 'data-v3-workbench="true"' in arrival_text,
            "conversation panel": 'data-role="conversation-panel"' in arrival_text,
            "task workbench": 'data-role="task-workbench"' in arrival_text,
            "operation log": 'data-role="operation-log"' in arrival_text,
            "calendar preview dialog": 'id="calendar-dialog"' in arrival_text,
            "share preview dialog": 'id="share-dialog"' in arrival_text,
            "redaction preview": "已移除" in arrival_text,
            "portal permission boundary": "不接触密码" in arrival_text,
        }
        for label, ok in v3_checks.items():
            if not ok:
                fail(f"freshman-arrival-workbench.html: missing {label}", errors)
        for token in (
            "BEGIN:VCALENDAR",
            "END:VCALENDAR",
            "DTSTART;TZID=Asia/Shanghai",
            "URL:https://fresh.pku.edu.cn/",
        ):
            if token not in arrival_text:
                fail(f"freshman-arrival-workbench.html: incomplete calendar preview ({token})", errors)

    radar = ROOT / "assets/examples/four-year-radar.html"
    if radar.exists():
        radar_text = radar.read_text(encoding="utf-8")
        for token in (
            "BEGIN:VCALENDAR",
            "END:VCALENDAR",
            "DTSTART;TZID=Asia/Shanghai",
            "URL:https://dean.pku.edu.cn/",
        ):
            if token not in radar_text:
                fail(f"four-year-radar.html: incomplete calendar export ({token})", errors)

    registry = ROOT / "references/source-registry.md"
    if registry.exists():
        registry_text = registry.read_text(encoding="utf-8")
        for domain in (
            "fresh.pku.edu.cn",
            "dean.pku.edu.cn",
            "zwb.pku.edu.cn",
            "cyzx.pku.edu.cn",
            "hospital.pku.edu.cn",
            "bwb.pku.edu.cn",
            "sfao.pku.edu.cn",
        ):
            if domain not in registry_text:
                fail(f"source registry missing core domain: {domain}", errors)

    unfinished_markers = ("TO" + "DO", "T" + "BD", "PLACE" + "HOLDER", "lorem" + " ipsum")
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".html", ".json", ".py"}:
            content = path.read_text(encoding="utf-8").lower()
            if any(marker.lower() in content for marker in unfinished_markers):
                fail(f"unfinished scaffold marker in {path.relative_to(ROOT)}", errors)

    if errors:
        print("PACKAGE VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PACKAGE VALIDATION PASSED")
    print(f"- root: {ROOT}")
    print(f"- fixed behavior cases: {len(cases)}")
    print(f"- HTML examples: {len(html_paths)}")
    print("- V3 workbench example: 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
