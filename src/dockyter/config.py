from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict
import os
import tomllib


@dataclass
class DockyterConfig:
    backend_mode: str = "docker"        
    api_url: str = ""
    default_args: str = ""              
    profiles: Dict[str, str] = field(default_factory=dict)


def _candidate_paths():
    paths = []

    env_path = os.environ.get("DOCKYTER_CONFIG")
    if env_path:
        paths.append(Path(env_path))

    cwd = Path.cwd()
    paths.append(cwd / "dockyter.toml")

    home = Path.home()
    paths.append(home / ".dockyter.toml")
    paths.append(home / ".config" / "dockyter" / "config.toml")

    return paths


def load_config():
    cfg = DockyterConfig()

    for path in _candidate_paths():
        if not path.is_file():
            continue

        try:
            with path.open("rb") as f:
                data = tomllib.load(f)
        except Exception:
            continue

        backend = data.get("backend", {})
        if isinstance(backend, dict):
            mode = backend.get("mode")
            if isinstance(mode, str):
                cfg.backend_mode = mode

            api_url = backend.get("api_url")
            if isinstance(api_url, str):
                cfg.api_url = api_url

        docker_section = data.get("docker", {})
        if isinstance(docker_section, dict):
            default_args = docker_section.get("default_args")
            if isinstance(default_args, str):
                cfg.default_args = default_args

        profiles_section = data.get("profiles", {})
        if isinstance(profiles_section, dict):
            for profile_name, args in profiles_section.items():
                if isinstance(args, str):
                    cfg.profiles[profile_name] = args
        break

    return cfg
