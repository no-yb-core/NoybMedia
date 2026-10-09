# Contributing to NoybMedia

Thank you for your interest in contributing to NoybMedia!

NoybMedia is an open-source Python project providing a CLI and FastAPI metadata API for Wistia media that users are authorized to access. Contributions of bug fixes, tests, documentation, and improvements are welcome.

## Before You Start

- Check the existing [issues](https://github.com/no-yb-core/NoybMedia/issues) to avoid duplicating work.
- For significant changes, open an issue or comment on an existing one before starting implementation.
- For issue #1 and other beginner-friendly tasks, please comment on the issue to discuss your proposed approach before opening a pull request.

## Development Setup

### Requirements

- Python 3.12 or newer, within the range supported by `pyproject.toml`
- [uv](https://docs.astral.sh/uv/)

### Set up the project

Clone the repository and enter its directory:

```bash
git clone https://github.com/no-yb-core/NoybMedia.git
cd NoybMedia
```

Install the project and its development dependencies:

```bash
uv sync --all-groups
```

Verify that the CLI works:

```bash
uv run noybmedia --help
```

## Code Quality and Tests

Run the test suite:

```bash
uv run pytest
```

Check test coverage:

```bash
uv run pytest --cov=noybmedia --cov-report=term-missing --cov-fail-under=90
```

Run Ruff linting and formatting checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run Pyright:

```bash
uv run pyright
```

Please ensure all checks pass before submitting a pull request.

## Contribution Guidelines

- Follow the existing project structure and coding conventions.
- Keep changes focused and avoid unrelated refactoring.
- Add or update tests for changed behavior.
- Update documentation when changing user-facing functionality.
- Preserve existing CLI commands and API behavior unless a change is explicitly intended and discussed.
- Never commit credentials, access tokens, private media URLs, or other secrets.
- Do not implement authentication bypasses, DRM circumvention, or access-control evasion. Contributions must respect applicable laws, platform terms, and media owners' permissions.

## Pull Requests

1. Create a branch for your change.
2. Implement the change and add relevant tests.
3. Run the quality checks described above.
4. Update documentation when needed.
5. Open a pull request against `main`.
6. Describe the problem, your solution, and how you tested it.
7. Link the related issue using GitHub's issue-closing syntax when appropriate, for example, `Closes #1`.

Keep pull requests focused and explain any trade-offs or design decisions that reviewers should know about.

## Questions

If you're unsure about an approach, ask in the relevant issue before investing significant time in implementation.

Thank you for helping improve NoybMedia!
