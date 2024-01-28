# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'ASV Memray Benchmark'
copyright = '2024, Rohit Goswami'
author = 'Rohit Goswami'
release = '0.1.0'

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
