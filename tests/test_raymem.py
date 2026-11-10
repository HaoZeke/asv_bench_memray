from __future__ import annotations

from pathlib import Path

import pytest

from asv_bench_memray.benchmarks import raymem
from asv_bench_memray.benchmarks.raymem import RayMemBenchmark


def _bench(func, sources=None):
    if sources is None:
        sources = [func]
    return RayMemBenchmark("suite.alloc", func, sources)


def test_readme_and_docs_name_the_project():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    index = (root / "doc" / "source" / "index.rst").read_text(encoding="utf-8")
    assert "asv_plugin_memray" not in readme
    assert "asv_plugin_memray" not in index
    assert "asv_bench_memray" in readme
    assert "asv_bench_memray" in index


def test_single_repeat_returns_peak_int():
    def alloc():
        return bytearray(8192)

    peak = _bench(alloc).run()
    assert isinstance(peak, int)
    assert peak > 0


def test_repeat_returns_one_sample_per_capture():
    calls = {"n": 0}

    def alloc():
        calls["n"] += 1
        return bytearray(16384)

    alloc.repeat = 4
    result = _bench(alloc).run()
    assert calls["n"] == 4
    assert result["number"] == 1
    assert len(result["samples"]) == 4
    assert all(isinstance(sample, int) and sample > 0 for sample in result["samples"])


def test_repeat_triple_stops_at_max_time():
    calls = {"n": 0}

    def alloc():
        calls["n"] += 1
        return bytearray(32)

    alloc.repeat = (2, 10, 0.0)
    result = _bench(alloc).run()
    assert calls["n"] == 2
    assert len(result["samples"]) == 2


def test_repeat_zero_is_one_sample():
    calls = {"n": 0}

    def alloc():
        calls["n"] += 1
        return bytearray(16)

    alloc.repeat = 0
    peak = _bench(alloc).run()
    assert calls["n"] == 1
    assert isinstance(peak, int)


def test_invalid_repeat():
    def alloc():
        return bytearray(8)

    alloc.repeat = -1
    with pytest.raises(ValueError, match="repeat"):
        _bench(alloc).run()


