import dockyter.config as config_module
from dockyter.config import DockyterConfig


def test_load_config_defaults_when_no_files(monkeypatch):
    def fake_candidate_paths():
        return []

    monkeypatch.setattr(config_module, "_candidate_paths", fake_candidate_paths)

    cfg = config_module.load_config()

    assert isinstance(cfg, DockyterConfig)
    assert cfg.backend_mode == "docker"
    assert cfg.api_url == ""
    assert cfg.default_args == ""
    assert cfg.profiles == {}


def test_load_config_from_env_file(monkeypatch, tmp_path):
    """Un fichier pointé par DOCKYTER_CONFIG doit être pris en compte."""
    config_text = """
        [backend]
        mode = "api"
        api_url = "http://example.com"

        [docker]
        default_args = "-v /tmp:/tmp ubuntu:22.04"

        [profiles]
        local = "-v /tmp:/tmp ubuntu:22.04"
        ml    = "--gpus all -v /data:/data pytorch/pytorch:latest"
    """

    cfg_path = tmp_path / "dockyter.toml"
    cfg_path.write_text(config_text, encoding="utf-8")

    monkeypatch.setenv("DOCKYTER_CONFIG", str(cfg_path))

    cfg = config_module.load_config()

    assert cfg.backend_mode == "api"
    assert cfg.api_url == "http://example.com"
    assert cfg.default_args == "-v /tmp:/tmp ubuntu:22.04"
    assert cfg.profiles == {
        "local": "-v /tmp:/tmp ubuntu:22.04",
        "ml": "--gpus all -v /data:/data pytorch/pytorch:latest",
    }


def test_load_config_skips_invalid_toml(monkeypatch, tmp_path):
    bad_path = tmp_path / "bad.toml"
    bad_path.write_text("invalid toml implementation", encoding="utf-8")

    good_path = tmp_path / "good.toml"
    good_path.write_text(
        """
        [backend]
        mode = "api"
        api_url = "http://example.com"
        """,
        encoding="utf-8",
    )

    def fake_candidate_paths():
        return [bad_path, good_path]

    monkeypatch.setattr(config_module, "_candidate_paths", fake_candidate_paths)

    cfg = config_module.load_config()

    assert cfg.backend_mode == "api"
    assert cfg.api_url == "http://example.com"


def test_load_config_stops_at_first_existing_file(monkeypatch, tmp_path):
    first_path = tmp_path / "first.toml"
    first_path.write_text(
        """
        [backend]
        mode = "api"

        [docker]
        default_args = "FIRST_ARGS"
        """,
        encoding="utf-8",
    )

    second_path = tmp_path / "second.toml"
    second_path.write_text(
        """
        [backend]
        mode = "docker"

        [docker]
        default_args = "SECOND_ARGS"
        """,
        encoding="utf-8",
    )

    def fake_candidate_paths():
        return [first_path, second_path]

    monkeypatch.setattr(config_module, "_candidate_paths", fake_candidate_paths)

    cfg = config_module.load_config()

    assert cfg.backend_mode == "api"
    assert cfg.default_args == "FIRST_ARGS"
