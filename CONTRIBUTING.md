# Contributing

1. Create a focused branch and describe user-visible behavior.
2. Install with `make install` and enable hooks with `uv run pre-commit install`.
3. Keep cloud AI SDKs, telemetry, remote assets, and hard-coded local paths out of the project.
4. Add meaningful tests for behavior changes. Automated tests must not require Ollama or model downloads.
5. Run `make format`, `make lint`, `make typecheck`, `make test`, and `make evaluate`.
6. Add an Alembic migration for relational schema changes.
7. Update documentation, `TASKS.md`, and `CHANGELOG.md` where behavior changes.

Security-sensitive reports should follow `SECURITY.md` instead of public issue discussion.
