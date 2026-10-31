# SPDX-License-Identifier: MIT
# Copyright (c) 2023--present Rohit Goswami <rgoswami[at]ieee[dot]org>
# For full license text, see LICENSE file in the root directory of this source tree
# or visit https://opensource.org/licenses/MIT
"""ASV benchmark type: peak memory via memray.

::

    def ray_sum(self, n):
        ...

    ray_sum.ray_save_profile = True  # write memray flamegraph HTML
    ray_sum.ray_trace_python_allocators = True
    ray_sum.ray_native_traces = True
    ray_sum.warmup_time = 0.1  # seconds, outside the tracker
    ray_sum.repeat = 3  # or (min_repeat, max_repeat, max_time)

``warmup_time`` defaults to ``0`` and ``repeat`` defaults to ``1`` (a single
peak, returned as an int). Allocator tracing and native traces default off.
``ASV_BENCH_MEMRAY_TRACE_PYTHON_ALLOCATORS`` and
``ASV_BENCH_MEMRAY_NATIVE_TRACES`` turn those on for every ``ray_*`` benchmark.
Profile HTML lands under ``.asv/profiles/memray/`` (override with
``ASV_BENCH_MEMRAY_PROFILE_DIR``). With ``repeat`` greater than 1, the HTML is
the last sample. Publish into asv-tachyon with::

    python -m asv_bench_memray profiles publish --html-dir .asv/html
"""

from __future__ import annotations

import os
import re
import tempfile
import time
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


def capture_format(name):
    """Memray capture format for a ``ray_file_format`` attribute.

    The Tracker default is ``FileFormat.ALL_ALLOCATIONS`` (every
    allocation). This plugin passes the format explicitly so a change
    of that default does not silently change the measurement. ``all``
    is the plugin default. ``aggregated`` selects
    ``FileFormat.AGGREGATED_ALLOCATIONS``.
    """
    text = str(name if name is not None else "all").strip().lower()
    if text in {"aggregated", "agg", "aggregated_allocations"}:
        return memray.FileFormat.AGGREGATED_ALLOCATIONS
    return memray.FileFormat.ALL_ALLOCATIONS


def _write_flamegraph(bin_path: Path, out: Path) -> None:
    from memray.reporters.flamegraph import FlameGraphReporter

    reader = FileReader(str(bin_path))
    records = reader.get_high_watermark_allocation_records(merge_threads=True)
    reporter = FlameGraphReporter.from_snapshot(
        records,
        memory_records=tuple(reader.get_memory_snapshots()),
        native_traces=reader.metadata.has_native_traces,
    )
    try:
        with out.open("w", encoding="utf-8") as fh:
            reporter.render(
                outfile=fh,
                metadata=reader.metadata,
                show_memory_leaks=False,
                merge_threads=True,
                inverted=False,
            )
    except Exception:
        out.unlink(missing_ok=True)
        raise


def _write_stub(out: Path, name: str, exc: BaseException) -> None:
    detail = f"{type(exc).__name__}: {exc}"
    out.write_text(
        (
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>memray {name}</title></head><body>"
            f"<h1>memray peak for {name}</h1>"
            f"<p>{detail}</p>"
            "<p>The flamegraph reporter could not be imported.</p>"
            "</body></html>\n"
        ),
        encoding="utf-8",
    )


def _want_profile(attr_sources) -> bool:
    if _truthy(os.environ.get("ASV_BENCH_MEMRAY_PROFILE")):
        return True
    if os.environ.get("ASV_BENCH_MEMRAY_PROFILE_DIR"):
        return True
    return _truthy(_get_first_attr(attr_sources, "ray_save_profile", False))


def _flag(attr_sources, name: str, env: str) -> bool:
    if _truthy(os.environ.get(env)):
        return True
    return _truthy(_get_first_attr(attr_sources, name, False))


