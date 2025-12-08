from IPython.core.magic import (Magics, magics_class, line_magic, cell_magic)
from IPython.core.getipython import get_ipython
from .backend import DockerBackend, APIBackend, CommandResult

BACKEND_MODE_DOCKER = "docker"
BACKEND_MODE_API = "api"

@magics_class
class Dockyter(Magics):
    def __init__(self, shell=None, **kwargs):
        super().__init__(shell=shell, **kwargs)
        self.docker_args: str = ""
        self.original_system = None
        self.docker_reroute_enabled = False
        self.backend = DockerBackend()

    def print_error(self, message: str):
        print(f"\033[91m{message}\033[0m")

    def print_outputs(self, result: CommandResult):
        has_stdout = bool(result.stdout)
        has_stderr = bool(result.stderr)

        if has_stdout:
            print(result.stdout)

        if has_stderr:
            if not has_stdout:
                self.print_error(result.stderr)
            else:
                print(result.stderr)


    def docker_console(self, cmd):
        result = self.backend.dockyter_command(cmd, self.docker_args)
        self.print_outputs(result)

    @line_magic("docker_status")
    def docker_status_magic(self, line: str = ""):
        ok, docker_status = self.backend.get_status()
        docker_backend_type = "Docker" if isinstance(self.backend, DockerBackend) else "API"

        print("=== Dockyter Backend Status ===")
        print(f"Dockyter backend type: {docker_backend_type}")
        print(f"Dockyter backend status: {'available' if ok else 'unavailable'}")
        print(f"Dockyter backend status: {docker_status}")
        print(f"Dockyer redirection for '!': {'on' if self.docker_reroute_enabled else 'off'}")
        
        if self.docker_args:
            print(f"Current docker args: {self.docker_args}")

    @line_magic("docker_backend")
    def docker_backend_magic(self, line: str):
        parts = line.strip().split()

        if not parts:
            self.print_error("Usage: %docker_backend <docker|api> [api_url]")
            return

        mode = parts[0].lower()

        if mode == BACKEND_MODE_DOCKER:
            self.backend = DockerBackend()
            print("Switched backend to Docker (local daemon).")
            self.docker_status_magic()
            return

        if mode == BACKEND_MODE_API:
            if len(parts) < 2:
                self.print_error("Usage: %docker_backend api <api_url>")
                return
            url = parts[1]
            self.backend = APIBackend(url)
            print(f"Switched backend to APIBackend ({url}).")
            self.docker_status_magic()
            return

        self.print_error(f"Unknown backend. Use {BACKEND_MODE_DOCKER} or {BACKEND_MODE_API}.")


    @line_magic("docker")
    def docker_line_magic(self, line: str):
        self.docker_args = line

        ip = get_ipython()
        if ip is not None:
            self.original_system = ip.system
            self.docker_on_magic()
            result = self.backend.dockyter_command("echo 'Connected'", args=line)
            self.print_outputs(result)
        else:
            self.print_error("Could not access IPython instance to reroute '!' commands.")

    @line_magic("docker_on")
    def docker_on_magic(self, line: str = ""):
        ip = get_ipython()
        if ip is not None:
            self.original_system = ip.system
            ip.system = self.docker_console
            self.docker_reroute_enabled = True
        else:
            self.print_error("Could not access IPython instance to reroute '!' commands.")

    @line_magic("docker_off")
    def docker_off_magic(self, line: str = ""):
        ip = get_ipython()
        if ip is not None and self.original_system is not None:
            ip.system = self.original_system
            self.docker_reroute_enabled = False
        else:
            self.print_error("Could not access IPython instance to restore original '!' behavior.")

    @cell_magic("docker")
    def docker_cell_magic(self, line: str, cell):
        result = self.backend.dockyter_command(cell, args=line)
        self.print_outputs(result)
