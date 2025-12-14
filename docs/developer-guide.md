# Dockyter Developer Guide

This document is for developers who want to understand the internals of Dockyter, run the tests, or contribute code.

---

## 1. Goals and scope

Dockyter aims to:

- provide a clean, tested IPython extension for running Docker-based tools from notebooks,
- support both a local Docker daemon and remote HTTP API backends,
- keep the core logic small and well-isolated (backend, config, magics),
- be safe to import even when Docker is unavailable (no kernel crashes).

---

## 2. Project structure

Main layout (simplified):

```text
dockyter/
├── src/
│   └── dockyter/
│       ├── __init__.py          # IPython entrypoint / extension registration
│       ├── backend.py           # DockerBackend, APIBackend, CommandResult, validation
│       ├── magics.py            # IPython magics 
│       └── config.py            # DockyterConfig dataclass and config file loader
│
├── docs/
│   ├── examples/
│   │   ├── 01_local_cli.ipynb
│   │   ├── 02_ml_tool_in_docker.ipynb
│   │   ├── 03_api_backend.ipynb
│   │   └── 04_config_profiles.ipynb
│   └── api_example/
│       └── server.py            # Example FastAPI implementation of the Dockyter API
│
└── tests/
    ├──  conftest.py
    ├── test_backend_docker.py
    ├── test_backend_api.py
    ├── test_magics.py
    └── test_notebooks_integration.py        
```
---

## 3. Backend design

### 3.1 CommandResult

`backend.py` defines a simple `CommandResult` object with:

* `stdout: str`
* `stderr: str`

Both backends return this object from `dockyter_command(cmd, args)`.

### 3.2 DockerBackend

Responsibilities:

* Check availability:

  * `docker_exist()` calls `docker info`.
  * `docker_daemon_running()` parses stderr from `docker info`.
  * `get_status()` returns `(ok: bool, message: str)`.
* Validate Docker flags with `validate_docker_args(args)`.
* Build and run:

  ```python
  full_cmd = ["docker", "run", "--rm"] + args.split() + ["bash", "-lc", cmd]
  subprocess.run(...)
  ```

Errors from Docker (`stderr`) are propagated via `CommandResult.stderr`.

### 3.3 APIBackend

Responsibilities:

* Check availability via `GET /health`.

* Send commands via `POST /execute` with JSON:

  ```json
  { "cmd": "...", "args": "..." }
  ```

* Parse JSON response and expose `stdout` / `stderr` via `CommandResult`.

The API contract is documented in the README (see “API backend contract”).

---

## 4. Config loader

`config.py` defines:

* `DockyterConfig` dataclass:

  ```python
  @dataclass
  class DockyterConfig:
      backend_mode: str = "docker"
      api_url: str = ""
      default_args: str = ""
      profiles: Dict[str, str] = field(default_factory=dict)
  ```

* `_candidate_paths()`:

  * `DOCKYTER_CONFIG` env var
  * `./dockyter.toml`
  * `~/.dockyter.toml`
  * `~/.config/dockyter/config.toml`

* `load_config()`:

  * returns a `DockyterConfig` instance with values filled from the first existing TOML file.
  * unknown keys are ignored.
---

## 5. IPython magics

`magics.py` defines the `Dockyter` class:

* Loads config on construction (`self.config = load_config()`).
* Chooses backend based on config.
* Exposes IPython magics:

  * `%%docker` → `docker_cell_magic`
  * `%docker` → `docker_line_magic`
  * `%docker_status`
  * `%docker_backend`
  * `%docker_profile`
  * `%docker_on` / `%docker_off`

The magics are registered by the standard IPython mechanism via:

```python
def load_ipython_extension(ip):
    ip.register_magics(Dockyter)
```

Error handling based on `CommandResult`:

* If there is only stderr, it is printed in red.
* If both stdout and stderr are non-empty, the stderr is printed normally (not red) to avoid treating mixed progress+output as an error.

---

## 6. Testing

Dockyter uses `pytest` and `nbconvert`.

### 6.1 Unit tests

* `tests/test_backend_docker.py`

  * tests `validate_docker_args`
  * tests `DockerBackend.dockyter_command` with monkeypatched `subprocess.run` and status checks
* `tests/test_backend_api.py`

  * tests `APIBackend.dockyter_command` with monkeypatched `requests.get`/`post`
* `tests/test_magics.py`

  * tests magics logic using fake backends and a fake IPython shell

Run:

```bash
# Unit tests only
uv run pytest -m "not integration"
```

On CI (GitHub Actions), this is also what runs before publishing to PyPI.

### 6.2 Integration tests

* `tests/test_notebooks_integration.py`

  * starts the example FastAPI server (fixture `api_server`)
  * executes notebooks under `docs/examples/` with `nbconvert`
  * scans outputs for red-colored error messages, and fails if any are found.

Run:

```bash
# Full test suite
uv run pytest
```

This is run on release workflows on GitHub Actions.

---

## 7. CI and release process

Dockyter is released via GitHub Actions and PyPI.

Typical release steps:

1. Bump the version in `pyproject.toml` (e.g. `0.3.0`).

2. Commit the change:

   ```bash
   git commit -m "chore: bump version to 0.3.0"
   git push origin main
   ```

3. Create a Git tag:

   ```bash
   git tag v0.3.0
   git push origin v0.3.0
   ```

4. The `release` GitHub Actions workflow builds the package and publishes it to PyPI if tests pass.

---

## 8. Coding style

* Python 3.12+ only.
* Use type hints where reasonable.
* Keep functions small and focused.
* Prefer pure logic in backends/config, side effects in magics only.
* Tests:

  * use `pytest`,
  * use `monkeypatch` for external calls (`subprocess`, `requests`),
  * keep tests deterministic and fast when possible.

---

## 9. Local development

### 9.1. Prerequisites

You’ll need:

* **Python** ≥ 3.12
* **Docker** installed and reachable via the `docker` CLI (for the Docker backend / examples)
* **uv** for dependency management: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

### 9.2. Install dependencies

Clone the repo and set up the environment:

```bash
# Clone
git clone https://github.com/Lunfeer/dockyter.git
cd dockyter

# Install main + dev dependencies
uv sync
```

This installs:

```toml
[project]
dependencies = [
    "ipython>=9.8.0",
    "requests>=2.32.5",
]

[dependency-groups]
dev = [
    "ipykernel>=7.1.0",
    "nbconvert>=7.16.6",
    "pytest>=9.0.2",
]
api-example = [
    "fastapi>=0.124.0",
    "pydantic>=2.12.5",
    "uvicorn>=0.38.0",
]
```

If you also want to run the **example API backend** used in the notebooks and integration tests:

```bash
uv sync --group api-example
```

### 9.3. Running tests

```bash
# Unit tests only
uv run pytest -m "not integration"

# Full suite (unit + notebook integration)
uv run pytest
```

> The integration tests will:
>
> * start the example FastAPI server in `docs/api_example/server.py`
> * execute the notebooks in `docs/examples/`
> * fail if Dockyter prints any “hard error” messages in red.

### 9.4. Playing with the notebooks

You can open and run the example notebooks under `docs/examples/`:

* `01_local_cli.ipynb`
* `02_ml_tool_in_docker.ipynb`
* `03_api_backend.ipynb`
* `04_config_profiles.ipynb`

