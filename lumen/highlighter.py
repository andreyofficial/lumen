"""Lightweight regex-based syntax highlighter for several languages."""

from __future__ import annotations

import re
from dataclasses import dataclass

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)

from .theme import PALETTE


def _fmt(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.DemiBold)
    if italic:
        f.setFontItalic(True)
    return f


# ---------- Language definitions ----------

@dataclass
class MultilineRule:
    start: QRegularExpression
    end: QRegularExpression
    fmt: QTextCharFormat
    state_id: int


@dataclass
class LangSpec:
    name: str
    keywords: tuple[str, ...] = ()
    keywords2: tuple[str, ...] = ()
    constants: tuple[str, ...] = ()
    types: tuple[str, ...] = ()
    line_comment: str | None = None
    block_comment: tuple[str, str] | None = None
    triple_strings: tuple[str, ...] = ()  # (delimiter,)
    string_quotes: tuple[str, ...] = ('"', "'")
    extra_rules: tuple[tuple[str, QTextCharFormat], ...] = ()


_PY = LangSpec(
    name="python",
    keywords=(
        "False None True and as assert async await break class continue def del "
        "elif else except finally for from global if import in is lambda nonlocal "
        "not or pass raise return try while with yield match case"
    ).split(),
    keywords2=("self", "cls"),
    constants=("True", "False", "None", "NotImplemented", "Ellipsis"),
    types=(
        "int float str bytes bool list dict tuple set frozenset complex bytearray "
        "object type Exception BaseException ValueError TypeError KeyError IndexError"
    ).split(),
    line_comment="#",
    triple_strings=('"""', "'''"),
)

_JS_KW = (
    "break case catch class const continue debugger default delete do else enum "
    "export extends false finally for function if implements import in instanceof "
    "interface let new null of package private protected public return static super "
    "switch this throw true try typeof undefined var void while with yield async await"
).split()

_TS_KW = _JS_KW + ["abstract", "as", "namespace", "readonly", "type", "from", "satisfies"]

_JS = LangSpec(
    name="javascript",
    keywords=tuple(_JS_KW),
    constants=("true", "false", "null", "undefined", "NaN", "Infinity"),
    types=("string", "number", "boolean", "any", "object", "Array", "Promise"),
    line_comment="//",
    block_comment=("/*", "*/"),
    triple_strings=("`",),  # template literal — handled as multiline string
)
_TS = LangSpec(
    name="typescript",
    keywords=tuple(_TS_KW),
    constants=("true", "false", "null", "undefined", "NaN", "Infinity"),
    types=(
        "string number boolean any unknown never void object Array Promise Record "
        "Partial Required Readonly Pick Omit Map Set"
    ).split(),
    line_comment="//",
    block_comment=("/*", "*/"),
    triple_strings=("`",),
)

_C = LangSpec(
    name="c",
    keywords=(
        "auto break case char const continue default do double else enum extern "
        "float for goto if inline int long register restrict return short signed "
        "sizeof static struct switch typedef union unsigned void volatile while "
        "_Bool _Complex _Imaginary"
    ).split(),
    constants=("NULL", "true", "false"),
    types=("size_t ssize_t int8_t int16_t int32_t int64_t uint8_t uint16_t uint32_t uint64_t FILE").split(),
    line_comment="//",
    block_comment=("/*", "*/"),
)

_CPP = LangSpec(
    name="cpp",
    keywords=(
        _C.keywords
        + ("class namespace template typename public private protected virtual override "
           "final new delete this nullptr explicit friend using throw try catch "
           "constexpr noexcept decltype static_cast dynamic_cast reinterpret_cast "
           "const_cast operator").split()
    ),
    constants=("nullptr", "true", "false", "NULL"),
    types=("std string vector map unordered_map set unordered_set list array auto").split(),
    line_comment="//",
    block_comment=("/*", "*/"),
)

_GO = LangSpec(
    name="go",
    keywords=(
        "break case chan const continue default defer else fallthrough for func go "
        "goto if import interface map package range return select struct switch type var"
    ).split(),
    constants=("true", "false", "nil", "iota"),
    types=("int int8 int16 int32 int64 uint uint8 uint16 uint32 uint64 byte rune "
           "float32 float64 string bool error any").split(),
    line_comment="//",
    block_comment=("/*", "*/"),
)

