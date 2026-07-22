# SPDX-License-Identifier: MIT
# Copyright (c) 2023--present Rohit Goswami <rgoswami[at]ieee[dot]org>
# For full license text, see LICENSE file in the root directory of this source tree
# or visit https://opensource.org/licenses/MIT
"""ASV benchmark type: peak memory via memray.

::

    def ray_sum(self, n):
        ...

    ray_sum.ray_save_profile = True  # write memray flamegraph HTML

Profile HTML lands under ``.asv/profiles/memray/`` (override with
``ASV_BENCH_MEMRAY_PROFILE_DIR``). Publish into asv-tachyon with::

    python -m asv_bench_memray profiles publish --html-dir .asv/html
"""

from __future__ import annotations

import os
import re
import tempfile
import uuid
from pathlib import Path

from asv_runner.benchmarks._base import Benchmark, _get_first_attr
from asv_runner.benchmarks._exceptions import NotRequired

try:
    import memray
    from memray import FileReader
except ImportError:
    raise NotRequired("RayMemBenchmark not requested or memray not found")


def _truthy(val) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _want_profile(attr_sources) -> bool:
    if _truthy(os.environ.get("ASV_BENCH_MEMRAY_PROFILE")):
        return True
    if os.environ.get("ASV_BENCH_MEMRAY_PROFILE_DIR"):
        return True
    return _truthy(_get_first_attr(attr_sources, "ray_save_profile", False))


class RayMemBenchmark(Benchmark):
    """Peak allocated memory (bytes) measured by memray."""

    name_regex = re.compile("^(Ray[A-Z_].+)|(ray_.+)$")

    def __init__(self, name, func, attr_sources):
        Benchmark.__init__(self, name, func, attr_sources)
        self.type = "memory"
        self.unit = "bytes"
        self.ray_save_profile = _want_profile(attr_sources)

    def run(self, *param):
        u_id = uuid.uuid4()
        temp_dir = tempfile.gettempdir()
        tfile_loc = Path(f"{temp_dir}/{u_id}.bin")
        with memray.Tracker(
            destination=memray.FileDestination(tfile_loc, overwrite=True)
        ):
            self.func(*param)
        freader = FileReader(str(tfile_loc))
        peak = freader.metadata.peak_memory

        if self.ray_save_profile:
            self._save_html_report(tfile_loc)

        try:
            tfile_loc.unlink(missing_ok=True)
        except OSError:
            pass
        return peak

    def _save_html_report(self, bin_path: Path) -> None:
        from asv_bench_memray.profiles import (
            default_profile_dir,
            profile_path_for,
            register_profile,
        )

        profile_dir = default_profile_dir()
        out = profile_path_for(self.name, profile_dir)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Prefer flamegraph reporter when available; fall back to table.
        try:
            from memray.reporters.flamegraph import FlameGraphReporter

            reader = FileReader(str(bin_path))
            records = reader.get_high_watermark_allocation_records(merge_threads=True)
            reporter = FlameGraphReporter.from_snapshot(
                records,
                memory_records=tuple(reader.get_memory_snapshots()),
                native_traces=reader.metadata.has_native_traces,
            )
            with out.open("w", encoding="utf-8") as fh:
                reporter.render(
                    outfile=fh,
                    metadata=reader.metadata,
                    show_memory_leaks=False,
                    merge_threads=True,
                    inverted=False,
                )
        except Exception:
            # Minimal fallback so the profiles.json link is never empty.
            reader = FileReader(str(bin_path))
            peak = reader.metadata.peak_memory
            out.write_text(
                (
                    "<!doctype html><html><head><meta charset='utf-8'>"
                    f"<title>memray {self.name}</title></head><body>"
                    f"<h1>memray peak for {self.name}</h1>"
                    f"<p>Peak memory: {peak} bytes</p>"
                    "<p>Install a full memray flamegraph export path if this "
                    "stub appears (FlameGraphReporter failed).</p>"
                    "</body></html>\n"
                ),
                encoding="utf-8",
            )

        if out.is_file():
            register_profile(self.name, out, profile_dir=profile_dir)


export_as_benchmark = [RayMemBenchmark]
