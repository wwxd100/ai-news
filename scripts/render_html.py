#!/usr/bin/env python3
"""Render repository Markdown as paired Chinese/English HTML.

Usage: python3 scripts/render_html.py README.md README.zh-CN.md daily/2026-10/2026-10-18.md ...
Rendering Markdown and Mermaid in the browser uses the marked/mermaid CDNs.
"""

import argparse
import html
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; --fg:#1f2328; --bg:#fff; --muted:#656d76; --line:#d0d7de; --code:#f6f8fa; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --fg:#e6edf3; --bg:#0d1117; --muted:#8d96a0; --line:#30363d; --code:#161b22; }} }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.7 -apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", sans-serif; }}
  main {{ max-width:960px; margin:0 auto; padding:40px 24px 80px; }}
  h1,h2,h3 {{ line-height:1.3; }} h1,h2 {{ border-bottom:1px solid var(--line); padding-bottom:.3em; }}
  a {{ color:#0969da; }} blockquote {{ margin:0; padding:0 1em; color:var(--muted); border-left:4px solid var(--line); }}
  code {{ background:var(--code); padding:.15em .4em; border-radius:6px; font-size:.9em; }}
  pre {{ background:var(--code); padding:16px; border-radius:8px; overflow:auto; }} pre code {{ padding:0; }}
  table {{ border-collapse:collapse; display:block; overflow:auto; }}
  th,td {{ border:1px solid var(--line); padding:6px 12px; }}
  .language-switch {{ max-width:960px; margin:0 auto; padding:16px 24px 0; text-align:right; }}
  .language-switch a {{ margin-left:12px; }}
  .language-switch [aria-current="page"] {{ color:var(--fg); font-weight:600; text-decoration:none; }}
  .mermaid {{ display:flex; justify-content:center; margin:24px 0; padding:16px; border:1px solid var(--line); border-radius:12px; overflow:auto; }}
  .mermaid-error {{ color:#cf222e; white-space:pre-wrap; }}
</style>
</head>
<body>
{navigation}
<main id="content"></main>
<script type="module">
import {{ marked }} from "https://cdn.jsdelivr.net/npm/marked@12/lib/marked.esm.js";
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
const source = {source};
const root = document.getElementById("content");
root.innerHTML = marked.parse(source);
root.querySelectorAll("pre > code.language-mermaid").forEach((code) => {{
  const div = document.createElement("div");
  div.className = "mermaid";
  div.textContent = code.textContent;
  code.parentElement.replaceWith(div);
}});
const dark = matchMedia("(prefers-color-scheme: dark)").matches;
mermaid.initialize({{ startOnLoad: false, theme: dark ? "dark" : "default", securityLevel: "strict" }});
for (const el of root.querySelectorAll(".mermaid")) {{
  try {{ await mermaid.run({{ nodes: [el] }}); }}
  catch (e) {{ el.classList.add("mermaid-error"); el.textContent = {error_prefix} + e.message; }}
}}
document.body.dataset.rendered = "true";
</script>
</body>
</html>
"""


def counterpart(relative: Path) -> Path:
    if relative == Path("README.md"):
        return ROOT / "README.zh-CN.md"
    if relative == Path("README.zh-CN.md"):
        return ROOT / "README.md"
    if relative == Path("en/README.md"):
        return ROOT / "README.zh-CN.md"
    if relative.parts[0] == "en":
        return ROOT.joinpath(*relative.parts[1:])
    return ROOT / "en" / relative


def render(src: Path) -> Path:
    src = src.resolve()
    relative = src.relative_to(ROOT)
    if src.suffix != ".md":
        raise ValueError(f"Expected Markdown: {src}")
    markdown = src.read_text(encoding="utf-8")
    english = relative == Path("README.md") or relative.parts[0] == "en"
    lang = "en" if english else "zh-CN"
    dest = src.with_suffix(".html")
    other = counterpart(relative)
    navigation = ""
    if other.is_file():
        zh = other if english else src
        en = src if english else other
        links = []
        for label, target, active in (("中文", zh, not english), ("English", en, english)):
            href = html.escape(os.path.relpath(target.with_suffix(".html"), dest.parent), quote=True)
            current = ' aria-current="page"' if active else ""
            links.append(f'<a href="{href}" lang="{"zh-CN" if label == "中文" else "en"}"{current}>{label}</a>')
        navigation = '<nav class="language-switch" aria-label="Language / 语言">' + "".join(links) + "</nav>"
    title = next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), src.stem)
    source = json.dumps(markdown, ensure_ascii=False).replace("</", "<\\/")
    output = TEMPLATE.format(
        lang=lang,
        title=html.escape(title),
        navigation=navigation,
        source=source,
        error_prefix=json.dumps("Mermaid syntax error: " if english else "Mermaid 语法错误："),
    )
    dest.write_text(output, encoding="utf-8")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.files:
        print(render(path))


if __name__ == "__main__":
    main()
