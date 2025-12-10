import nbformat
import subprocess
import pytest
from pathlib import Path
from nbconvert.preprocessors import ExecutePreprocessor

RED_ANSI = "\x1b[91m"
RESET_ANSI = "\x1b[0m"
NOTEBOOK_DIR = Path("docs/examples")
API_URL = "http://127.0.0.1:8000"

@pytest.fixture(scope="session")
def api_server():
    proc = subprocess.Popen(
        [
            "uvicorn",
            "docs.api_example.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

@pytest.mark.integration
@pytest.mark.parametrize(
    "notebook_path",
    list(NOTEBOOK_DIR.glob("*.ipynb")),
)
def test_example_notebook_runs_without_red_errors(api_server, notebook_path, tmp_path):
    with notebook_path.open() as f:
        nb = nbformat.read(f, as_version=4)

    ep = ExecutePreprocessor(
        timeout=600,
        kernel_name="python3",
    )
    ep.preprocess(nb, {"metadata": {"path": str(tmp_path)}})

    red_messages = []

    for cell in nb.cells:
        for output in cell.get("outputs", []):
            if output.get("output_type") != "stream":
                continue

            text = output.get("text", "")

            start = text.find(RED_ANSI)
            if start == -1:
                continue
            start_content = start + len(RED_ANSI)

            end = text.find(RESET_ANSI)
            content = text[start_content:end]
            red_messages.append(content)

    assert not red_messages, (
        f"Notebook {notebook_path} printed error messages in red:\n"
        + "\n---\n".join(red_messages)
    )
