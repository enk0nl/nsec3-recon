# Contribution Guidelines

## Project structure

```text
src/nsec3_recon/        Python package
tests/                  project tests
docs/                   documentation
scripts/                install, bootstrap, and asset helpers
assets/                 generated local assets, not committed
deps/src/               external dependency checkouts, not committed
runs/                   run workspaces, not committed
```

## Tests

Run project tests without collecting dependency tests:

```bash
pytest tests
```

Common focused checks:

```bash
pytest tests/test_docs.py
pytest tests/test_pipeline_flow.py
python -m ruff format --check .
python -m ruff check .
```

## Documentation style

- Keep README as the product entry point.
- Put detailed installation, usage, configuration, dashboard, and troubleshooting content in `docs/`.
- Use repository-relative links for internal files.
- Avoid duplicated sections and generated prose.
- Use `pytest tests` in docs unless pytest discovery is explicitly constrained.

## Dependency policy

Do not change dependency pins, scheduler refs, repository refs, installer refs, or commit hashes casually. Dependency updates should be focused changes with tool-check output and compatibility notes.

## Submitting changes

Keep patches scoped. Separate documentation cleanup, behavior changes, dependency updates, and generated asset changes into different submissions.
