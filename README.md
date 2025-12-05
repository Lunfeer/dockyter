# Dockyter

Dockyter is an IPython extension that adds a `%%docker` cell magic and optional `!` redirection so that you can run CLI tools packaged as Docker images from inside notebooks, while keeping the base Python environment light.

Typical use cases:

- running heavy tools (ML frameworks, data validators, internal CLIs) from Docker images,
- keeping notebook kernels small and simple,
- using the same Dockerised tools across local Jupyter, JupyterHub, and private Binder deployments.

---

## Installation

```bash
pip install dockyter
```

Then in a notebook:

```python
%load_ext dockyter
```

Dockyter expects a working `docker` CLI on `PATH` and access to a Docker-compatible daemon (or rootless runtime) in order to actually run containers.

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
* subsequent `!cmd` calls in that notebook are rerouted to:

```bash
docker run --rm [ARGS] IMAGE bash -lc "cmd"
```

Important behaviour:

* each `!cmd` runs in a **fresh container**,
* shell state is **not** shared between `!` calls:

  ```python
  %docker myimage:latest
  !cd /data
  !pwd   # runs in a new container → not in /data
  ```

For anything that relies on `cd`, multi-line shell logic, or persistent state, prefer `%%docker`.
`%docker` + `!` is best for simple one-shot commands.

---

## Commands

* `%%docker [DOCKER ARGS...] IMAGE[:TAG]`
  Run the cell content in a single Docker container with the given image/arguments.

* `%docker [DOCKER ARGS...] IMAGE[:TAG]`
  Configure “Docker mode” for `!` so that each `!cmd` is executed inside a container. (docker_on is activated automatically)

* `%docker_off`
  Restore the original `!` behaviour (no Docker redirection).

* `%docker_on`
  Activate Docker mode for `!` again, using the last configured image/arguments.

* `%docker_status`
  Show whether Docker mode is enabled and which image/arguments are currently configured.

---

## Behaviour when Docker is not available

If the `docker` CLI is not found on `PATH`, or `docker info` fails, Dockyter:

* prints a clear message (e.g. “Docker is not installed or not available in the system PATH.”),
* does **not** crash the kernel,
* leaves the `!` behaviour unchanged.

This makes it safe to include Dockyter in environments where Docker is not available (for example, many public Binder deployments): notebooks will still run, but `%%docker` will simply report that Docker is unavailable.

---

## Private Binder / JupyterHub integration (high-level)

In a **private BinderHub / JupyterHub** deployment, Dockyter can be integrated at two levels:

1. **Extension-only (safe default)**

   * Install `dockyter` into the image built by repo2docker (e.g. via `requirements.txt`).
   * Users can `"%load_ext dockyter"` in their notebooks.
   * If no `docker` CLI is available inside the user container, Dockyter just prints its “Docker not available” message and does not crash.

2. **Docker-enabled profiles (advanced, trusted users)**

   * The JupyterHub/Binder admin provides a special notebook image that includes:

     * `dockyter`, and
     * a container runtime (Docker or rootless Podman) accessible from the user container.
   * Only selected profiles/kernels get this image.
   * In those environments, `%%docker` and `%docker` can actually launch containers, while isolation and resource limits are still enforced at the JupyterHub/Binder infrastructure level.

Dockyter itself is **not** a security sandbox. Even if dockyter filters out some dangerous Docker flags, a malicious user with access to `docker` inside their container could still escape it. Real isolation must be handled by the surrounding platform (JupyterHub/Binder, Kubernetes, etc.). Dockyter only adds in-kernel guardrails and convenience. 

---

## Examples

* `examples/01_local_cli.ipynb` – Run simple commands in a local Docker image (`%%docker` basics).
* `examples/02_ml_tool_in_docker.ipynb` – Use a real ML framework (e.g. PyTorch) inside Docker, keeping the notebook kernel light.

(Additional examples, such as Binder-like environments or local Databricks Connect workflows, can be added under `examples/` as the project evolves.)
