# Dockyter

<!-- Optional: badges -->
[![CI](https://github.com/Lunfeer/dockyter/actions/workflows/ci.yml/badge.svg)](https://github.com/Lunfeer/dockyter/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/dockyter.svg)](https://pypi.org/project/dockyter/)
[![License](https://img.shields.io/pypi/l/dockyter.svg)](https://github.com/Lunfeer/dockyter/blob/main/LICENSE)

<p align="center">
  <img src="docs/media/dockyter-banner.png" alt="Dockyter banner" width="600">
</p>

Dockyter is an IPython extension that adds:

- a `%%docker` **cell magic** to run whole cells inside Docker containers,
- an optional `!` **shell redirection** so that `!cmd` runs inside Docker,
- and a **pluggable backend** system:
  - **local Docker daemon** (default),
  - or a **remote HTTP API** backend.

The goal is to run heavy CLI tools packaged as Docker images from notebooks,
while keeping the base Python environment light and reproducible.

Typical use cases:

- running ML frameworks, data validation tools, or internal CLIs from Docker images,
- keeping notebook kernels small and simple,
- using the same Dockerised tools across local Jupyter, JupyterHub, and Binder-like deployments,
- delegating container execution to a remote HTTP API instead of the local Docker daemon.

---

## Highlights

- IPython / Jupyter magics:
  - `%%docker` cell magic
  - `%docker` + `!` shell redirection
- Pluggable backends:
  - local Docker daemon
  - HTTP API backend (FastAPI example included)
- Configurable via `dockyter.toml`:
  - default backend and Docker args
  - named profiles via `%docker_profile`
- Tested:
  - unit tests (backends + magics)
  - integration tests that execute real notebooks and the example API
- Automatic releases:
  - GitHub Actions build and publish to PyPI on tagged releases

---

## Installation

```bash
pip install dockyter
```

Then in a notebook:

```python
%load_ext dockyter
```

By default, Dockyter expects:

* a working `docker` CLI on `PATH`, and
* access to a Docker-compatible daemon (or rootless runtime)

in order to run containers with the **Docker backend**.

If you use the **API backend**, the Docker daemon can live on a separate machine:
Dockyter just talks HTTP to your API.

---

## Backends: Docker daemon vs HTTP API

Dockyter has two backends:

* **Docker backend** (default)
  Runs containers by calling the local `docker` CLI:

  ```bash
  docker run --rm [ARGS] IMAGE bash -lc "cmd"
  ```

* **API backend**
  Sends commands to an HTTP API that you implement and manage.

You can switch backend at runtime:

```python
# Use local Docker daemon (default)
%docker_backend docker

# Use HTTP API backend
%docker_backend api http://127.0.0.1:8000
```

The current backend and status can be inspected with:

```python
%docker_status
```

This prints:

* which backend is active (`Docker` or `API`),
* whether it appears available,
* the current Docker arguments (image, volumes, etc.),
* whether `!` redirection is enabled.

---

## API backend contract

The API backend is intentionally small and simple.
Dockyter only assumes **two endpoints**:

1. **Health check**

   ```http
   GET /health
   ```

   * Must return a **2xx** status code if the backend is available.
   * Response body is ignored by Dockyter.

2. **Command execution**

   ```http
   POST /execute
   Content-Type: application/json
   ```

   Request body:

   ```json
   {
     "cmd": "echo hello",
     "args": "-v /host:/data ubuntu:22.04"
   }
   ```

   Response body (JSON):

   ```json
   {
     "stdout": "hello",
     "stderr": ""
   }
   ```

Dockyter:

* passes the **entire cell** or `!` command as `cmd`,
* passes the raw `%docker` / `%%docker` arguments as `args`,
* prints `stdout` to the notebook,
* prints `stderr` in **red** if not empty.

What happens inside the API is entirely up to you. A typical implementation:

* receives `cmd` and `args`,
* constructs a `docker run ...` command on the server,
* captures `stdout` / `stderr`,
* returns them in JSON.

But the API **does not have to use Docker** internally; it could use Kubernetes, a job queue, or anything else — Dockyter only cares about the HTTP contract above.

### Security responsibility

Dockyter **does not** implement any security for the API backend.

* Authentication, authorisation, rate limiting, logging, etc. are entirely the responsibility of the API owner.
* The example API server in this repository is **not** intended for exposure on the public internet. It is a minimal reference implementation for local / trusted environments.
* A real deployment must:

  * protect the API (auth, HTTPS),
  * control which images and arguments are allowed,
  * run on a hardened host.

Dockyter only provides a convenient **client** for this API from inside notebooks; it is **not** a security boundary.

---

## Basic usage

### Cell magic: `%%docker` (recommended)

```python
%%docker myorg/tool:latest
echo "Hello from inside the container"
pwd
```

The **entire cell** is sent to `bash -lc` inside a **single container**.
All lines share the same shell state:

* `cd` persists for the rest of the cell,
* environment variables set in one line are visible to the others,
* multi-line scripts, `if`/`for`, heredocs, etc. work as expected.

This is the recommended way to run anything non-trivial in Docker from a notebook.

The same syntax works with both backends:

* Docker backend → runs `docker run ...` locally.
* API backend → sends `cmd` and `args` to `POST /execute`.

---

### Line magic: `%docker` + `!` redirection

```python
%docker -v /host/path:/data myorg/tool:latest
```

Then:

```python
!tool --input /data/file.txt
```

Here `%docker` **configures** Dockyter:

* Docker arguments and image are stored,
* subsequent `!cmd` calls in that notebook are rerouted to the active backend:

  * Docker backend → `docker run --rm [ARGS] IMAGE bash -lc "cmd"`
  * API backend → `POST /execute` with `cmd="cmd"` and `args="[ARGS] IMAGE"`

Important behaviour:

* each `!cmd` runs in a **fresh container** (or fresh backend execution),
* shell state is **not** shared between `!` calls:

  ```python
  %docker myimage:latest
  !cd /data
  !pwd   # runs in a new container. Not in /data
  ```

For anything that relies on `cd`, multi-line shell logic, or persistent state, prefer `%%docker`.
`%docker` + `!` is best for simple one-shot commands.

---

## Commands

* `%%docker [DOCKER ARGS...] IMAGE[:TAG]`
  Run the cell content in a single Docker container with the given image/arguments,
  using the currently selected backend.

* `%docker [DOCKER ARGS...] IMAGE[:TAG]`
  Configure “Docker mode” for `!` so that each `!cmd` is executed inside a container
  via the currently selected backend. (`%docker_on` is effectively activated.)

* `%docker_off`
  Restore the original `!` behaviour (no Docker redirection).

* `%docker_on`
  Activate Docker mode for `!` again, using the last configured image/arguments.

* `%docker_status`
  Show the current backend type, its availability, whether `!` redirection is enabled,
  and which image/arguments are currently configured.

* `%docker_backend docker`
  Use the local Docker daemon backend. (call %docker_status automatically after)

* `%docker_backend api <URL>`
  Use an HTTP API backend at the given base URL (for example `http://127.0.0.1:8000`). (call %docker_status automatically after)

* `%docker_profile NAME`
  Load a named profile from the config file (see below) to set image/arguments for `%docker`.

---

## Configuration file (optional)

Dockyter can read an optional `dockyter.toml` configuration file to choose:

- which backend to use by default (`docker` vs `api`),
- default Docker arguments (image, volumes, etc.),
- named profiles for `%docker_profile`.

Dockyter looks for the first config file in this order:

1. The path given by the `DOCKYTER_CONFIG` environment variable.
2. `dockyter.toml` in the current working directory.
3. `~/.dockyter.toml`
4. `~/.config/dockyter/config.toml`

The first file found wins. If no file is found, built-in defaults are used.

Example `dockyter.toml`:

```toml
[backend]
mode = "api"                         # "docker" or "api"
api_url = "http://127.0.0.1:8000"    # required for "api"

[docker]
default_args = "-v /tmp:/tmp ubuntu:22.04"

[profiles]
local = "-v /tmp:/tmp ubuntu:22.04"
ml    = "--gpus all -v /data:/data pytorch/pytorch:latest"
```

With this file in place:

* `%load_ext dockyter` will automatically use the API backend and `default_args`.

* `%docker_profile local` is equivalent to:

  ```python
  %docker -v /tmp:/tmp ubuntu:22.04
  ```

* `%docker_profile ml` configures Dockyter to use the ML image/profile.

---

## Binder / JupyterHub integration (high-level)

In BinderHub / JupyterHub, Dockyter can be used in a few ways:

### 1. Extension-only (safest default)

- Install `dockyter` in the image (e.g. via `requirements.txt`).
- Users do `%load_ext dockyter` in notebooks.
- If `docker` is not available in the container, Dockyter just reports it and does not crash.

This is the right choice for **public / untrusted** notebook environments.

### 2. Direct Docker daemon access (trusted only)

You can expose a Docker runtime inside user containers and use the **Docker backend**.

This is **very dangerous** for public notebooks:

- Users can bypass Dockyter and run `!docker ...` directly,
- including flags like `--privileged` or `--network=host`.

Only consider this if users are trusted and the platform is carefully locked down.

### 3. API backend (recommended for untrusted users)

A safer option for public or multi-tenant setups:

- Do **not** expose `docker` in user containers.
- Run a separate, hardened Dockyter-compatible **API backend**.
- In notebooks, use:

```python
  %docker_backend api https://your-secure-api.example.com
```

The API is then responsible for all security (auth, allowed images/flags, rate limiting, etc.).

Dockyter is **not** a security boundary; it only provides convenience and light guardrails.
Real isolation must come from the surrounding platform or the API implementation.

---

## Documentation

- **User guide** – Installation, basic usage, troubleshooting  
  `docs/user-guide.md`

- **Developer guide** – Architecture, code layout, style, tests  
  `docs/developer-guide.md`

---

## Examples

This repository includes several example notebooks and an example API server:

* `docs/examples/01_local_cli.ipynb`
  Run simple commands in a **local Docker image** (`%%docker` basics).

* `docs/examples/02_ml_tool_in_docker.ipynb`
  Use a real ML framework (e.g. PyTorch) inside Docker, keeping the notebook kernel light.

* `docs/examples/03_api_backend.ipynb`
  Use Dockyter with the **API backend**, switching with `%docker_backend api` and running
  commands via the HTTP API instead of the local Docker daemon.

* `docs/examples/04_config_profiles.ipynb`
  Demonstrates the `dockyter.toml` configuration file and the `%docker_profile` magic
  for reusable Docker argument profiles.
  
* `docs/api_example/server.py`
  Minimal example of a Dockyter-compatible API implemented with FastAPI + Uvicorn.
  This is a reference implementation for local / trusted environments only.

Exemples are also on nbviewer:
  - **Local CLI**: https://nbviewer.org/github/Lunfeer/dockyter/blob/main/docs/examples/01_local_cli.ipynb  
  - **ML in Docker**: https://nbviewer.org/github/Lunfeer/dockyter/blob/main/docs/examples/02_ml_tool_in_docker.ipynb  
  - **API backend**: https://nbviewer.org/github/Lunfeer/dockyter/blob/main/docs/examples/03_api_backend.ipynb  
  - **Config profiles**: https://nbviewer.org/github/Lunfeer/dockyter/blob/main/docs/examples/04_config_profiles.ipynb

---

## Tests

Dockyter has:

* **Unit tests** for:

  * `DockerBackend` and `APIBackend` (using monkeypatch for `subprocess` / `requests`),
  * the IPython magics layer.

* **Integration tests** that:

  * execute the example notebooks via `nbconvert`,
  * start the example API server for API backend tests,
  * fail if Dockyter prints error messages in red.

You can run them locally with:

```bash
# Unit tests only
uv run pytest -m "not integration"

# Full test suite (including notebook + API integration)
uv run pytest
```

## Contributing

Contributions are welcome !

- Fork the repository and create a feature branch.
- Keep changes small and focused (one feature or fix per pull request).
- Make sure tests pass locally:

  ```bash
  # Unit tests only
  uv run pytest -m "not integration"

  # Full test suite (notebooks + API example)
  uv run pytest
  ```

* If you change behaviour or add features, consider:

* updating / adding example notebooks under `docs/examples/`,
* updating the user/developer guides under `docs/`.

Open a pull request on GitHub once everything is green.