_RUST = LangSpec(
    name="rust",
    keywords=(
        "as async await break const continue crate dyn else enum extern fn for if "
        "impl in let loop match mod move mut pub ref return self Self static struct "
        "super trait type unsafe use where while box union"
    ).split(),
    constants=("true", "false", "None", "Some", "Ok", "Err"),
    types=("i8 i16 i32 i64 i128 isize u8 u16 u32 u64 u128 usize f32 f64 bool char str String Vec Option Result Box").split(),
    line_comment="//",
    block_comment=("/*", "*/"),
)

_BASH = LangSpec(
    name="shell",
    keywords=(
        "if then else elif fi case esac for in do done while until "
        "function return break continue exit local export declare readonly select"
    ).split(),
    constants=("true", "false"),
    line_comment="#",
)

_JSON = LangSpec(
    name="json",
    constants=("true", "false", "null"),
)

_CSS = LangSpec(
    name="css",
    line_comment=None,
    block_comment=("/*", "*/"),
)

# Languages with structural highlighter (HTML/Markdown) handled in subclasses.

_LANG_BY_NAME: dict[str, LangSpec] = {
    "python": _PY,
    "javascript": _JS,
    "typescript": _TS,
    "json": _JSON,
    "c": _C,
    "cpp": _CPP,
    "go": _GO,
    "rust": _RUST,
    "shell": _BASH,
    "css": _CSS,
}


# Public mapping consumed by the code-completion popup so each language's
# keywords feed straight into the suggestion list.
LANG_KEYWORDS: dict[str, tuple[str, ...]] = {
    name: tuple(sorted(set(spec.keywords) | set(spec.keywords2)
                       | set(spec.constants) | set(spec.types)))
    for name, spec in _LANG_BY_NAME.items()
}


_EXT_TO_LANG = {
    ".py": "python", ".pyw": "python", ".pyi": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".json": "json", ".jsonc": "json",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp", ".hxx": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".css": "css", ".scss": "css", ".less": "css",
    ".html": "html", ".htm": "html", ".xml": "html", ".svg": "html",
    ".md": "markdown", ".markdown": "markdown",
    ".yml": "yaml", ".yaml": "yaml",
    ".toml": "toml",
    ".ini": "ini", ".cfg": "ini",
}


def detect_language(filename: str | None, text: str = "") -> str:
    if filename:
        lower = filename.lower()
        for ext, lang in _EXT_TO_LANG.items():
            if lower.endswith(ext):
                return lang
        if lower.endswith("makefile") or "/makefile" in lower:
            return "shell"
    if text.startswith("#!"):
        first = text.splitlines()[0]
        if "python" in first:
            return "python"
        if any(x in first for x in ("bash", "sh", "zsh")):
            return "shell"
        if "node" in first:
            return "javascript"
    return "text"


def comment_marker_for(language: str) -> str:
    spec = _LANG_BY_NAME.get(language)
    if spec and spec.line_comment:
        return spec.line_comment
    if language in ("html", "xml"):
        return "<!--"
    if language == "markdown":
        return "<!--"
    if language == "css":
        return "/*"
    return "#"


# ---------- Highlighter ----------

