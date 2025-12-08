import subprocess
import requests

DOCKER_STATUS_GOOD_MESSAGE = "Docker is installed and the daemon is running."
DOCKER_NOT_INSTALLED_MESSAGE = "Docker is not installed or not available in the system PATH."
DOCKER_DAEMON_NOT_RUNNING_MESSAGE = "Docker daemon is not running. Please start the Docker service."

DOCKER_FORBIDDEN_FLAGS = [
    "--privileged",
    "--network=host",
    "--net=host",
]

class CommandResult:
    stdout: str = ""
    stderr: str = "" 

def validate_docker_args(args: str):
    tokens = args.split()
    for flag in DOCKER_FORBIDDEN_FLAGS:
        if flag in tokens:
            return False, f"Forbidden Docker flag detected: {flag}"
    return True, ""

class DockerBackend:
    def docker_exist(self):
        result = subprocess.run(["docker"], capture_output=True, text=True)
        return result.returncode == 0
    
    def docker_daemon_running(self):
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        return result.returncode == 0
    
    def get_status(self):
        is_docker_available = self.docker_exist()
        if not is_docker_available:
            return False, DOCKER_NOT_INSTALLED_MESSAGE
        is_daemon_running = self.docker_daemon_running()
        if not is_daemon_running:
            return False, DOCKER_DAEMON_NOT_RUNNING_MESSAGE
        return True, DOCKER_STATUS_GOOD_MESSAGE
    
    def dockyter_command(self, cmd, args: str) -> CommandResult:
        result: CommandResult = CommandResult()

        ok, docker_status = self.get_status()
        if ok == False:
            result.stderr = docker_status
            return result

        ok, bad_flag_message = validate_docker_args(args)
        if ok == False: 
            result.stderr = bad_flag_message
            return result
        
        full_cmd = [
            "docker", "run", "--rm",
        ] + args.split() + [
            "bash", "-lc", cmd
        ]

        subprocessRes = subprocess.run(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,          
            encoding="utf-8",   
            errors="replace",   
        )

        result.stdout = subprocessRes.stdout
        result.stderr = subprocessRes.stderr

        return result

class APIBackend:
    def __init__(self, url):
        self.url = url.rstrip("/")

    def get_status(self):
        try:
            r = requests.get(f"{self.url}/health", timeout=10)
        except requests.RequestException as e:
            return False, f"API backend unreachable at {self.url}: {e}"
        if r.ok:
            return True, f"API backend reachable at {self.url}"
        return False, f"API backend error {r.status_code} at {self.url}"
        
    def dockyter_command(self, cmd, args: str) -> CommandResult:
        result: CommandResult = CommandResult()

        ok, api_status = self.get_status()
        if ok == False:
            result.stderr = api_status
            return result

        ok, bad_flag_message = validate_docker_args(args)
        if ok == False: 
            result.stderr = bad_flag_message
            return result
        
        body = {
            "cmd": cmd,
            "args": args,
        }

        try:
            r = requests.post(
                f"{self.url}/execute",
                json=body,
                timeout=10,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            result.stderr = f"Error calling Dockyter API at {self.url}/execute: {e}"
            return result

        try:
            data = r.json()
        except ValueError:
            result.stderr = "Invalid JSON response from Dockyter API."
            return result

        result.stdout = data.get("stdout", "")
        result.stderr = data.get("stderr", "")

        return result
        
