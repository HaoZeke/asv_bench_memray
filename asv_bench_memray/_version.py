# SPDX-License-Identifier: MIT
# Copyright (c) 2023--present Rohit Goswami <rgoswami[at]ieee[dot]org>
# For full license text, see LICENSE file in the root directory of this source tree
# or visit https://opensource.org/licenses/MIT
"""Read the one handwritten project version.

That string is ``[project].version`` in ``pyproject.toml``. PEP 621
defines the field:

https://peps.python.org/pep-0621/#version

A checkout reads the file, including an editable install, so a local
edit is visible without reinstalling. A wheel does not ship
``pyproject.toml``. Hatchling copies the static field into distribution
metadata at build time, and :mod:`importlib.metadata` reads it back:

https://hatch.pypa.io/latest/version/#static
https://docs.python.org/3/library/importlib.metadata.html

``tomllib`` is not used. It arrived in Python 3.11, and this project
still declares ``requires-python = ">=3.8"``. The handwritten assignment
is a single-line TOML basic or literal string. Multiline strings and
escapes are rejected so a second encoding cannot hide another copy.
"""

from __future__ import annotations

import re
from pathlib import Path

# Single-line TOML string. Group 2 is the raw value, with no escape
# processing, because the handwritten version does not use escapes.
_VERSION_LINE = re.compile("""^version\\s*=\\s*(['\"])([^'\"]*)\\1\\s*$""")


def _pyproject_path() -> Path:
    """Return ``pyproject.toml`` at the root of this repository.

    The search walks parents of this file. The root is the first
    directory that contains both ``pyproject.toml`` and the
    ``asv_bench_memray`` package directory. The package directory keeps
    the walk from stopping at an unrelated ``pyproject.toml`` above the
    checkout.
    """

    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "asv_bench_memray"
        ).is_dir():
            return candidate / "pyproject.toml"
    raise RuntimeError(f"pyproject.toml not found above {here}")


def _version_in_pyproject(path: Path) -> str:
    """Return the single ``[project].version`` string in ``path``."""

    in_project = False
    found: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("[")
            and stripped.endswith("]")
            and "=" not in stripped
        ):
            # Any other table, including an array table such as
            # [[tool.towncrier.type]], ends the [project] section.
            in_project = stripped == "[project]"
            continue
        if not in_project:
            continue
        match = _VERSION_LINE.match(stripped)
        if match is None:
            continue
        if found is not None:
            raise RuntimeError(f"more than one [project].version in {path}")
        found = match.group(2)
    if found is None:
        raise RuntimeError(f"no [project].version in {path}")
    if found == "":
        # PEP 621 metadata cannot publish an empty version string.
        raise RuntimeError(f"empty [project].version in {path}")
    return found


def _version_from_distribution() -> str:
    """Return the installed distribution version.

    Used when this module is imported from a wheel, which has no
    ``pyproject.toml`` beside the package. The build copies the
    handwritten field into the distribution metadata.
    """

    from importlib.metadata import PackageNotFoundError, version

    try:
        installed = version("asv_bench_memray")
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "project version is not in a checkout pyproject.toml and "
            "asv_bench_memray is not installed"
        ) from exc
    if installed == "":
        raise RuntimeError("installed asv_bench_memray version is empty")
    return installed


def read_project_version(pyproject: Path | None = None) -> str:
    """Return the project version.

    Pass ``pyproject`` to read that file and nothing else. With no
    argument, a checkout file wins over installed metadata.
    """

    if pyproject is not None:
        return _version_in_pyproject(Path(pyproject))
    try:
        path = _pyproject_path()
    except RuntimeError:
        return _version_from_distribution()
    return _version_in_pyproject(path)
