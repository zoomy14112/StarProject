#!/usr/bin/env python3
"""
md2html.py — Convert Markdown to Typora-compatible HTML (based on
StarProject.html / Reverse.html template).

Usage:
    python3 md2html.py <input.md> [output.html]
    python3 md2html.py --batch <directory>
    python3 md2html.py --batch <directory> --output-dir <dir>

Dependencies:
    - markdown-it-py (system package: python3-markdown-it-py)
    - Pygments      (system package: python3-pygments)

The output HTML uses the same CSS / wrapper structure as the existing
StarProject.html and Reverse.html files (Typora export format).
"""

import argparse
import os
import re
import sys
from html import escape
from pathlib import Path


# ---------------------------------------------------------------------------
# Dependency checks — bail early if a required library is missing
# ---------------------------------------------------------------------------

def _check_deps() -> None:
    missing = []
    try:
        from markdown_it import MarkdownIt  # noqa: F401
    except ModuleNotFoundError:
        missing.append("markdown-it-py (python3-markdown-it-py)")

    try:
        import pygments  # noqa: F401
    except ModuleNotFoundError:
        missing.append("Pygments (python3-pygments)")

    if missing:
        print("Missing dependencies:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print("\nInstall with:", file=sys.stderr)
        print("  sudo apt install python3-markdown-it-py python3-pygments", file=sys.stderr)
        print("  # or:  pip3 install --break-system-packages markdown-it-py Pygments", file=sys.stderr)
        sys.exit(1)


_check_deps()

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound


# ---------------------------------------------------------------------------
# Paths — all template files live next to this script
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
CSS_FILE = SCRIPT_DIR / 'typora-export.css'
PROLOGUE_FILE = SCRIPT_DIR / 'typora-prologue.html'

# ---------------------------------------------------------------------------
# GitHub-style heading slug
# ---------------------------------------------------------------------------

def _heading_slug(text: str) -> str:
    """Generate a heading anchor ID (GitHub convention)."""
    slug = text.lower().strip()
    slug = re.sub(r'[^\x00-\x7F]+', '', slug)        # strip non-ASCII
    slug = re.sub(r'[^\w\s-]', '', slug)             # strip punctuation
    slug = re.sub(r'[\s_]+', '-', slug)              # whitespace → hyphen
    slug = re.sub(r'-{2,}', '-', slug)               # collapse hyphens
    return slug.strip('-')


def _unique_slug(slug: str, used: set) -> str:
    """If *slug* is empty or already in *used*, append -1, -2, ..."""
    if not slug:
        slug = 'heading'
    original = slug
    counter = 1
    while slug in used:
        counter += 1
        slug = f'{original}-{counter}'
    used.add(slug)
    return slug


# ---------------------------------------------------------------------------
# Custom renderer — inject id= attribute on headings
# ---------------------------------------------------------------------------

class _HeadingIdRenderer(RendererHTML):
    """markdown-it renderer that adds GitHub-style heading IDs."""

    def __init__(self, parser=None):
        super().__init__(parser)
        self._slugs: set = set()

    def heading_open(self, tokens, idx, options, env):
        token = tokens[idx]
        if idx + 1 < len(tokens) and tokens[idx + 1].type == 'inline':
            text = tokens[idx + 1].content
        else:
            text = ''
        slug = _unique_slug(_heading_slug(text), self._slugs)
        tag = token.tag
        return f'<{tag} id=\'{escape(slug)}\'>'

    def heading_close(self, tokens, idx, options, env):
        return f'</{tokens[idx].tag}>\n'


# ---------------------------------------------------------------------------
# Code highlighting callback
# ---------------------------------------------------------------------------

def _highlight(code: str, lang: str, _attrs: str = '') -> str:
    if not lang:
        lang = 'text'
    try:
        lexer = get_lexer_by_name(lang, stripall=True)
    except ClassNotFound:
        lexer = get_lexer_by_name('text', stripall=True)
    formatter = HtmlFormatter(nowrap=True, style='default')
    return highlight(code, lexer, formatter)


# ---------------------------------------------------------------------------
# Post-processing helpers (applied to rendered HTML body)
# ---------------------------------------------------------------------------

_TASK_RE = re.compile(
    r'<li>\s*\[([ xX])\]\s*(.*?)</li>',
    re.DOTALL,
)

_TASK_TMPL = (
    '<li class="task-list-item">'
    '<input type="checkbox" class="task-list-item-checkbox" disabled{checked}>'
    '<span>{content}</span>'
    '</li>'
)


def _fix_task_lists(html: str) -> str:
    def _replace(m: re.Match) -> str:
        checked = ' checked' if m.group(1).lower() == 'x' else ''
        return _TASK_TMPL.format(checked=checked, content=m.group(2))
    return _TASK_RE.sub(_replace, html)


_MERMAID_RE = re.compile(
    r'<pre><code class="language-mermaid">(.*?)</code></pre>',
    re.DOTALL,
)


def _fix_mermaid(html: str) -> str:
    return _MERMAID_RE.sub(r'<div class="mermaid">\1</div>', html)


# ---------------------------------------------------------------------------
# Fix **text** patterns that markdown-it-py misses due to CJK punctuation
# flanking rules (CommonMark spec §6.2).
#
# When a closing ** is preceded by a CJK punctuation character（：。！？，、；）
# and followed immediately by a CJK letter, markdown-it-py refuses to
# recognise it as a right-flanking delimiter.  We catch these leftovers here.
# ---------------------------------------------------------------------------

# Blocks whose content must NOT be touched
_PROTECTED_BLOCKS = [
    re.compile(r'(<pre[^>]*>.*?</pre>)', re.DOTALL),
    re.compile(r'(<code[^>]*>.*?</code>)', re.DOTALL),
    re.compile(r'(<style[^>]*>.*?</style>)', re.DOTALL),
]

_REMAINING_BOLD = re.compile(r'\*\*(.+?)\*\*')


def _fix_remaining_bold(html: str) -> str:
    """Convert any leftover **text** markers into <strong>text</strong>.

    Protected blocks (pre / code / style) are temporarily removed so their
    literal asterisks are not altered.
    """
    # 1. Pull out protected blocks
    protected: list[str] = []
    for pattern in _PROTECTED_BLOCKS:
        def _collect(m: re.Match, _pat=pattern) -> str:
            protected.append(m.group(1))
            return f'\x00PROTECT{len(protected)-1}\x00'
        html = pattern.sub(_collect, html)

    # 2. Convert stray **text** → <strong>text</strong>
    html = _REMAINING_BOLD.sub(r'<strong>\1</strong>', html)

    # 3. Restore protected blocks
    for i, block in enumerate(protected):
        html = html.replace(f'\x00PROTECT{i}\x00', block)

    return html


def _fix_footnotes(html: str) -> str:
    """Convert markdown-it footnote markup to Typora-compatible format.

    markdown-it (with footnote plugin) generates:
      <sup class="footnote-ref"><a href="#fn1" id="fnref1">[1]</a></sup>
      ...
      <hr class="footnotes-sep">
      <section class="footnotes">
        <ol class="footnotes-list">
          <li id="fn1"><p>note text <a href="#fnref1" class="footnote-backref">↩︎</a></p></li>
        </ol>
      </section>

    Typora format:
      In-text: <sup><a href='#ref-footnote-1'>[1]</a></sup>
      Footnote area:
        <div class='footnotes-area'><hr/>
        <div class='footnote-line'><span class='md-fn-count'>1</span> <span>note text</span>
        <a name='dfref-footnote-1' href='#ref-footnote-1' title='回到文档' class='reversefootnote'>↩</a></div>
        </div>
    """
    # Process footnotes section at the end of the document
    # Look for the markdown-it footnotes section and convert it
    fn_section = re.search(
        r'<hr class="footnotes-sep">\s*<section class="footnotes">\s*<ol class="footnotes-list">(.*?)</ol>\s*</section>',
        html, re.DOTALL,
    )
    if not fn_section:
        return html

    fn_list_html = fn_section.group(1)

    # Extract individual footnote items
    fn_items = re.findall(
        r'<li id="fn(\d+)">\s*<p>(.*?)<a href="#fnref\d+" class="footnote-backref".*?</a>\s*</p>\s*</li>',
        fn_list_html, re.DOTALL,
    )

    # Build Typora footnotes area
    fn_lines = []
    for fn_id, note_text in fn_items:
        # Clean up the note text (remove trailing newlines etc.)
        note_text = note_text.strip()
        fn_lines.append(
            f'<div class=\'footnote-line\'>'
            f'<span class=\'md-fn-count\'>{fn_id}</span>'
            f' <span>{note_text}</span> '
            f'<a name=\'dfref-footnote-{fn_id}\' href=\'#ref-footnote-{fn_id}\' '
            f'title=\'回到文档\' class=\'reversefootnote\'>↩</a>'
            f'</div>'
        )

    typora_fn_area = (
        f'<div class=\'footnotes-area\'><hr/>\n'
        + '\n'.join(fn_lines) +
        f'</div>'
    )

    # Remove the markdown-it footnotes section
    html = html[:fn_section.start()] + html[fn_section.end():]

    # Insert Typora footnotes AREA before the closing of body content
    # The footnotes need to be inside #write, before its closing </div>
    # Since we handle this in the full HTML assembly, just return the modified body
    html = html.rstrip() + '\n' + typora_fn_area

    return html


# ---------------------------------------------------------------------------
# Markdown → body HTML
# ---------------------------------------------------------------------------

def render_body(md_text: str) -> str:
    """Render markdown to inner-body HTML (content that goes inside #write)."""
    md = MarkdownIt('gfm-like', {
        'linkify': False,
        'highlight': _highlight,
    }, renderer_cls=_HeadingIdRenderer)

    html = md.render(md_text)
    html = _fix_task_lists(html)
    html = _fix_mermaid(html)
    html = _fix_remaining_bold(html)
    html = _fix_footnotes(html)
    return html


# ---------------------------------------------------------------------------
# HTML assembly — wrap body content in Typora-compatible template
# ---------------------------------------------------------------------------

def _load_prologue() -> str:
    """Read the HTML prologue from typora-prologue.html."""
    if PROLOGUE_FILE.is_file():
        return PROLOGUE_FILE.read_text(encoding='utf-8')
    # Fallback: generate minimal Typora prologue from the CSS file
    css = _load_css()
    font_link = (
        "<link href='https://fonts.googleapis.com/css?family=Open+Sans:400italic,"
        "700italic,700,400&subset=latin,latin-ext' rel='stylesheet' type='text/css' />"
    )
    return f"""<!doctype html>
<html style='font-size:18px !important'>
<head>
<meta charset='UTF-8'><meta name='viewport' content='width=device-width initial-scale=1'>
{font_link}<style type='text/css'>{css}</style>
</head>
<body class='typora-export os-windows'><div class='typora-export-content'>
<div id='write' class=''>
"""


def _load_css() -> str:
    """Read the Typora CSS from typora-export.css."""
    if CSS_FILE.is_file():
        return CSS_FILE.read_text(encoding='utf-8')
    # Absolute minimal fallback
    return """html{overflow-x:initial!important}:root{--bg-color:#fff;--text-color:#333}
body{margin:0;padding:0;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}"""


_TITLE_RE = re.compile(r'<title>[^<]*</title>')


# CSS injected after the prologue to ensure bold / strong always renders
_EXTRA_CSS = (
    '<style>'
    '#write strong,#write b{font-weight:bold!important}'
    '#write em,#write i{font-style:italic!important}'
    '</style>'
)

# Regex to strip ** markers from inside URL hrefs (leftover from #### anchor links)
_URL_ASTERISK_RE = re.compile(r'(href="[^"]*)\*\*([^"]*)\*\*([^"]*")')


def build_html(md_text: str, title: str = '') -> str:
    """Convert markdown to a complete Typora-compatible HTML document."""
    prologue = _load_prologue()
    # Replace the title from the template with the actual document title
    prologue = _TITLE_RE.sub(f'<title>{escape(title)}</title>', prologue)
    # Inject extra CSS before </head> to ensure bold/italic always render
    prologue = prologue.replace('</head>', _EXTRA_CSS + '</head>')
    body = render_body(md_text)

    # Strip ** markers from href URLs (anchor links that contain inline bold)
    body = _URL_ASTERISK_RE.sub(r'\1\2\3', body)

    # The epilogue closes #write, typora-export-content, and body/html
    # Typora HTML has footnotes INSIDE #write, which our body rendering
    # already includes via _fix_footnotes.
    epilogue = '\n</div>\n</div>\n</body>\n</html>\n'

    return prologue + body + epilogue


# ---------------------------------------------------------------------------
# File-level helpers
# ---------------------------------------------------------------------------

def convert_file(input_path: Path, output_path: Path) -> None:
    md_text = input_path.read_text(encoding='utf-8')
    html = build_html(md_text, title=input_path.stem)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding='utf-8')
    print(f'✔  {input_path.name}  →  {output_path.name}')


