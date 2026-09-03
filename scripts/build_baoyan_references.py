#!/usr/bin/env python3
"""Build searchable Markdown mirrors for the local baoyan source bundle."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "references" / "baoyan-sources" / "originals"
OUTPUT_DIR = ROOT / "references" / "baoyan-sources" / "searchable"


DOCX_SOURCES = {
    "7.2 2020-2023保研院校真题资料.docx": (
        "2020—2023 新闻传播保研院校真题资料",
        "按院校与年份整理的经验资料和回忆题。",
        "2020-2023-question-bank.md",
    ),
    "清华复习计划表.docx": (
        "清华新闻传播保研复习计划表",
        "个人经验版复习模块、资料与整理方法。",
        "tsinghua-review-plan.md",
    ),
    "简历面mocklist.docx": (
        "简历面 Mock List",
        "个人经历、专业认知、综合素养与申请动机题库。",
        "resume-interview-mocklist.md",
    ),
}


def run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def build_docx_sources() -> None:
    for filename, (title, note, output_name) in DOCX_SOURCES.items():
        body = run(
            [
                "pandoc",
                str(SOURCE_DIR / filename),
                "--from=docx",
                "--to=gfm",
                "--wrap=none",
            ]
        )
        header = (
            f"# {title}\n\n"
            f"> 原件：`../originals/{filename}`\n>\n"
            f"> 资料性质：{note}不代表院校官方发布；引用时必须标原始文件名与章节。\n>\n"
            "> 本文件是检索镜像；若转换文字与原件版式冲突，以原件为准。\n\n"
        )
        (OUTPUT_DIR / output_name).write_text(header + normalize(body), encoding="utf-8")


def build_pdf_source() -> None:
    filename = "25胡师姐新传保研真题.pdf"
    source = SOURCE_DIR / filename
    result = subprocess.run(
        ["pdftotext", "-layout", str(source), "-"],
        check=True,
        capture_output=True,
    )
    raw = result.stdout.decode("utf-8", errors="replace")
    pages = raw.split("\f")
    sections: list[str] = []
    for number, page in enumerate(pages, start=1):
        page = normalize(page)
        if page.strip():
            sections.append(f"## PDF 第 {number} 页\n\n```text\n{page.rstrip()}\n```\n")
    header = (
        "# 25 胡师姐新传保研真题\n\n"
        f"> 原件：`../originals/{filename}`\n>\n"
        "> 资料性质：个人整理的经验资料和回忆题，不代表院校官方发布。\n>\n"
        "> 本文件按 PDF 物理页生成检索镜像；引用时标注原始文件名和“PDF 第 N 页”。\n\n"
    )
    (OUTPUT_DIR / "senior-hu-question-bank.md").write_text(
        header + "\n".join(sections), encoding="utf-8"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_docx_sources()
    build_pdf_source()
    print(f"Built {len(DOCX_SOURCES) + 1} searchable Markdown sources in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
