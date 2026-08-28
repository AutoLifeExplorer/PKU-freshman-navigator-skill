#!/usr/bin/env python3
"""Validate the V2 skill package using only the Python standard library."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


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
        for relative in re.findall(r"\]\((references/[^)]+)\)", text):
            if not (ROOT / relative).exists():
                fail(f"missing referenced file: {relative}", errors)

    expected = [
        "references/source-policy.md",
        "references/source-registry.md",
        "references/experience-seed.md",
        "references/scenario-playbooks.md",
        "references/output-contracts.md",
        "references/web-ui-spec.md",
        "references/maintenance.md",
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

    cases_path = ROOT / "tests/cases.json"
    cases: list[dict[str, object]] = []
    if cases_path.exists():
        try:
            cases = json.loads(cases_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"invalid tests/cases.json: {exc}", errors)
        if len(cases) != 12:
            fail("expected exactly 12 fixed behavior cases", errors)
        ids = [case.get("id") for case in cases]
        if len(ids) != len(set(ids)):
            fail("duplicate test case ids", errors)
        required = {"id", "prompt", "route", "must_search", "expected_format", "must_ask", "invariants"}
        for index, case in enumerate(cases):
            missing = required - set(case)
            if missing:
                fail(f"case {index} missing fields: {sorted(missing)}", errors)

    expected_types = {
        "study-place-decision.html": "place",
        "resource-unlock.html": "resource",
        "rule-decision-flow.html": "rule",
        "four-year-radar.html": "planning",
    }
    html_paths = sorted((ROOT / "assets/examples").glob("*.html"))
    if len(html_paths) != 4:
        fail(f"expected exactly 4 HTML examples, found {len(html_paths)}", errors)

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

    radar = ROOT / "assets/examples/four-year-radar.html"
    if radar.exists():
        radar_text = radar.read_text(encoding="utf-8")
        for token in ("BEGIN:VCALENDAR", "END:VCALENDAR", "DTSTART;TZID=Asia/Shanghai", "URL:https://dean.pku.edu.cn/"):
            if token not in radar_text:
                fail(f"four-year-radar.html: incomplete calendar export ({token})", errors)

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