def batch_convert(input_dir: Path, output_dir: Path | None = None) -> None:
    md_files = sorted(input_dir.glob('*.md'))
    if not md_files:
        print(f'No .md files found in {input_dir}')
        return
    out_dir = output_dir or input_dir
    for md_file in md_files:
        out_path = out_dir / (md_file.stem + '.html')
        convert_file(md_file, out_path)
    print(f'\nDone — {len(md_files)} file(s) converted.')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Convert Markdown to Typora-style HTML.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 md2html.py README.md
  python3 md2html.py input.md output.html
  python3 md2html.py --batch ./docs
  python3 md2html.py --batch ./docs --output-dir ./html
        """,
    )
    parser.add_argument(
        'input', nargs='?',
        help='Input .md file path',
    )
    parser.add_argument(
        'output', nargs='?', default=None,
        help='Output .html file path (default: same name with .html extension)',
    )
    parser.add_argument(
        '--batch', '-b', default=None,
        help='Batch mode: convert all .md files in a directory',
    )
    parser.add_argument(
        '--output-dir', '-o', default=None,
        help='Output directory for batch mode (default: same as input dir)',
    )

    args = parser.parse_args()

    if args.batch:
        batch_convert(
            Path(args.batch).resolve(),
            Path(args.output_dir).resolve() if args.output_dir else None,
        )
        return

    if not args.input:
        parser.print_help()
        sys.exit(1)

    src = Path(args.input).resolve()
    if not src.is_file():
        print(f'Error: file not found — {src}', file=sys.stderr)
        sys.exit(1)

    dst = Path(args.output).resolve() if args.output else src.with_suffix('.html')
    convert_file(src, dst)


if __name__ == '__main__':
    main()
