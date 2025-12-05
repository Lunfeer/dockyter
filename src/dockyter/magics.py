import subprocess
from IPython.core.magic import (Magics, magics_class, line_magic, cell_magic)
from IPython.core.getipython import get_ipython

DOCKER_STATUS_GOOD_MESSAGE = "Docker is installed and the daemon is running."
DOCKER_NOT_INSTALLED_MESSAGE = "Docker is not installed or not available in the system PATH."
DOCKER_DAEMON_NOT_RUNNING_MESSAGE = "Docker daemon is not running. Please start the Docker service."
DOCKER_FORBIDDEN_FLAGS = [
    "--privileged",
    "--network=host",
    "--net=host",
]

@magics_class
class Dockyter(Magics):
    def __init__(self, shell=None, **kwargs):
        super().__init__(shell=shell, **kwargs)
        self.docker_args: str = ""
        self.original_system = None
        self.docker_reroute_enabled = False

    def docker_exist(self):
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        return result.returncode == 0
    
    def docker_daemon_running(self):
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        stderr = result.stderr.lower()
        if "failed to connect" in stderr or "daemon" in stderr:
            return False
        return True
    
    def get_docker_status(self):
        is_docker_available = self.docker_exist()
        if not is_docker_available:
            return DOCKER_NOT_INSTALLED_MESSAGE
        is_daemon_running = self.docker_daemon_running()
        if not is_daemon_running:
            return DOCKER_DAEMON_NOT_RUNNING_MESSAGE
        return DOCKER_STATUS_GOOD_MESSAGE

    def validate_docker_args(self, args: str) -> bool:
        tokens = args.split()
        for flag in DOCKER_FORBIDDEN_FLAGS:
            if flag in tokens:
                print(f"Forbidden Docker flag detected: {flag}")
                print("Please remove this flag and try again.")
                return False
        return True


    def docker_command(self, cmd, args=None):
        if args is None:
            args = self.docker_args
        full_cmd = [
            "docker", "run", "--rm",
        ] + args.split() + [
            "bash", "-lc", cmd
        ]

        result = subprocess.run(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,          
            encoding="utf-8",   
            errors="replace",   
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr

        return output


    def docker_console(self, cmd):
        print(self.docker_command(cmd))

    @line_magic("docker_status")
    def docker_status_magic(self, line):
        docker_status = self.get_docker_status()

        print(f"Docker runtime: {docker_status}")
        print(f"Docker redirection for '!': {'on' if self.docker_reroute_enabled else 'off'}")
        
        if self.docker_args:
            print(f"Current docker args: {self.docker_args}")

    @line_magic("docker")
    def docker_line(self, line):
        docker_status = self.get_docker_status()
        if docker_status != DOCKER_STATUS_GOOD_MESSAGE:
            print(docker_status)
            return
        
        if not self.validate_docker_args(line):
            return

        self.docker_args = line

        ip = get_ipython()
        if ip is not None:
            self.original_system = ip.system
            self.docker_on()
            print(self.docker_command("echo 'Connected'"))
        else:
            print("Could not access IPython instance to reroute '!' commands.")

    @line_magic("docker_on")
    def docker_on(self, line = ""):
        ip = get_ipython()
        if ip is not None:
            self.original_system = ip.system
            ip.system = self.docker_console
            self.docker_reroute_enabled = True
        else:
            print("Could not access IPython instance to reroute '!' commands.")

    @line_magic("docker_off")
    def docker_off(self, line = ""):
        ip = get_ipython()
        if ip is not None and self.original_system is not None:
            ip.system = self.original_system
            self.docker_reroute_enabled = False
        else:
            print("Could not access IPython instance to restore original '!' behavior.")

    @cell_magic("docker")
    def docker_cell(self, line, cell):
        docker_status = self.get_docker_status()
        if docker_status != DOCKER_STATUS_GOOD_MESSAGE:
            print(docker_status)
            return
        
        if not self.validate_docker_args(line):
            return

        print(self.docker_command(cell, args=line))
