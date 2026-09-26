# Development, documentation and CI

## One Python environment

```sh
uv sync --locked --group docs
uv run bandgap --help
uv run python -m unittest discover -s tests -p 'test_*.py'
uv run bandgap acceptance
```

The last command requires installed EDA tools; the CLI tests run without them.
The project pins its default Python in `.python-version` and locks runtime and
documentation dependencies in `uv.lock`. Use `uv add` or `uv add --group docs`
when changing dependencies, and commit both the project metadata and lockfile.

The console command is a small Typer adapter in `bandgap_cli.py`. The project is
intended to run from a source checkout: its schematics, cells and configuration
are repository assets. It is not a standalone PyPI application wheel. Numerical
and physical evaluation remains in the visible `tools/` scripts. The adapter
uses its environment's Python interpreter and preserves subprocess exit codes.

## Provided starter generation and checks

```sh
uv run python -m starter --check
uv run python tests/starter_acceptance.py --pdk-root pdk
```

The first command checks the committed files in `templates/provided` against the
schematic and bundled cell geometry, without EDA tools. Run
`uv run python -m starter` to regenerate those assets deliberately after source
changes; review the resulting diff. The generator rejects unsupported assembly
parameters instead of silently dropping or miscounting devices. `bandgap new`
copies the committed template and does not run extraction or regenerate parts.

The second command uses Magic/Netgen to check the reference, every electrical
tile type, the tray's extracted device inventory, its expected circuit-LVS
mismatch, and its DRC. It also checks direct editor loading and the locations of
known extraction warnings. It retains logs in `runs/starter-validation-*`.
See the [design record](starter-design.md) for the boundary and measured results.

## Preview and build documentation

```sh
uv run --group docs mkdocs serve
uv run --group docs mkdocs build --strict
```

Edit the existing Markdown files in place. `scripts/docs_hook.py` stages them
and an explicit set of public design assets into ignored `.docs-build/` during
builds. README becomes the home page. No manual duplication of the journal,
rules, testbench notes or evidence is needed. `mkdocs.yml` supplies the navigation;
new Markdown pages must be added there because strict builds flag omitted pages.
The hook never stages `tools.local.yaml`, simulation runs, environments or Git
metadata. Site output is ignored in `site/`.

Material provides full-text search, light/dark themes, copyable code, section
navigation and a table of contents. Markdown extensions provide tabs,
admonitions, collapsible details, footnotes, highlighted code and Mermaid.
LaTeX equations use Arithmatex and a pinned MathJax 3.2.2 browser runtime; that
runtime is loaded from jsDelivr. Pages remain readable without it, but rendering
math requires access to that CDN. No analytics or external web fonts are enabled.

Configuration follows the official [uv project guide](https://docs.astral.sh/uv/guides/projects/),
[Material navigation guide](https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/),
and [Material math guide](https://squidfunk.github.io/mkdocs-material/reference/math/).

## GitHub Actions and Pages

Every main-branch push and pull request runs CLI contract tests and builds the
entire site in strict mode using the locked dependencies. Main-branch builds
publish the artifact through GitHub's Pages deployment action; pull requests
build only. The workflow uses separate build and deploy permissions, and does
not need a personal access token. See the [GitHub Pages workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

The hosted workflow does **not** claim analog/DRC qualification: the PDK is
bundled, but hosted runners have no EDA executables. Run `uv run bandgap acceptance` and the appropriate evaluation
profile on a configured workstation when changing the evaluator. The existing
[reference qualification](reference-results.md) remains dated measurement evidence,
not a claim that each documentation build reruns those simulations.
