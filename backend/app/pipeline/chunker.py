"""
tree-sitter tabanlı kod chunk'layıcı — çok dilli.
Her fonksiyon ve sınıf ayrı bir chunk olur.

Desteklenen diller: Python, JavaScript, TypeScript, Java, Go, Rust,
C, C++, C#, Ruby, PHP.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

ChunkType = Literal["function", "class", "module"]

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "dist",
    "build", ".next", "coverage", ".pytest_cache", "vendor", "target",
    "bin", "obj", ".gradle", ".idea", ".vs", "out", "Pods",
}
IGNORE_EXTENSIONS = {
    ".min.js", ".map", ".lock", ".png", ".jpg", ".jpeg", ".gif",
    ".svg", ".ico", ".pdf", ".zip", ".tar", ".gz", ".woff", ".woff2",
    ".ttf", ".eot", ".mp3", ".mp4", ".webm", ".webp",
}

LANG_EXTENSIONS: dict[str, str] = {
    # Python
    ".py": "python",
    # JS/TS
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    # Java / JVM
    ".java": "java",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # C / C++
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
    # C#
    ".cs": "csharp",
    # Ruby
    ".rb": "ruby",
    # PHP
    ".php": "php",
}


@dataclass
class CodeChunk:
    file_path: str
    start_line: int
    end_line: int
    chunk_type: ChunkType
    name: str
    language: str
    code: str


# Lazy parser cache: language -> (Language, Parser)
_PARSER_CACHE: dict = {}


def _get_parser(lang: str):
    """Dil için parser döndür — yoksa None (paket yüklü değil/desteklenmez)."""
    if lang in _PARSER_CACHE:
        return _PARSER_CACHE[lang]

    from tree_sitter import Language, Parser
    try:
        if lang == "python":
            import tree_sitter_python as m
            language = Language(m.language())
        elif lang == "javascript":
            import tree_sitter_javascript as m
            language = Language(m.language())
        elif lang == "typescript":
            import tree_sitter_typescript as m
            language = Language(m.language_typescript())
        elif lang == "java":
            import tree_sitter_java as m
            language = Language(m.language())
        elif lang == "go":
            import tree_sitter_go as m
            language = Language(m.language())
        elif lang == "rust":
            import tree_sitter_rust as m
            language = Language(m.language())
        elif lang == "c":
            import tree_sitter_c as m
            language = Language(m.language())
        elif lang == "cpp":
            import tree_sitter_cpp as m
            language = Language(m.language())
        elif lang == "csharp":
            import tree_sitter_c_sharp as m
            language = Language(m.language())
        elif lang == "ruby":
            import tree_sitter_ruby as m
            language = Language(m.language())
        elif lang == "php":
            import tree_sitter_php as m
            # PHP paketi sadece language_php / language_php_only sağlıyor
            language = Language(m.language_php_only())
        else:
            _PARSER_CACHE[lang] = None
            return None
        parser = Parser(language)
        _PARSER_CACHE[lang] = parser
        return parser
    except Exception as e:
        logger.warning(f"tree-sitter parser '{lang}' yüklenemedi: {e}")
        _PARSER_CACHE[lang] = None
        return None


# Dil bazlı function/class node tipleri
FUNCTION_TYPES = {
    "function_definition",        # Python, C, C++, PHP
    "function_declaration",       # JS, TS, Go
    "method_definition",          # JS/TS class method
    "method_declaration",         # Java, C#, PHP
    "constructor_declaration",    # Java, C#
    "function_item",              # Rust
    "method",                     # Ruby
    "singleton_method",           # Ruby
    "arrow_function",             # JS/TS
}

CLASS_TYPES = {
    "class_definition",           # Python, PHP
    "class_declaration",          # JS, TS, Java, C#
    "interface_declaration",      # Java, TS, C#
    "struct_item",                # Rust
    "enum_item",                  # Rust
    "impl_item",                  # Rust
    "trait_item",                 # Rust
    "type_declaration",           # Go (struct/interface tipler)
    "struct_specifier",           # C/C++
    "class_specifier",            # C++
    "namespace_definition",       # PHP, C++ kısmen
    "class",                      # Ruby
    "module",                     # Ruby
}


def chunk_repo(repo_path: str, max_file_kb: int = 200) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    root = Path(repo_path)

    for fpath in root.rglob("*"):
        if not fpath.is_file():
            continue
        if any(part in IGNORE_DIRS for part in fpath.parts):
            continue
        if fpath.suffix.lower() in IGNORE_EXTENSIONS:
            continue
        lang = LANG_EXTENSIONS.get(fpath.suffix.lower())
        if not lang:
            continue
        if fpath.stat().st_size > max_file_kb * 1024:
            logger.debug(f"Skipping large file: {fpath}")
            continue
        try:
            file_chunks = _chunk_file(fpath, lang, str(fpath.relative_to(root)))
            chunks.extend(file_chunks)
        except Exception as e:
            logger.warning(f"Failed to chunk {fpath}: {e}")

    return chunks


def _chunk_file(fpath: Path, lang: str, rel_path: str) -> list[CodeChunk]:
    source = fpath.read_text(encoding="utf-8", errors="replace")

    parser = _get_parser(lang)
    if parser is None:
        # Parser yoksa: tüm dosyayı tek modül chunk olarak ekle
        return [
            CodeChunk(
                file_path=rel_path,
                start_line=1,
                end_line=source.count("\n") + 1,
                chunk_type="module",
                name=fpath.stem,
                language=lang,
                code=source[:4000],
            )
        ]

    try:
        tree = parser.parse(source.encode())
    except Exception:
        return [
            CodeChunk(
                file_path=rel_path,
                start_line=1,
                end_line=source.count("\n") + 1,
                chunk_type="module",
                name=fpath.stem,
                language=lang,
                code=source[:4000],
            )
        ]

    lines = source.splitlines()
    chunks: list[CodeChunk] = []
    _walk(tree.root_node, lines, rel_path, lang, chunks)
    return chunks or [
        CodeChunk(
            file_path=rel_path,
            start_line=1,
            end_line=len(lines),
            chunk_type="module",
            name=Path(rel_path).stem,
            language=lang,
            code=source[:4000],
        )
    ]


def _walk(node, lines: list[str], rel_path: str, lang: str, chunks: list[CodeChunk]):
    if node.type in FUNCTION_TYPES or node.type in CLASS_TYPES:
        chunk_type: ChunkType = "class" if node.type in CLASS_TYPES else "function"
        name = _extract_name(node, lines)
        start = node.start_point[0] + 1
        end = node.end_point[0] + 1
        code = "\n".join(lines[start - 1 : end])[:4000]
        chunks.append(
            CodeChunk(
                file_path=rel_path,
                start_line=start,
                end_line=end,
                chunk_type=chunk_type,
                name=name,
                language=lang,
                code=code,
            )
        )
        # Sınıfların içindeki metodları da yakala
        if chunk_type == "class":
            for child in node.children:
                _walk(child, lines, rel_path, lang, chunks)
        return

    for child in node.children:
        _walk(child, lines, rel_path, lang, chunks)


def _extract_name(node, lines: list[str]) -> str:
    # Önce field_name "name" ile dene (tree-sitter çoğunlukla destekler)
    try:
        named = node.child_by_field_name("name")
        if named is not None:
            txt = lines[named.start_point[0]][named.start_point[1] : named.end_point[1]]
            if txt.strip():
                return txt
    except Exception:
        pass
    # Düz identifier child'ı dene
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "constant", "name"):
            return lines[child.start_point[0]][child.start_point[1] : child.end_point[1]]
    return "anonymous"
