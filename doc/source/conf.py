# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import importlib.util
from pathlib import Path


def _read_project_version():
    # Walk to the repository root: the directory that holds both
    # pyproject.toml and the asv_bench_memray package. Same rule as
    # asv_bench_memray._version._pyproject_path. A fixed parent index is
    # not used, so moving this file under doc/ does not change the result.
    here = Path(__file__).resolve()
    root = None
    for candidate in here.parents:
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "asv_bench_memray"
        ).is_dir():
            root = candidate
            break
    if root is None:
        raise RuntimeError(f"repository root not found from {here}")
    path = root / "asv_bench_memray" / "_version.py"
    spec = importlib.util.spec_from_file_location(
        "asv_bench_memray._version", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_project_version()


project = 'ASV Memray Benchmark'
copyright = '2024, Rohit Goswami'
author = 'Rohit Goswami'
# Sphinx release is the full version string:
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-release
release = _read_project_version()

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "autodoc2",
    "myst_parser",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",  # Links to source code
]

templates_path = ['_templates']
exclude_patterns = []

autodoc2_render_plugin = 'myst'

autodoc2_packages = [
    "../../asv_bench_memray",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
    "asv": ("https://asv.readthedocs.io/en/latest/", None),
    "asv_runner": ("https://asv.readthedocs.io/projects/asv-runner/en/latest/", None),
}
myst_enable_extensions = ["fieldlist", "deflist"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']
