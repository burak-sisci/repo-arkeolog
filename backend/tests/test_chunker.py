"""Chunker birim testleri."""
import tempfile
import os
import pytest
from app.pipeline.chunker import chunk_repo, CodeChunk


def _write_file(tmp_dir, rel_path, content):
    full = os.path.join(tmp_dir, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)


def test_python_function_chunking():
    with tempfile.TemporaryDirectory() as tmp:
        _write_file(tmp, "src/foo.py", "def foo():\n    pass\n\ndef bar():\n    pass\n")
        chunks = chunk_repo(tmp)
        names = [c.name for c in chunks]
        assert "foo" in names
        assert "bar" in names


def test_python_class_chunking():
    with tempfile.TemporaryDirectory() as tmp:
        _write_file(tmp, "src/models.py", "class User:\n    def __init__(self):\n        pass\n")
        chunks = chunk_repo(tmp)
        types = [c.chunk_type for c in chunks]
        assert "class" in types


def test_ignores_node_modules():
    with tempfile.TemporaryDirectory() as tmp:
        _write_file(tmp, "node_modules/lib/index.js", "function secret() {}")
        _write_file(tmp, "src/app.js", "function main() {}")
        chunks = chunk_repo(tmp)
        paths = [c.file_path for c in chunks]
        assert not any("node_modules" in p for p in paths)


def test_chunk_has_required_fields():
    with tempfile.TemporaryDirectory() as tmp:
        _write_file(tmp, "src/utils.py", "def helper(x):\n    return x * 2\n")
        chunks = chunk_repo(tmp)
        assert len(chunks) > 0
        c = chunks[0]
        assert c.file_path
        assert c.language in ("python", "javascript", "typescript")
        assert c.start_line >= 1
        assert c.end_line >= c.start_line
        assert c.code
