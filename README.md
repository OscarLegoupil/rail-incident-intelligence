# Rail Incident Intelligence

A pipeline for extracting structured maintenance incident data from
heterogeneous rail operator reports.

## Quickstart

### Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (recommended package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/OscarLegoupil/rail-incident-intelligence.git
cd rail-incident-intelligence

# Install with dev dependencies
uv sync --group dev
```

### Usage

```bash
# Show available commands
uv run rail-ii --help

# Print version
uv run rail-ii version
```

### Development

```bash
# Run linter
make lint

# Auto-format
make format

# Run tests
make test

# Run all checks (lint + tests)
make check
```

## Project Structure

```
rail-incident-intelligence/
├── src/rail_ii/          # Main package
│   ├── cli.py            # Typer CLI entry-point
│   ├── config.py         # Pydantic-settings configuration
│   ├── models.py         # Domain models
│   └── pipeline.py       # Extraction pipeline (stub)
├── tests/                # Pytest test suite
├── docs/                 # Documentation
├── .github/workflows/    # CI
├── pyproject.toml        # Project metadata & tool config
├── Makefile              # Developer shortcuts
└── .env.example          # Environment variable template
```

## Configuration

Copy `.env.example` to `.env` and adjust values:

| Variable | Default | Description |
|---|---|---|
| `RAIL_II_DEBUG` | `false` | Enable debug mode |
| `RAIL_II_DATA_DIR` | `data` | Directory for raw report files |

## License

MIT
