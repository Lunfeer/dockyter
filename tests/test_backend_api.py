import requests
from dockyter.backend import APIBackend


class FakeResponse:
    def __init__(self, ok=True, status_code=200, json_data=None):
        self.ok = ok
        self.status_code = status_code
        self._json_data = json_data or {}

    def raise_for_status(self):
        if not self.ok:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def test_api_backend_success(monkeypatch):
    FAKE_API_GOOD_RESULT = "Hello from fake API"
    calls_get = []
    calls_post = []

    def fake_get(url, timeout):
        calls_get.append(url)
        assert url.endswith("/health")
        return FakeResponse(ok=True, status_code=200)

    def fake_post(url, json, timeout):
        calls_post.append((url, json))
        assert url.endswith("/execute")
        assert json["cmd"] == "echo hello"
        assert "ubuntu:latest" in json["args"]
        return FakeResponse(
            ok=True,
            status_code=200,
            json_data={
                "stdout": FAKE_API_GOOD_RESULT,
                "stderr": ""
            },
        )

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    backend = APIBackend("https://api.example.com")
    result = backend.dockyter_command("echo hello", "ubuntu:latest -v /tmp:/tmp")

    assert result.stdout == FAKE_API_GOOD_RESULT
    assert result.stderr == ""

    assert len(calls_get) == 1
    assert len(calls_post) == 1


def test_api_backend_unreachable(monkeypatch):
    calls_get = []
    calls_post = []

    def fake_get(url, timeout):
        calls_get.append(url)
        raise requests.RequestException("Connection error")

    def fake_post(url, json, timeout):
        calls_post.append((url, json))
        return FakeResponse(
            ok=True, 
            status_code=200, 
            json_data={
                "stdout": "SHOULD NOT BE USED",
                "stderr": "SHOULD NOT BE USED"
            }
        )

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    backend = APIBackend("https://api.example.com")
    result = backend.dockyter_command("echo hello", "ubuntu:latest -v /tmp:/tmp")

    assert result.stdout == ""
    assert "API backend unreachable at " in result.stderr
    assert len(calls_get) == 1
    assert len(calls_post) == 0


def test_api_backend_forbidden_flag(monkeypatch):
    calls_get = []
    calls_post = []

    def fake_get(url, timeout):
        calls_get.append(url)
        return FakeResponse(ok=True, status_code=200)

    def fake_post(url, json, timeout):
        calls_post.append((url, json))
        return FakeResponse(
            ok=True,
            status_code=200,
            json_data={
                "stdout": "SHOULD NOT BE USED", 
                "stderr": "SHOULD NOT BE USED"
            },
        )

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    backend = APIBackend("https://api.example.com")
    result = backend.dockyter_command("echo hello", "ubuntu:latest --privileged")

    assert result.stdout == ""
    assert "Forbidden Docker flag detected: " in result.stderr

    assert len(calls_get) == 1
    assert len(calls_post) == 0
