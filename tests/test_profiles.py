from __future__ import annotations

import json
from pathlib import Path

from asv_bench_memray.profiles import profile_key, publish, register_profile


def test_publish_merge(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "profiles" / "memray"
    html = src / "bench.ray_sum.html"
    html.parent.mkdir(parents=True)
    html.write_text("<html>mem</html>", encoding="utf-8")
    register_profile("bench.ray_sum", html, profile_dir=src)

    site = tmp_path / "html"
    site.mkdir()
    (site / "profiles.json").write_text(
        json.dumps({"paths": {"bench.sample_hot": "profiles/tachyon/x.html"}}),
        encoding="utf-8",
    )
    paths = publish(site, from_dir=src, merge=True)
    assert paths["bench.ray_sum"].startswith("profiles/memray/")
    assert paths["bench.sample_hot"] == "profiles/tachyon/x.html"
    assert profile_key("a", 1) == "a@1"
