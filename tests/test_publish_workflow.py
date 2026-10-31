from __future__ import annotations

from pathlib import Path


def _job_keys(text: str) -> list[str]:
    """Keys of the pypi-publish job, indented four spaces.

    List items under ``steps`` are not job keys. GitHub Actions rejects a
    duplicate key at this level (``environment`` and ``permissions``).
    """
    keys: list[str] = []
    in_job = False
    for raw in text.splitlines():
        if raw.startswith("  pypi-publish:"):
            in_job = True
            continue
        if not in_job:
            continue
        if raw and not raw.startswith(" "):
            break
        if raw.startswith("    ") and not raw.startswith("     "):
            stripped = raw.strip()
            if stripped.startswith("-") or ":" not in stripped:
                continue
            keys.append(stripped.split(":", 1)[0])
    return keys


def _workflow_text() -> str:
    root = Path(__file__).resolve().parents[1]
    return (root / ".github" / "workflows" / "python-publish.yml").read_text(
        encoding="utf-8"
    )


def test_publish_workflow_has_no_duplicate_keys():
    keys = _job_keys(_workflow_text())
    assert keys == ["runs-on", "if", "environment", "permissions", "steps"]
    assert len(keys) == len(set(keys))


def test_duplicate_job_keys_are_rejected():
    sample = (
        "jobs:\n"
        "  pypi-publish:\n"
        "    environment:\n"
        "      name: pypi\n"
        "    permissions:\n"
        "      id-token: write\n"
        "    environment:\n"
        "      name: other\n"
    )
    keys = _job_keys(sample)
    assert keys.count("environment") == 2
    assert len(keys) != len(set(keys))
