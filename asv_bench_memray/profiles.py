"""Publish memray HTML reports into asv-tachyon ``profiles.json``.

Same sidecar contract as asv_bench_tachyon::

    {
      "paths": {
        "<bench>@<rev>": "profiles/memray/<safe_name>.html",
        "<bench>": "profiles/memray/<safe_name>.html"
      }
    }

During ``asv run``, ray_* benchmarks with profile saving enabled write
HTML under ``.asv/profiles/memray/`` (or ``$ASV_BENCH_MEMRAY_PROFILE_DIR``).
After ``asv publish``::

    python -m asv_bench_memray profiles publish --html-dir .asv/html
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

KIND = "memray"
SUBDIR = "profiles/memray"
REGISTRY_NAME = "registry.json"


def sanitize_name(name: str) -> str:
    return re.sub(r"[^\w.\-]+", "_", name)


def profile_key(bench: str, rev: str | int | None = None) -> str:
    if rev is None or rev == "":
        return bench
    return f"{bench}@{rev}"


def default_profile_dir(results_dir: str | Path | None = None) -> Path:
    env = os.environ.get("ASV_BENCH_MEMRAY_PROFILE_DIR")
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    if results_dir is not None:
        base = Path(results_dir).parent
    else:
        base = Path(".asv")
    out = base / "profiles" / KIND
    out.mkdir(parents=True, exist_ok=True)
    return out


def profile_filename(
    bench: str,
    rev: str | int | None = None,
    params: object = None,
) -> str:
    """File name for one profile.

    The benchmark name alone is not unique across revisions or parameters,
    so those are part of the file name when they are known.
    """
    parts = [sanitize_name(bench)]
    if rev not in (None, ""):
        parts.append(sanitize_name(str(rev)))
    if params not in (None, (), []):
        parts.append(sanitize_name(repr(params)))
    return "_".join(parts) + ".html"


def profile_path_for(
    bench: str,
    profile_dir: Path | None = None,
    rev: str | int | None = None,
    params: object = None,
) -> Path:
    root = profile_dir if profile_dir is not None else default_profile_dir()
    return root / profile_filename(bench, rev, params)


def load_registry(profile_dir: Path) -> dict[str, Any]:
    reg = profile_dir / REGISTRY_NAME
    if not reg.is_file():
        return {"kind": KIND, "entries": []}
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"kind": KIND, "entries": []}
    if not isinstance(data, dict):
        return {"kind": KIND, "entries": []}
    data.setdefault("kind", KIND)
    data.setdefault("entries", [])
    return data


def save_registry(profile_dir: Path, registry: dict[str, Any]) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / REGISTRY_NAME).write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def register_profile(
    bench: str,
    html_path: Path,
    *,
    rev: str | int | None = None,
    params: object = None,
    profile_dir: Path | None = None,
) -> Path:
    root = profile_dir if profile_dir is not None else default_profile_dir()
    root.mkdir(parents=True, exist_ok=True)
    stored_rev = None if rev in (None, "") else rev
    params_repr = None if params in (None, (), []) else repr(params)
    dest = profile_path_for(bench, root, rev=stored_rev, params=params)
    html_path = Path(html_path)
    if html_path.resolve() != dest.resolve():
        shutil.copy2(html_path, dest)

    registry = load_registry(root)
    entries: list[dict[str, Any]] = []
    for entry in registry.get("entries") or []:
        same = (
            entry.get("bench") == bench
            and entry.get("rev", None) == stored_rev
            and entry.get("params", None) == params_repr
        )
        if not same:
            entries.append(entry)

    stored: dict[str, Any] = {"bench": bench, "file": dest.name, "kind": KIND}
    if stored_rev is not None:
        stored["rev"] = stored_rev
    if params_repr is not None:
        stored["params"] = params_repr
    entries.append(stored)
    registry["entries"] = entries
    save_registry(root, registry)
    return dest


def load_profiles_json(html_dir: Path) -> dict[str, str]:
    path = Path(html_dir) / "profiles.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict) and isinstance(data.get("paths"), dict):
        return {str(k): str(v) for k, v in data["paths"].items() if v is not None}
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}
    return {}


def write_profiles_json(html_dir: Path, paths: dict[str, str]) -> Path:
    html_dir = Path(html_dir)
    html_dir.mkdir(parents=True, exist_ok=True)
    out = html_dir / "profiles.json"
    payload = {"paths": dict(sorted(paths.items()))}
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def publish(
    html_dir: str | Path,
    *,
    from_dir: str | Path | None = None,
    rev: str | int | None = None,
    merge: bool = True,
) -> dict[str, str]:
    html_dir = Path(html_dir)
    src = Path(from_dir) if from_dir is not None else default_profile_dir()
    dest_dir = html_dir / "profiles" / KIND
    dest_dir.mkdir(parents=True, exist_ok=True)

    paths = load_profiles_json(html_dir) if merge else {}
    registry = load_registry(src)
    entries = list(registry.get("entries") or [])

    html_files = {p.name: p for p in src.glob("*.html")}
    if not entries and html_files:
        for name, path in html_files.items():
            bench = name[: -len(".html")] if name.endswith(".html") else name
            entries.append({"bench": bench, "file": path.name, "kind": KIND})

    for entry in entries:
        bench = entry.get("bench")
        fname = entry.get("file")
        if not bench or not fname:
            continue
        src_file = src / str(fname)
        if not src_file.is_file():
            continue
        dest_file = dest_dir / str(fname)
        shutil.copy2(src_file, dest_file)
        rel = f"{SUBDIR}/{fname}"
        entry_rev = entry.get("rev")
        if entry_rev in (None, ""):
            entry_rev = rev
        if entry_rev not in (None, ""):
            paths[profile_key(str(bench), entry_rev)] = rel
        else:
            paths[str(bench)] = rel

    write_profiles_json(html_dir, paths)
    return paths


def cmd_publish(args: argparse.Namespace) -> int:
    paths = publish(
        args.html_dir,
        from_dir=args.from_dir,
        rev=args.rev,
        merge=not args.no_merge,
    )
    print(
        f"Published {len(paths)} profile path(s) into "
        f"{Path(args.html_dir) / 'profiles.json'}"
    )
    for k, v in sorted(paths.items()):
        print(f"  {k} -> {v}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    src = Path(args.from_dir) if args.from_dir else default_profile_dir()
    print(json.dumps(load_registry(src), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m asv_bench_memray",
        description="asv_bench_memray: ray_* metrics + profiles.json for asv-tachyon",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    p_prof = sub.add_parser("profiles", help="Manage memray profile artifacts")
    psub = p_prof.add_subparsers(dest="profiles_cmd", required=True)

    pub = psub.add_parser(
        "publish",
        help="Copy .asv/profiles/memray into html_dir and merge profiles.json",
    )
    pub.add_argument("--html-dir", type=Path, required=True)
    pub.add_argument("--from", dest="from_dir", type=Path, default=None)
    pub.add_argument("--rev", default=None)
    pub.add_argument("--no-merge", action="store_true")
    pub.set_defaults(func=cmd_publish)

    show = psub.add_parser("show", help="Print local profile registry")
    show.add_argument("--from", dest="from_dir", type=Path, default=None)
    show.set_defaults(func=cmd_show)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