class RayMemBenchmark(Benchmark):
    """Peak allocated memory (bytes) measured by memray.

    ``warmup_time`` (seconds) runs the benchmark outside the tracker before
    samples are taken. ``repeat`` is an exact sample count, or a
    ``(min_repeat, max_repeat, max_time)`` triple with the same meaning as a
    timing benchmark. ``ray_trace_python_allocators`` and ``ray_native_traces``
    are forwarded to ``memray.Tracker``.
    """

    name_regex = re.compile("^(Ray[A-Z_].+)|(ray_.+)$")

    def __init__(self, name, func, attr_sources):
        Benchmark.__init__(self, name, func, attr_sources)
        self.type = "memory"
        self.unit = "bytes"
        self._load_run_options()

    def _load_run_options(self) -> None:
        sources = self._attr_sources
        self.ray_save_profile = _want_profile(sources)
        self.warmup_time = _get_first_attr(sources, "warmup_time", 0)
        self.repeat = _get_first_attr(sources, "repeat", 1)
        self.ray_trace_python_allocators = _flag(
            sources,
            "ray_trace_python_allocators",
            "ASV_BENCH_MEMRAY_TRACE_PYTHON_ALLOCATORS",
        )
        self.ray_native_traces = _flag(
            sources,
            "ray_native_traces",
            "ASV_BENCH_MEMRAY_NATIVE_TRACES",
        )
        self.ray_file_format = _get_first_attr(sources, "ray_file_format", "all")

    def do_setup(self):
        # setup() may change repeat / warmup; asv --quick injects them too.
        skipped = Benchmark.do_setup(self)
        self._load_run_options()
        return skipped

    def _warmup_seconds(self) -> float:
        try:
            value = float(self.warmup_time)
        except (TypeError, ValueError):
            return 0.0
        if value <= 0:
            return 0.0
        return value

    def _repeat_plan(self):
        repeat = self.repeat
        # 0 matches an unset timing default: one memory sample, not an
        # automatic 1..10 range (each sample is a full capture).
        if not isinstance(repeat, bool) and repeat in (None, 0):
            return 1, 1, None
        try:
            min_repeat, max_repeat, max_time = repeat
        except (TypeError, ValueError):
            try:
                count = int(repeat)
            except (TypeError, ValueError):
                raise ValueError(
                    f"{self.name}: repeat must be an integer >= 1 or a "
                    "(min_repeat, max_repeat, max_time) triple"
                ) from None
            if isinstance(repeat, bool) or count < 1:
                raise ValueError(
                    f"{self.name}: repeat must be an integer >= 1 or a "
                    "(min_repeat, max_repeat, max_time) triple"
                )
            return count, count, None

        min_repeat = int(min_repeat)
        max_repeat = int(max_repeat)
        max_time = float(max_time)
        if min_repeat < 1 or max_repeat < min_repeat:
            raise ValueError(f"{self.name}: invalid repeat triple {repeat!r}")
        return min_repeat, max_repeat, max_time

    def _warmup(self, param) -> None:
        duration = self._warmup_seconds()
        if duration <= 0:
            return
        deadline = time.perf_counter() + duration
        while True:
            self.redo_setup()
            self.func(*param)
            if time.perf_counter() >= deadline:
                return

    def _measure_peak(self, param) -> int:
        tfile_loc = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}.bin"
        try:
            with memray.Tracker(
                destination=memray.FileDestination(tfile_loc, overwrite=True),
                native_traces=self.ray_native_traces,
                trace_python_allocators=self.ray_trace_python_allocators,
                file_format=capture_format(self.ray_file_format),
            ):
                self.func(*param)
            peak = FileReader(str(tfile_loc)).metadata.peak_memory
            if self.ray_save_profile:
                self._save_html_report(tfile_loc, param)
            return int(peak)
        finally:
            try:
                tfile_loc.unlink(missing_ok=True)
            except OSError:
                pass

    def run(self, *param):
        self._load_run_options()
        self._warmup(param)
        min_repeat, max_repeat, max_time = self._repeat_plan()
        samples = []
        started = time.perf_counter()
        while len(samples) < max_repeat:
            self.redo_setup()
            samples.append(self._measure_peak(param))
            if (
                max_time is not None
                and len(samples) >= min_repeat
                and time.perf_counter() - started >= max_time
            ):
                break
        if min_repeat == 1 and max_repeat == 1:
            return samples[0]
        return {"samples": samples, "number": 1}

    def _save_html_report(self, bin_path: Path, param: tuple = ()) -> None:
        from asv_bench_memray.profiles import (
            default_profile_dir,
            profile_path_for,
            register_profile,
        )

        profile_dir = default_profile_dir()
        rev = os.environ.get("ASV_COMMIT") or None
        out = profile_path_for(self.name, profile_dir, rev=rev, params=param)
        out.parent.mkdir(parents=True, exist_ok=True)

        # A missing flamegraph reporter writes a stub. Any other error
        # propagates so a broken report is not saved as a successful page.
        try:
            _write_flamegraph(bin_path, out)
        except ImportError as exc:
            _write_stub(out, self.name, exc)

        if out.is_file():
            register_profile(
                self.name,
                out,
                rev=rev,
                params=param,
                profile_dir=profile_dir,
            )


export_as_benchmark = [RayMemBenchmark]
