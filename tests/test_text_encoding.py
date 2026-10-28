import ast
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODE = re.compile(r"[rwxat+]+\Z")


def text_io_without_encoding(path):
    """Sorted (line, call) for text file I/O that falls back to the locale encoding."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), str(path))):
        if not isinstance(node, ast.Call) or any(keyword.arg == "encoding" for keyword in node.keywords):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name in ("read_text", "write_text"):
            found.append((node.lineno, name))
        elif name == "open":
            # Builtin open(path, mode) or Path.open(mode); other .open(...) calls take paths or names.
            args = node.args[1:] if isinstance(func, ast.Name) else node.args
            mode = next((keyword.value for keyword in node.keywords if keyword.arg == "mode"), args[0] if args else None)
            if mode is None:
                if isinstance(func, ast.Name) or not node.args:
                    found.append((node.lineno, name))
            elif isinstance(mode, ast.Constant) and isinstance(mode.value, str) and MODE.match(mode.value) and "b" not in mode.value:
                found.append((node.lineno, name))
    return sorted(found)


class TextEncodingTests(unittest.TestCase):
    def test_text_files_name_their_encoding(self):
        # Korean Windows uses cp949 when encoding is omitted, so UTF-8 JSON with Korean text fails there.
        found = [f"{path.relative_to(ROOT)}:{line} {name}"
                 for folder in ("scripts", "tests") for path in sorted((ROOT / folder).rglob("*.py"))
                 for line, name in text_io_without_encoding(path)]
        self.assertEqual(found, [])

    def test_detector_flags_text_calls_only(self):
        with tempfile.TemporaryDirectory() as temp:
            sample = Path(temp) / "sample.py"
            sample.write_text('p.read_text()\np.write_text("x", encoding="utf-8")\nopen(f)\nopen(f, "rb")\n'
                              'p.open("a")\nImage.open(f)\np.open()\nopen(f, mode="w")\n', encoding="utf-8")
            self.assertEqual([line for line, _ in text_io_without_encoding(sample)], [1, 3, 5, 7, 8])


if __name__ == "__main__":
    unittest.main()
