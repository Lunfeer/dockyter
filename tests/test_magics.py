import dockyter.magics as magics_module
from dockyter.backend import CommandResult


class FakeShell:
    def __init__(self):
        self.calls = []
        self.system = self._default_system

    def _default_system(self, cmd):
        self.calls.append(cmd)

class FakeDockerBackend():
    def __init__(self):
        self.calls = []

    def get_status(self):
        return True, "Docker is installed and the daemon is running."

    def dockyter_command(self, cmd, args):
        res = CommandResult()
        res.stdout = f"Docker backend: {cmd} [{args}]"
        res.stderr = ""
        self.calls.append((cmd, args))
        return res

class FakeAPIBackend():
    def __init__(self, url):
        self.calls = []
        self.url = url

    def get_status(self):
         return True, f"API backend reachable at {self.url}"
    
    def dockyter_command(self, cmd, args):
        res = CommandResult()
        res.stdout = f"API backend: {cmd} [{args}]"
        res.stderr = ""
        self.calls.append((cmd, args))
        return res


def test_docker_backend_magic_switches_to_docker(monkeypatch, capsys):
    monkeypatch.setattr(magics_module, "DockerBackend", FakeDockerBackend)
    monkeypatch.setattr(magics_module, "APIBackend", FakeAPIBackend)

    shell = FakeShell()
    dockyter = magics_module.Dockyter(shell=shell)

    dockyter.docker_backend_magic("docker")
    assert isinstance(dockyter.backend, FakeDockerBackend)

    captured = capsys.readouterr().out
    assert "Switched backend to Docker (local daemon)." in captured
    assert "Dockyter backend type: Docker" in captured


def test_docker_backend_magic_switches_to_api(monkeypatch, capsys):
    monkeypatch.setattr(magics_module, "DockerBackend", FakeDockerBackend)
    monkeypatch.setattr(magics_module, "APIBackend", FakeAPIBackend)

    shell = FakeShell()
    dockyter = magics_module.Dockyter(shell=shell)

    dockyter.docker_backend_magic("api https://api.example.com")
    assert isinstance(dockyter.backend, FakeAPIBackend)
    assert dockyter.backend.url == "https://api.example.com"

    captured = capsys.readouterr().out
    assert "Switched backend to APIBackend (https://api.example.com)." in captured
    assert "Dockyter backend type: API" in captured


def test_docker_backend_magic_no_args(capsys):
    shell = FakeShell()
    dockyter = magics_module.Dockyter(shell=shell)

    dockyter.docker_backend_magic("")

    captured = capsys.readouterr().out
    assert "Usage: %docker_backend <docker|api> [api_url]" in captured


def test_docker_backend_magic_unknown_mode(capsys):
    shell = FakeShell()
    dockyter = magics_module.Dockyter(shell=shell)

    dockyter.docker_backend_magic("badmode")

    captured = capsys.readouterr().out
    assert "Unknown backend. Use docker or api." in captured


def test_docker_line_magic(monkeypatch, capsys):
    monkeypatch.setattr(magics_module, "DockerBackend", FakeDockerBackend)
    monkeypatch.setattr(magics_module, "APIBackend", FakeAPIBackend)

    shell = FakeShell()
    monkeypatch.setattr(magics_module, "get_ipython", lambda: shell)

    dockyter = magics_module.Dockyter(shell=shell)
    original_system = shell.system

    dockyter.docker_line_magic("ubuntu:latest -v /tmp:/tmp")
    assert dockyter.docker_args == "ubuntu:latest -v /tmp:/tmp"
    assert dockyter.docker_reroute_enabled is True
    assert shell.system == dockyter.docker_console  
    assert dockyter.original_system == original_system

    assert dockyter.backend.calls == [("echo 'Connected'", "ubuntu:latest -v /tmp:/tmp")]

    captured = capsys.readouterr().out
    assert "Connected" in captured


def test_docker_on_and_off_magics(monkeypatch):
    monkeypatch.setattr(magics_module, "DockerBackend", FakeDockerBackend)
    monkeypatch.setattr(magics_module, "APIBackend", FakeAPIBackend)

    shell = FakeShell()
    monkeypatch.setattr(magics_module, "get_ipython", lambda: shell)

    dockyter = magics_module.Dockyter(shell=shell)
    original_system = shell.system

    dockyter.docker_on_magic()
    assert dockyter.docker_reroute_enabled is True
    assert shell.system == dockyter.docker_console
    assert dockyter.original_system == original_system

    dockyter.docker_off_magic()
    assert dockyter.docker_reroute_enabled is False
    assert shell.system == original_system


def test_docker_cell_magic(monkeypatch, capsys):
    monkeypatch.setattr(magics_module, "DockerBackend", FakeDockerBackend)
    monkeypatch.setattr(magics_module, "APIBackend", FakeAPIBackend)

    shell = FakeShell()
    dockyter = magics_module.Dockyter(shell=shell)

    dockyter.docker_cell_magic("ubuntu:latest", "echo hello")
    assert dockyter.backend.calls == [("echo hello", "ubuntu:latest")]

    captured = capsys.readouterr().out
    assert "Docker backend: echo hello [ubuntu:latest]" in captured
