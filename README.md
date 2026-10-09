# NoybMedia

**An open-source Wistia video downloader built with Python.**

NoybMedia is a Python application designed to download Wistia-hosted videos that you own or are authorized to access. It aims to provide a reliable command-line interface and a simple web interface for retrieving media, selecting available video quality, and saving files locally.

Part of the **Noybcore** open-source ecosystem.

> **Status:** Under active development. Features described below are planned unless explicitly marked as implemented.

## Features

- **Wistia URL and media ID support** — accept supported Wistia media references.
- **Media metadata** — retrieve available video information when accessible.
- **Quality selection** — choose from formats and resolutions actually offered by the source.
- **Video downloads** — stream media to disk without loading the entire video into memory.
- **Meaningful filenames** — preserve or generate safe, descriptive filenames.
- **Progress reporting** — communicate download progress and failures.
- **Batch downloads** — process multiple media references with configurable limits.
- **CLI and web interfaces** — support both terminal-based and browser-based workflows.
- **Automated testing** — validate application behavior using repeatable tests.

## Technology stack

- Python
- uv for project and dependency management
- `pyproject.toml` and `uv.lock`
- FastAPI for the web interface and HTTP API
- Typer for the CLI
- HTTPX for HTTP communication and streaming
- pytest for automated testing
- Ruff for linting and formatting
- Pyright for static type checking
- GitHub Actions for continuous integration

## Getting started

### Prerequisites

- A supported Python version specified in `pyproject.toml`
- [uv](https://docs.astral.sh/uv/)
- Git

### Installation

Clone the repository:

```bash
git clone https://github.com/no-yb-core/noybmedia.git
cd noybmedia
```

Install the project and development dependencies:

```bash
uv sync --all-groups
```

The CLI and web interface will receive their usage instructions when their implementations are available.

## Development

Run the test suite:

```bash
uv run pytest
```

Check code quality:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

The project uses a `src/`-based package layout. Core download logic is shared between interfaces to avoid duplicated behavior.

## Roadmap

- [ ] Establish the Python package and project configuration.
- [ ] Add automated tests and CI.
- [ ] Implement Wistia URL and media ID validation.
- [ ] Implement media metadata retrieval.
- [ ] Implement available-format selection.
- [ ] Implement robust, streamed video downloads.
- [ ] Build the CLI.
- [ ] Build the web interface.
- [ ] Configure deployment and production safeguards.
- [ ] Publish a stable release.

## Responsible use

NoybMedia is intended for media that users own or are authorized to download. It does not aim to bypass authentication, access controls, DRM, or other technical restrictions.

Users are responsible for respecting copyright, applicable laws, and the terms governing their access to media.

## Contributing

Contributions and bug reports are welcome. Please open an issue before undertaking substantial changes. Code contributions should include relevant tests and pass the configured quality checks.

## License

The project license will be specified before the first public release.

## Noybcore

NoybMedia is part of the Noybcore open-source ecosystem.

- Organization: https://github.com/no-yb-core
- Website: https://noybcore.com