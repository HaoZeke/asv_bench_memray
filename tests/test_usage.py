"""Discovery contract for ray_* benchmarks.

asv_runner builds the user's class with no arguments, then wraps each
matching method as RayMemBenchmark(name, func, attr_sources).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SUITE = "benchsuite_memray_usage"


def _write_suite(root: Path, source: str) -> None:
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")
    (root / "bench.py").write_text(source, encoding="utf-8")


def _discover(root: Path):
    from asv_runner._aux import update_sys_path
    from asv_runner.discovery import disc_benchmarks

    for key in list(sys.modules):
        if key == SUITE or key.startswith(SUITE + "."):
            del sys.modules[key]
    # Importing the plugin module before asv_runner.benchmarks finishes its
    # scan can miss export_as_benchmark. Put the class on the list explicitly.
    from asv_runner.benchmarks import benchmark_types

    from asv_bench_memray.benchmarks.raymem import RayMemBenchmark

    if RayMemBenchmark not in benchmark_types:
        benchmark_types.append(RayMemBenchmark)
    meta = list(sys.meta_path)
    update_sys_path(str(root))
    try:
        return list(disc_benchmarks(str(root)))
    finally:
        sys.meta_path[:] = meta


def test_plain_class_is_wrapped(tmp_path):
    root = tmp_path / SUITE
    _write_suite(
        root,
        "class MyBenchmark:\n"
        "    def ray_sum(self):\n"
        "        return bytearray(16384)\n",
    )
    found = _discover(root)
    bench = next(b for b in found if b.name.endswith("MyBenchmark.ray_sum"))
    assert type(bench).__name__ == "RayMemBenchmark"
    peak = bench.run()
    assert isinstance(peak, int)
    assert peak > 0


def test_subclass_still_missing_constructor_args(tmp_path):
    root = tmp_path / SUITE
    _write_suite(
        root,
        "from asv_bench_memray.benchmarks.raymem import RayMemBenchmark\n"
        "class MyBenchmark(RayMemBenchmark):\n"
        "    name = 'n'\n"
        "    func = None\n"
        "    attr_sources = []\n"
        "    def ray_sum(self):\n"
        "        return bytearray(8)\n",
    )
    with pytest.raises(TypeError, match="name.*func.*attr_sources"):
        _discover(root)