def test_warmup_runs_outside_the_tracker(monkeypatch):
    calls = {"n": 0, "tracked": 0}
    real = raymem.memray.Tracker

    def tracker(*args, **kwargs):
        calls["tracked"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(raymem.memray, "Tracker", tracker)

    def alloc():
        calls["n"] += 1
        return bytearray(64)

    alloc.warmup_time = 0.05
    alloc.repeat = 2
    result = _bench(alloc).run()
    assert calls["tracked"] == 2
    assert calls["n"] > calls["tracked"]
    assert len(result["samples"]) == 2


def test_quick_params_override_repeat_and_warmup():
    calls = {"n": 0}

    def alloc():
        calls["n"] += 1
        return bytearray(32)

    alloc.repeat = 5
    alloc.warmup_time = 0.2

    class Quick:
        repeat = 1
        warmup_time = 0

    bench = _bench(alloc, [Quick, alloc])
    peak = bench.run()
    assert calls["n"] == 1
    assert isinstance(peak, int)


def test_default_tracker_leaves_allocator_tracing_off(monkeypatch):
    seen = {}
    real = raymem.memray.Tracker

    def tracker(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(raymem.memray, "Tracker", tracker)

    def alloc():
        return bytearray(64)

    assert isinstance(_bench(alloc).run(), int)
    assert seen["trace_python_allocators"] is False
    assert seen["native_traces"] is False


def test_capture_records_allocator_and_native_flags(monkeypatch):
    seen = {}
    real_reader = raymem.FileReader

    class Recording:
        def __init__(self, path):
            self._inner = real_reader(path)
            meta = self._inner.metadata
            seen["trace"] = meta.trace_python_allocators
            seen["native"] = meta.has_native_traces
            seen["peak"] = meta.peak_memory

        def __getattr__(self, name):
            return getattr(self._inner, name)

    monkeypatch.setattr(raymem, "FileReader", Recording)

    def alloc():
        return bytearray(65536)

    alloc.ray_trace_python_allocators = True
    alloc.ray_native_traces = True
    peak = _bench(alloc).run()
    assert peak == seen["peak"]
    assert peak > 0
    assert seen["trace"] is True
    assert seen["native"] is True


def test_env_enables_allocator_tracing(monkeypatch):
    seen = {}
    real = raymem.memray.Tracker

    def tracker(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(raymem.memray, "Tracker", tracker)
    monkeypatch.setenv("ASV_BENCH_MEMRAY_TRACE_PYTHON_ALLOCATORS", "1")
    monkeypatch.setenv("ASV_BENCH_MEMRAY_NATIVE_TRACES", "yes")

    def alloc():
        return bytearray(32)

    alloc.ray_trace_python_allocators = False
    alloc.ray_native_traces = False
    _bench(alloc).run()
    assert seen["trace_python_allocators"] is True
    assert seen["native_traces"] is True


def test_larger_allocation_has_a_larger_peak():
    def alloc_small():
        return bytearray(16384)

    def alloc_large():
        return bytearray(4_000_000)

    small = _bench(alloc_small).run()
    large = _bench(alloc_large).run()
    assert large > small


def test_default_capture_format_is_all_allocations():
    import memray

    assert raymem.capture_format("all") is memray.FileFormat.ALL_ALLOCATIONS
    assert raymem.capture_format(None) is memray.FileFormat.ALL_ALLOCATIONS
    assert (
        raymem.capture_format("aggregated")
        is memray.FileFormat.AGGREGATED_ALLOCATIONS
    )

    def alloc():
        return None

    assert _bench(alloc).ray_file_format == "all"


def test_run_passes_file_format_explicitly(monkeypatch):
    import memray

    seen = {}
    real = memray.Tracker

    def factory(*args, **kwargs):
        seen["file_format"] = kwargs.get("file_format")
        return real(*args, **kwargs)

    monkeypatch.setattr(raymem.memray, "Tracker", factory)

    def alloc():
        return bytearray(64)

    alloc.ray_file_format = "aggregated"
    alloc.ray_save_profile = False
    alloc.warmup_time = 0
    alloc.repeat = 1
    _bench(alloc).run()
    assert seen["file_format"] is memray.FileFormat.AGGREGATED_ALLOCATIONS


def test_import_error_writes_stub(tmp_path, monkeypatch):
    import memray

    bin_path = tmp_path / "cap.bin"
    with memray.Tracker(bin_path):
        bytearray(32)
    monkeypatch.setenv("ASV_BENCH_MEMRAY_PROFILE_DIR", str(tmp_path / "profiles"))

    def missing(*_args, **_kwargs):
        raise ImportError("no flamegraph")

    monkeypatch.setattr(raymem, "_write_flamegraph", missing)

    def alloc():
        return None

    bench = _bench(alloc)
    bench._save_html_report(bin_path, ())
    html = list(Path(tmp_path / "profiles").glob("*.html"))
    assert len(html) == 1
    text = html[0].read_text(encoding="utf-8")
    assert "ImportError" in text
    assert "no flamegraph" in text


def test_other_report_errors_propagate(tmp_path, monkeypatch):
    import memray

    bin_path = tmp_path / "cap.bin"
    with memray.Tracker(bin_path):
        bytearray(32)
    monkeypatch.setenv("ASV_BENCH_MEMRAY_PROFILE_DIR", str(tmp_path / "profiles"))

    def broken(*_args, **_kwargs):
        raise RuntimeError("reporter broke")

    monkeypatch.setattr(raymem, "_write_flamegraph", broken)

    def alloc():
        return None

    bench = _bench(alloc)
    with pytest.raises(RuntimeError, match="reporter broke"):
        bench._save_html_report(bin_path, ())
    assert list(Path(tmp_path / "profiles").glob("*.html")) == []


def test_render_error_removes_partial_html(tmp_path, monkeypatch):
    import memray
    from memray.reporters import flamegraph

    bin_path = tmp_path / "cap.bin"
    with memray.Tracker(bin_path):
        bytearray(32)
    monkeypatch.setenv("ASV_BENCH_MEMRAY_PROFILE_DIR", str(tmp_path / "profiles"))

    class Reporter:
        @classmethod
        def from_snapshot(cls, *args, **kwargs):
            return cls()

        def render(self, **kwargs):
            raise RuntimeError("render broke")

    monkeypatch.setattr(flamegraph, "FlameGraphReporter", Reporter)

    def alloc():
        return None

    bench = _bench(alloc)
    with pytest.raises(RuntimeError, match="render broke"):
        bench._save_html_report(bin_path, ())
    assert list(Path(tmp_path / "profiles").glob("*.html")) == []
