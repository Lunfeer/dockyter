# Dockyter User Guide

This document explains how to install Dockyter, how to use its magics in notebooks, and how to troubleshoot common issues.

---

## 1. Requirements

- Python 3.12+
- IPython / Jupyter (e.g. JupyterLab, Jupyter Notebook)
- For the Docker backend:
  - `docker` CLI available on `PATH`
  - access to a Docker-compatible daemon (Docker, rootless Podman, etc.)
- For the API backend:
  - network access to your Dockyter-compatible HTTP API

---

## 2. Installation

Install from PyPI:

```bash
pip install dockyter
```

Then in a notebook:

```python
%load_ext dockyter
```

You should now have access to:

* the `%%docker` cell magic,
* the `%docker`, `%docker_status`, `%docker_backend`, `%docker_profile` line magics,
* optional shell redirection for `!cmd`.

---

## 3. Basic usage

### 3.1 Run a whole cell in Docker: `%%docker`

```python
%%docker ubuntu:22.04
echo "Hello from inside the container"
pwd
```

* The **entire cell** runs inside a single container.
* Lines share the same shell state (`cd`, environment variables, etc.).
* This is the recommended way to run anything non-trivial.

Works with both backends:

* Docker backend → runs `docker run ...` locally.
* API backend → sends `cmd` and `args` to `POST /execute`.

---

### 3.2 Configure `!` redirection: `%docker` + `!`

```python
%docker -v /host/path:/data ubuntu:22.04
```

Then:

```python
!ls /data
!echo "another command"
```

Behaviour:

* `%docker` stores the Docker arguments and image.
* Subsequent `!cmd` calls are rerouted to the active backend.
* Each `!cmd` runs in a **fresh container** (no shared shell state).
* For multi-line scripts or `cd`, prefer `%%docker`.

---

## 4. Backends

### 4.1 Docker backend (default)

This backend calls the local `docker` CLI:

```bash
docker run --rm [ARGS] IMAGE bash -lc "cmd"
```

Switch explicitly to the Docker backend:

```python
%docker_backend docker
%docker_status
```

### 4.2 API backend

The API backend sends commands to an HTTP API that you implement.

Switch to the API backend:

```python
%docker_backend api http://127.0.0.1:8000
%docker_status
```

See the README section “API backend contract” for the exact HTTP interface.

---

## 5. Configuration file (`dockyter.toml`)

Dockyter can read a configuration file to set:

* default backend (`docker` or `api`),
* optional `api_url`,
* default Docker arguments (`default_args`),
* named profiles for `%docker_profile`.

Search order (first file wins):

1. `DOCKYTER_CONFIG` environment variable, if set.
2. `dockyter.toml` in the current working directory.
3. `~/.dockyter.toml`
4. `~/.config/dockyter/config.toml`

Example:

```toml
[backend]
mode = "api"
api_url = "http://127.0.0.1:8000"

[docker]
default_args = "-v /tmp:/tmp ubuntu:22.04"

[profiles]
local = "-v /tmp:/tmp ubuntu:22.04"
ml    = "--gpus all -v /data:/data pytorch/pytorch:latest"
```

Usage in a notebook:

```python
%load_ext dockyter

# Use the "local" profile from dockyter.toml
%docker_profile local
!pwd

# Switch to ML profile
%docker_profile ml
!python -c "print('Hello from ML container')"
```

If no configuration file is found, Dockyter falls back to built-in defaults:
Docker backend and empty arguments.

---

## 6. Command reference

* `%%docker [DOCKER ARGS...] IMAGE[:TAG]`
  Run the cell in a single container via the active backend.

* `%docker [DOCKER ARGS...] IMAGE[:TAG]`
  Configure Docker mode for `!cmd` via the active backend.

* `%docker_status`
  Show current backend, availability, `!` redirection status, and current args.

* `%docker_backend docker`
  Switch to the local Docker backend.

* `%docker_backend api <URL>`
  Switch to the HTTP API backend.

* `%docker_profile NAME`
  Load Docker arguments from a named profile in `dockyter.toml` and apply them as if `%docker ...` was called.

* `%docker_on` / `%docker_off`
  Enable/disable `!` redirection.

---

## 7. Troubleshooting

### Docker backend

* **“Docker is not installed or not available in the system PATH.”**
  The `docker` command is missing. Install Docker and ensure `docker` is on your `PATH`.

* **“Docker daemon is not running. Please start the Docker service.”**
  The CLI is present but the daemon is down. Start Docker Desktop / the Docker service.

* **Red error about forbidden flags**
  Dockyter refuses some dangerous flags (e.g. `--privileged`, `--network=host`).
  Remove them or run your commands outside Dockyter.

### API backend

* **“API backend unreachable at …”**
  The URL is wrong, the server is down, or network access is blocked.

* **“Invalid JSON response from Dockyter API.”**
  The API is not following the expected contract (`stdout` / `stderr` JSON fields).
