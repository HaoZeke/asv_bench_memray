# SPDX-License-Identifier: MIT
# Copyright (c) 2023--present Rohit Goswami <rgoswami[at]ieee[dot]org>
# For full license text, see LICENSE file in the root directory of this source tree
# or visit https://opensource.org/licenses/MIT
"""The handwritten version matches every derived copy.

Run from the repository root:

    python tests/test_version_consistency.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# This file is tests/test_version_consistency.py. The package lives in the
# repository root, one directory above the script directory Python puts on
# sys.path when the file is executed directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asv_bench_memray import __version__  # noqa: E402
from asv_bench_memray._version import read_project_version  # noqa: E402

# Built without a cog begin marker so this test file is not itself a
# cog input. The marker is what cog searches for.
_COG_BEGIN = "[" * 3 + "cog"


def _tracked_cog_files() -> list[str]:
    """Return repo-relative paths of tracked files that contain a cog block.

    ``git ls-files`` lists the index. An untracked ``venv/`` or ``build/``
    that contains cog sources is not scanned.
    """

    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    found = []
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8")
        path = ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        if _COG_BEGIN in text:
            found.append(relative)
    return sorted(found)


class VersionConsistencyTest(unittest.TestCase):
    def test_checkout_version_matches_runtime(self) -> None:
        handwritten = read_project_version()
        self.assertNotEqual(handwritten, "")
        self.assertEqual(__version__, handwritten)
        self.assertEqual(read_project_version(ROOT / "pyproject.toml"), handwritten)

    def test_tbump_current_matches_handwritten_version(self) -> None:
        handwritten = read_project_version()
        text = (ROOT / "tbump.toml").read_text(encoding="utf-8")
        currents = re.findall(r'^current = "([^"]*)"', text, flags=re.MULTILINE)
        self.assertEqual(currents, [handwritten])

    def test_towncrier_examples_match_handwritten_version(self) -> None:
        handwritten = read_project_version()
        text = (ROOT / "doc/changelog.d/readme.md").read_text(encoding="utf-8")
        versions = re.findall(r"--version\s+([0-9][^\s]*)", text)
        self.assertEqual(versions, [handwritten, handwritten])

    def test_sphinx_release_is_not_a_literal(self) -> None:
        text = (ROOT / "doc/source/conf.py").read_text(encoding="utf-8")
        self.assertIn("read_project_version()", text)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("release"):
                self.assertIsNone(
                    re.match(r"""release\s*=\s*['\"][0-9]""", stripped),
                    stripped,
                )

    def test_pyproject_version_is_static(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertNotIn('dynamic = ["version"]', text)
        self.assertNotIn('source = "vcs"', text)
        self.assertNotIn("hatch-vcs", text)
        assignments = re.findall(
            r'^version = "([^"]*)"',
            text,
            flags=re.MULTILINE,
        )
        self.assertEqual(assignments, [read_project_version()])

    def test_cog_check_passes(self) -> None:
        files = _tracked_cog_files()
        self.assertEqual(
            files,
            ["doc/changelog.d/readme.md", "tbump.toml"],
        )
        workflow = (ROOT / ".github/workflows/version-drift.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("cog --check", workflow)
        for name in files:
            self.assertIn(name, workflow)
        completed = subprocess.run(
            [sys.executable, "-m", "cogapp", "--check", *files],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_reader_uses_project_table_only(self) -> None:
        # These three strings are sample text, not releases. They differ
        # so the assertion fails if the reader returns another table.
        tool_version = "8.7.6"
        project_version = "9.8.7"
        urls_version = "7.6.5"
        sample = "\n".join(
            [
                "[tool.example]",
                f'version = "{tool_version}"',
                "",
                "[project]",
                'name = "sample"',
                f'version = "{project_version}"',
                "",
                "[project.urls]",
                f'version = "{urls_version}"',
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyproject.toml"
            path.write_text(sample, encoding="utf-8")
            self.assertEqual(read_project_version(path), project_version)

    def test_reader_rejects_a_second_project_version(self) -> None:
        # Two different sample strings. The reader must reject the file
        # rather than pick one of them.
        sample = "\n".join(
            [
                "[project]",
                'version = "9.8.7"',
                'version = "8.7.6"',
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyproject.toml"
            path.write_text(sample, encoding="utf-8")
            with self.assertRaises(RuntimeError):
                read_project_version(path)

    def test_reader_rejects_a_missing_version(self) -> None:
        sample = "[project]\nname = \"sample\"\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyproject.toml"
            path.write_text(sample, encoding="utf-8")
            with self.assertRaises(RuntimeError):
                read_project_version(path)


if __name__ == "__main__":
    unittest.main()
