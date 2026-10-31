from __future__ import annotations

import json

from asv_bench_memray.profiles import profile_key, publish, register_profile


def test_profiles_are_not_keyed_by_name_alone(tmp_path):
    from asv_bench_memray.profiles import profile_path_for, register_profile

    src = tmp_path / "profiles"
    src.mkdir()
    first = src / "a.html"
    second = src / "b.html"
    first.write_text("<html>one</html>", encoding="utf-8")
    second.write_text("<html>two</html>", encoding="utf-8")

    path_a = register_profile(
        "bench.ray_sum", first, rev="aaa", params=(1,), profile_dir=src
    )
    path_b = register_profile(
        "bench.ray_sum", second, rev="bbb", params=(2,), profile_dir=src
    )
    assert path_a != path_b
    assert path_a.is_file() and path_b.is_file()
    assert path_a.read_text(encoding="utf-8") == "<html>one</html>"
    assert path_b.read_text(encoding="utf-8") == "<html>two</html>"
    assert profile_path_for("bench.ray_sum", src, rev="aaa", params=(1,)) == path_a


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
