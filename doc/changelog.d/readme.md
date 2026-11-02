# Usage

`towncrier` is used for keeping track of the changelog. The relevant configuration aspects are:
- Each file can be formatted using markdown
- The contents are rendered in bullets
- Each file should be labeled with the corresponding **pull request**, e.g. `NUM.TYPE.md`
  + Where there is no clear corresponding pull request, `+` can be used instead of `NUM`

For mapping the types to headings, the following table can be used:


| **TYPE** | **Heading**                 |
| feat     | New Features                |
| api      | API Changes                 |
| bugfix   | Bug Fixes                   |
| misc     | Other Changes and Additions |

## Release


<!-- [[[cog
import sys
from pathlib import Path
start = Path(cog.inFile).resolve().parent
root = start
while not (
    (root / "pyproject.toml").is_file()
    and (root / "asv_bench_memray").is_dir()
):
    if root.parent == root:
        raise RuntimeError("repository root not found from %s" % start)
    root = root.parent
sys.path.insert(0, str(root))
from asv_bench_memray._version import read_project_version
version = read_project_version()
when = '"$(date -u +%Y-%m-%d)"'
cog.outl("```bash")
cog.outl("# View the changes")
cog.outl(
    "towncrier build --draft --version %s --date %s" % (version, when)
)
cog.outl("# Modify CHANGES.md")
cog.outl("towncrier build --version %s --date %s" % (version, when))
cog.outl("```")
]]] -->
```bash
# View the changes
towncrier build --draft --version 0.1.2 --date "$(date -u +%Y-%m-%d)"
# Modify CHANGES.md
towncrier build --version 0.1.2 --date "$(date -u +%Y-%m-%d)"
```
<!-- [[[end]]] -->