class CodeHighlighter(QSyntaxHighlighter):
    """Multi-language syntax highlighter."""

    def __init__(self, document: QTextDocument, language: str = "text") -> None:
        super().__init__(document)
        self._language = "text"
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._multiline: list[MultilineRule] = []
        self.set_language(language)

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        self._language = language
        self._rules = []
        self._multiline = []

        # Special-case languages
        if language == "html":
            self._build_html()
        elif language == "markdown":
            self._build_markdown()
        elif language == "yaml":
            self._build_yaml()
        elif language == "toml":
            self._build_toml()
        elif language == "ini":
            self._build_ini()
        elif language == "css":
            self._build_css()
        elif language in _LANG_BY_NAME:
            self._build_generic(_LANG_BY_NAME[language])
        # text -> nothing
        self.rehighlight()

    # -- Builders --

    def _build_generic(self, spec: LangSpec) -> None:
        # Numbers
        self._rules.append((
            QRegularExpression(r"\b(0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|\d[\d_]*\.?\d*([eE][+-]?\d+)?)\b"),
            _fmt(PALETTE.syn_number),
        ))
        # Constants
        if spec.constants:
            self._rules.append((
                QRegularExpression(rf"\b(?:{'|'.join(map(re.escape, spec.constants))})\b"),
                _fmt(PALETTE.syn_constant, bold=True),
            ))
        # Types
        if spec.types:
            self._rules.append((
                QRegularExpression(rf"\b(?:{'|'.join(map(re.escape, spec.types))})\b"),
                _fmt(PALETTE.syn_type),
            ))
        # Keywords (primary)
        if spec.keywords:
            self._rules.append((
                QRegularExpression(rf"\b(?:{'|'.join(map(re.escape, spec.keywords))})\b"),
                _fmt(PALETTE.syn_keyword, bold=True),
            ))
        # Keywords secondary (self/cls etc)
        if spec.keywords2:
            self._rules.append((
                QRegularExpression(rf"\b(?:{'|'.join(map(re.escape, spec.keywords2))})\b"),
                _fmt(PALETTE.syn_keyword2, italic=True),
            ))

        # Operators / punctuation
        self._rules.append((
            QRegularExpression(r"[+\-*/%=<>!&|\^~?:]+"),
            _fmt(PALETTE.syn_operator),
        ))
        self._rules.append((
            QRegularExpression(r"[\(\)\{\}\[\];,\.]"),
            _fmt(PALETTE.syn_punct),
        ))

        # Function calls
        self._rules.append((
            QRegularExpression(r"\b([A-Za-z_][A-Za-z0-9_]*)(?=\s*\()"),
            _fmt(PALETTE.syn_function),
        ))
        # Class-style names (CamelCase)
        self._rules.append((
            QRegularExpression(r"\b([A-Z][A-Za-z0-9_]+)\b"),
            _fmt(PALETTE.syn_class),
        ))

        # Decorators (Python @)
        if spec.name == "python":
            self._rules.append((
                QRegularExpression(r"@\s*[A-Za-z_][\w\.]*"),
                _fmt(PALETTE.syn_decorator, italic=True),
            ))
            # f-string prefixes etc
            self._rules.append((
                QRegularExpression(r"\b(?:[rRbBuUfF]{1,2})(?=['\"])"),
                _fmt(PALETTE.syn_keyword2),
            ))

        # Single-line strings (handle escapes simply)
        for q in spec.string_quotes:
            self._rules.append((
                QRegularExpression(rf"{re.escape(q)}(?:\\.|[^{re.escape(q)}\\])*{re.escape(q)}"),
                _fmt(PALETTE.syn_string),
            ))

        # Line comment
        if spec.line_comment:
            self._rules.append((
                QRegularExpression(rf"{re.escape(spec.line_comment)}[^\n]*"),
                _fmt(PALETTE.syn_comment, italic=True),
            ))

        # Multi-line: triple strings
        for delim in spec.triple_strings:
            esc = re.escape(delim)
            self._multiline.append(MultilineRule(
                start=QRegularExpression(esc),
                end=QRegularExpression(esc),
                fmt=_fmt(PALETTE.syn_string),
                state_id=hash(delim) & 0xFFFF,
            ))

        # Block comment
        if spec.block_comment:
            s, e = spec.block_comment
            self._multiline.append(MultilineRule(
                start=QRegularExpression(re.escape(s)),
                end=QRegularExpression(re.escape(e)),
                fmt=_fmt(PALETTE.syn_comment, italic=True),
                state_id=0xC0DE,
            ))

    def _build_css(self) -> None:
        # selectors
        self._rules.append((
            QRegularExpression(r"^[^\{\}\n]+(?=\{)"),
            _fmt(PALETTE.syn_function),
        ))
        # property names
        self._rules.append((
            QRegularExpression(r"\b([a-zA-Z\-]+)(?=\s*:)"),
            _fmt(PALETTE.syn_attribute),
        ))
        # values: numbers + units
        self._rules.append((
            QRegularExpression(r"\b\d+\.?\d*(px|rem|em|%|vh|vw|s|ms|deg|fr)?\b"),
            _fmt(PALETTE.syn_number),
        ))
        # colors
        self._rules.append((
            QRegularExpression(r"#[0-9a-fA-F]{3,8}\b"),
            _fmt(PALETTE.syn_constant),
        ))
        # strings
        self._rules.append((
            QRegularExpression(r'"(?:\\.|[^"\\])*"'),
            _fmt(PALETTE.syn_string),
        ))
        self._rules.append((
            QRegularExpression(r"'(?:\\.|[^'\\])*'"),
            _fmt(PALETTE.syn_string),
        ))
        # @rules
        self._rules.append((
            QRegularExpression(r"@[A-Za-z\-]+"),
            _fmt(PALETTE.syn_keyword, bold=True),
        ))
        self._rules.append((
            QRegularExpression(r"[\{\};,\(\)]"),
            _fmt(PALETTE.syn_punct),
        ))
        self._multiline.append(MultilineRule(
            start=QRegularExpression(re.escape("/*")),
            end=QRegularExpression(re.escape("*/")),
            fmt=_fmt(PALETTE.syn_comment, italic=True),
            state_id=0xC0DE,
        ))

    def _build_html(self) -> None:
        # Attributes name=
        self._rules.append((
            QRegularExpression(r"\b([A-Za-z_:][A-Za-z0-9_\-:.]*)(?=\s*=)"),
            _fmt(PALETTE.syn_attribute),
        ))
        # Tag names
        self._rules.append((
            QRegularExpression(r"</?([A-Za-z][A-Za-z0-9\-]*)"),
            _fmt(PALETTE.syn_tag, bold=True),
        ))
        # Strings
        self._rules.append((
            QRegularExpression(r'"(?:\\.|[^"\\])*"'),
            _fmt(PALETTE.syn_string),
        ))
        self._rules.append((
            QRegularExpression(r"'(?:\\.|[^'\\])*'"),
            _fmt(PALETTE.syn_string),
        ))
        # Entities
        self._rules.append((
            QRegularExpression(r"&[A-Za-z#0-9]+;"),
            _fmt(PALETTE.syn_constant),
        ))
        # < > /
        self._rules.append((
            QRegularExpression(r"[<>/=]"),
            _fmt(PALETTE.syn_punct),
        ))
        # Comments
        self._multiline.append(MultilineRule(
            start=QRegularExpression(re.escape("<!--")),
            end=QRegularExpression(re.escape("-->")),
            fmt=_fmt(PALETTE.syn_comment, italic=True),
            state_id=0xC0DE,
        ))

    def _build_markdown(self) -> None:
        self._rules.append((
            QRegularExpression(r"^#{1,6}\s.*$"),
            _fmt(PALETTE.syn_heading, bold=True),
        ))
        self._rules.append((
            QRegularExpression(r"\*\*[^*]+\*\*|__[^_]+__"),
            _fmt(PALETTE.text, bold=True),
        ))
        self._rules.append((
            QRegularExpression(r"\*[^*]+\*|_[^_]+_"),
            _fmt(PALETTE.text, italic=True),
        ))
        self._rules.append((
            QRegularExpression(r"`[^`]+`"),
            _fmt(PALETTE.syn_string),
        ))
        self._rules.append((
            QRegularExpression(r"\[[^\]]+\]\([^\)]+\)"),
            _fmt(PALETTE.syn_link),
        ))
        self._rules.append((
            QRegularExpression(r"^\s*[-*+]\s"),
            _fmt(PALETTE.syn_keyword, bold=True),
        ))
        self._rules.append((
            QRegularExpression(r"^\s*\d+\.\s"),
            _fmt(PALETTE.syn_number),
        ))
        self._rules.append((
            QRegularExpression(r"^>\s.*$"),
            _fmt(PALETTE.syn_comment, italic=True),
        ))
        self._multiline.append(MultilineRule(
            start=QRegularExpression(r"^```.*$"),
            end=QRegularExpression(r"^```\s*$"),
            fmt=_fmt(PALETTE.syn_string),
            state_id=0xC0DE,
        ))

    def _build_yaml(self) -> None:
        self._rules.append((
            QRegularExpression(r"^\s*([A-Za-z_][\w\-]*)(?=\s*:)"),
            _fmt(PALETTE.syn_attribute),
        ))
        self._rules.append((
            QRegularExpression(r"\b\d+\.?\d*\b"),
            _fmt(PALETTE.syn_number),
        ))
        self._rules.append((
            QRegularExpression(r"\b(?:true|false|null|yes|no|on|off)\b"),
            _fmt(PALETTE.syn_constant, bold=True),
        ))
        self._rules.append((
            QRegularExpression(r'"(?:\\.|[^"\\])*"'),
            _fmt(PALETTE.syn_string),
        ))
        self._rules.append((
            QRegularExpression(r"'(?:\\.|[^'\\])*'"),
            _fmt(PALETTE.syn_string),
        ))
        self._rules.append((
            QRegularExpression(r"#[^\n]*"),
            _fmt(PALETTE.syn_comment, italic=True),
        ))

    def _build_toml(self) -> None:
        self._rules.append((
            QRegularExpression(r"^\s*\[.*\]\s*$"),
            _fmt(PALETTE.syn_class, bold=True),
        ))
        self._rules.append((
            QRegularExpression(r"^\s*([A-Za-z_][\w\-]*)(?=\s*=)"),
            _fmt(PALETTE.syn_attribute),
        ))
        self._rules.append((
            QRegularExpression(r"\b\d+\.?\d*\b"),
            _fmt(PALETTE.syn_number),
        ))
        self._rules.append((
            QRegularExpression(r"\b(?:true|false)\b"),
            _fmt(PALETTE.syn_constant, bold=True),
        ))
        self._rules.append((
            QRegularExpression(r'"(?:\\.|[^"\\])*"'),
            _fmt(PALETTE.syn_string),
        ))
        self._rules.append((
            QRegularExpression(r"#[^\n]*"),
            _fmt(PALETTE.syn_comment, italic=True),
        ))

    def _build_ini(self) -> None:
        self._build_toml()

    # -- Highlighting --

    # PyCharm-style TODO/FIXME/HACK/NOTE/XXX badges. Painted as a
    # post-pass after the language's regular comment colour so the
    # marker keyword + the rest of the comment both still read as a
    # comment, but the marker pops in a saturated warning hue.
    _TODO_RE = QRegularExpression(
        r"\b(TODO|FIXME|XXX|HACK|NOTE)\b[^\n]*",
        QRegularExpression.PatternOption.NoPatternOption,
    )

    def _todo_format(self, marker: str) -> QTextCharFormat:
        fmt = QTextCharFormat()
        # Same warning amber that PyCharm uses for TODO; a softer cool
        # hue for NOTE / FIXME so the wall doesn't shout.
        if marker == "FIXME" or marker == "XXX":
            fmt.setForeground(QColor(PALETTE.error))
        elif marker == "NOTE":
            fmt.setForeground(QColor(PALETTE.syn_link))
        else:
            fmt.setForeground(QColor(PALETTE.syn_number))
        fmt.setFontWeight(QFont.Weight.Bold)
        fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for regex, fmt in self._rules:
            it = regex.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

        # Multi-line
        self.setCurrentBlockState(0)
        for idx, rule in enumerate(self._multiline, start=1):
            in_state = self.previousBlockState() == idx
            start_idx = 0
            if not in_state:
                m = rule.start.match(text)
                start_idx = m.capturedStart() if m.hasMatch() else -1
            while start_idx >= 0:
                end_match = rule.end.match(text, start_idx + (1 if in_state else 1))
                if not in_state:
                    # Skip past the opening token before searching for end
                    open_match = rule.start.match(text, start_idx)
                    open_end = open_match.capturedStart() + open_match.capturedLength()
                    end_match = rule.end.match(text, open_end)
                if end_match.hasMatch():
                    end = end_match.capturedStart() + end_match.capturedLength()
                    length = end - start_idx
                    self.setFormat(start_idx, length, rule.fmt)
                    in_state = False
                    next_m = rule.start.match(text, end)
                    start_idx = next_m.capturedStart() if next_m.hasMatch() else -1
                else:
                    self.setCurrentBlockState(idx)
                    self.setFormat(start_idx, len(text) - start_idx, rule.fmt)
                    start_idx = -1

        # TODO / FIXME / HACK / NOTE / XXX overlay — applied last so it
        # always wins regardless of which comment style the language uses.
        it = self._TODO_RE.globalMatch(text)
        while it.hasNext():
            m = it.next()
            marker = m.captured(1)
            self.setFormat(
                m.capturedStart(), m.capturedLength(), self._todo_format(marker)
            )
