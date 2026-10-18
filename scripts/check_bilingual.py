#!/usr/bin/env python3
"""Check published English documents have matching Chinese files and working language links."""

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\]\(([^)]+)\)")
ITEM = re.compile(r"^### (\d+)\.", re.MULTILINE)


def check_file(english: Path) -> list:
    relative = english.relative_to(ROOT / "en")
    chinese = ROOT / ("README.zh-CN.md" if relative == Path("README.md") else relative)
    errors = []
    if not chinese.is_file():
        return [f"Missing Chinese counterpart: {chinese}"]
    for source in (english, chinese):
        content = source.read_text(encoding="utf-8")
        for raw in LINK.findall(content):
            if raw.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target = (source.parent / raw.split("#", 1)[0]).resolve()
            if not target.is_file():
                errors.append(f"Broken local link: {source}: {raw}")
        rendered = source.with_suffix(".html")
        if not rendered.is_file():
            errors.append(f"Missing HTML: {rendered}")
        else:
            markup = rendered.read_text(encoding="utf-8")
            language = "en" if source == english else "zh-CN"
            if f'<html lang="{language}">' not in markup:
                errors.append(f"Wrong HTML language: {rendered}")
            if '<nav class="language-switch"' not in markup:
                errors.append(f"Missing HTML language switch: {rendered}")
            for href in re.findall(r'<a href="([^"]+\.html)"', markup.split("</nav>", 1)[0]):
                if not (rendered.parent / href).resolve().is_file():
                    errors.append(f"Broken HTML language switch: {rendered}: {href}")
    english_text = english.read_text(encoding="utf-8")
    chinese_text = chinese.read_text(encoding="utf-8")
    if relative == Path("README.md"):
        if "../README.zh-CN.md" not in english_text or 'href="README.md"' not in chinese_text:
            errors.append("Missing Markdown language switch in legacy English or Chinese README")
    elif "[中文]" not in english_text or "[English]" not in chinese_text:
        errors.append(f"Missing Markdown language switch: {relative}")
    if relative.parts[0] in {"daily", "weekly", "monthly", "quarterly", "yearly"}:
        if english.stem not in english_text or chinese.stem not in chinese_text:
            errors.append(f"Date or period mismatch: {relative}")
        if relative.parts[0] == "daily" and ITEM.findall(english_text) != ITEM.findall(chinese_text):
            errors.append(f"Item numbering differs: {relative}")
    return errors


def main() -> int:
    english_files = sorted((ROOT / "en").rglob("*.md"))
    if not english_files:
        print("No English Markdown files found", file=sys.stderr)
        return 1
    failures = [issue for file in english_files for issue in check_file(file)]
    default = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese_home = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    default_html = ROOT / "README.html"
    if not default_html.is_file() or '<html lang="en">' not in default_html.read_text(encoding="utf-8"):
        failures.append("Default README HTML must exist and be English")
    for source in (ROOT / "README.md", ROOT / "README.zh-CN.md"):
        home = source.read_text(encoding="utf-8")
        for raw in LINK.findall(home) + re.findall(r'<a href="([^"]+)"', home):
            if not raw.startswith(("https://", "http://", "mailto:", "#")) and not (source.parent / raw.split("#", 1)[0]).is_file():
                failures.append(f"Broken homepage link: {source}: {raw}")
    if not default.index("## Current key trends") < default.index("## Historical content"):
        failures.append("Default homepage must show key trends before history")
    if not chinese_home.index("## 当前关键趋势") < chinese_home.index("## 历史内容"):
        failures.append("Chinese homepage must show key trends before history")
    if 'href="README.zh-CN.md"' not in default:
        failures.append("Default homepage must link to the Chinese homepage")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"Checked {len(english_files)} bilingual document pairs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
