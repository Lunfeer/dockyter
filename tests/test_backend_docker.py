from operator import call
import subprocess
from dockyter.backend import DockerBackend, validate_docker_args

def test_validate_docker_args():
    VALID_ARGS = ["ubuntu:latest -v /tmp:/tmp", "ubuntu:latest -e VAR=1"]
    INVALID_ARGS = ["ubuntu:latest --privileged", "ubuntu:latest --network=host", "ubuntu:latest --net=host"]
    
    for args in VALID_ARGS:
        ok, bad_flag_message = validate_docker_args(args)
        assert ok
        assert bad_flag_message == ""
    
    for args in INVALID_ARGS:
        ok, bad_flag_message = validate_docker_args(args)
        assert not ok
        assert "Forbidden Docker flag detected: " in bad_flag_message

def test_docker_backend_sucess(monkeypatch):
    FAKE_DOCKER_GOOD_RESULT = "Hello from fake docker"
    calls_run = []
    calls_get_status = []

    def fake_run(cmd, *args, **kwargs):
        calls_run.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=FAKE_DOCKER_GOOD_RESULT,
            stderr="",
        )

    def fake_get_status(self):
        calls_get_status.append(True)
        return True, "Docker is installed and the daemon is running."

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(DockerBackend, "get_status", fake_get_status)

    backend = DockerBackend()
    
    result = backend.dockyter_command("echo hello", "ubuntu:latest -v /tmp:/tmp")

    assert result.stdout == FAKE_DOCKER_GOOD_RESULT
    assert result.stderr == ""

    assert len(calls_get_status) == 1
    assert len(calls_run) == 1
    full_cmd = calls_run[0]

    assert full_cmd[:3] == ["docker", "run", "--rm"]
    assert "ubuntu:latest" in full_cmd
    assert "bash" in full_cmd
    assert "-lc" in full_cmd
    assert "echo hello" in full_cmd

def test_docker_backend_docker_not_installed(monkeypatch):
    DOCKER_NOT_INSTALLED_MESSAGE = "Docker is not installed or not available in the system PATH."
    calls_run = []
    calls_get_status = []

    def fake_run(cmd, *args, **kwargs):
        calls_run.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="SHOULD NOT BE USED",
            stderr="SHOULD NOT BE USED",
        )

    def fake_get_status(self):
        calls_get_status.append(True)
        return False, DOCKER_NOT_INSTALLED_MESSAGE

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(DockerBackend, "get_status", fake_get_status)

    backend = DockerBackend()
    result = backend.dockyter_command("echo hello", "ubuntu:latest -v /tmp:/tmp")

    assert result.stdout == ""
    assert result.stderr == DOCKER_NOT_INSTALLED_MESSAGE

    assert len(calls_get_status) == 1
    assert len(calls_run) == 0  

def test_docker_backend_forbidden_flag(monkeypatch):
    calls_run = []
    calls_get_status = []

    def fake_run(cmd, *args, **kwargs):
        calls_run.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="SHOULD NOT BE USED",
            stderr="SHOULD NOT BE USED",
        )

    def fake_get_status(self):
        calls_get_status.append(True)
        return True, "Docker is installed and the daemon is running."

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(DockerBackend, "get_status", fake_get_status)

    backend = DockerBackend()
    result = backend.dockyter_command("echo hello", "ubuntu:latest --privileged")

    assert result.stdout == ""
    assert "Forbidden Docker flag detected: " in result.stderr

    assert len(calls_get_status) == 1
    assert len(calls_run) == 0
