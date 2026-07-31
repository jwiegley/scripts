import importlib.machinery
import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


SCRIPT = Path(__file__).with_name("transcribe")
SCRIPT_PYTHON = Path("/etc/profiles/per-user/johnw/bin/python3")


def load_transcribe():
    if importlib.util.find_spec("numpy") is None:
        sys.modules.setdefault("numpy", ModuleType("numpy"))
    loader = importlib.machinery.SourceFileLoader("transcribe_under_test", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


transcribe = load_transcribe()


def write_route(path: Path, **overrides: object) -> dict[str, object]:
    document: dict[str, object] = {
        "version": 1,
        "provider": "omlx",
        "model": "Qwen3.6-27B-oQ4e-mtp",
        "base_url": "http://localhost:8000/v1/",
        "api_key": "dummy-key",
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")
    return document


def write_key(path: Path, value: str = "explicit-secret") -> None:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)


def run_cli(*args: object, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT_PYTHON), str(SCRIPT), *(str(arg) for arg in args)],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_load_managed_route_requires_exact_versioned_fields(tmp_path: Path) -> None:
    path = tmp_path / "route.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "provider": "omlx",
                "model": "Qwen3.6-27B-oQ4e-mtp",
                "base_url": "http://localhost:8000/v1/",
                "api_key": "dummy-key",
            }
        ),
        encoding="utf-8",
    )

    route = transcribe.load_managed_llm_route(path)

    assert route.provider == "omlx"
    assert route.model == "Qwen3.6-27B-oQ4e-mtp"
    assert route.base_url == "http://localhost:8000/v1"
    assert route.api_key == "dummy-key"


def test_load_managed_route_rejects_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"

    with pytest.raises(ValueError, match=re.escape(str(path))):
        transcribe.load_managed_llm_route(path)


def test_load_managed_route_rejects_invalid_json_without_exposing_contents(
    tmp_path: Path,
) -> None:
    path = tmp_path / "route.json"
    secret = "must-not-appear-in-errors"
    path.write_text(f'{{"api_key": "{secret}", invalid', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        transcribe.load_managed_llm_route(path)

    message = str(exc_info.value)
    assert str(path) in message
    assert secret not in message


@pytest.mark.parametrize("document", [[], "route", 1, None])
def test_load_managed_route_requires_a_json_object(
    tmp_path: Path, document: object
) -> None:
    path = tmp_path / "route.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="object"):
        transcribe.load_managed_llm_route(path)


@pytest.mark.parametrize("version", [0, 2, "1", None])
def test_load_managed_route_rejects_unsupported_versions(
    tmp_path: Path, version: object
) -> None:
    path = tmp_path / "route.json"
    write_route(path, version=version)

    with pytest.raises(ValueError, match="version 1"):
        transcribe.load_managed_llm_route(path)


@pytest.mark.parametrize("field", ["provider", "model", "base_url", "api_key"])
@pytest.mark.parametrize("value", [None, "", "   ", 42, True, [], {}])
def test_load_managed_route_rejects_missing_or_empty_string_fields(
    tmp_path: Path, field: str, value: object
) -> None:
    path = tmp_path / "route.json"
    document = write_route(path)
    if value is None:
        del document[field]
    else:
        document[field] = value
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        transcribe.load_managed_llm_route(path)

    assert field in str(exc_info.value)
    assert "dummy-key" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"model": "manual-model"}, ("manual-model", "http://localhost:8000/v1", "dummy-key")),
        ({"api_base": "https://override.test/v1/"}, ("Qwen3.6-27B-oQ4e-mtp", "https://override.test/v1", "dummy-key")),
        ({"api_key": "file-secret"}, ("Qwen3.6-27B-oQ4e-mtp", "http://localhost:8000/v1", "file-secret")),
    ],
)
def test_route_resolution_applies_cli_precedence_independently(
    tmp_path: Path,
    overrides: dict[str, str],
    expected: tuple[str, str, str],
) -> None:
    config = tmp_path / "route.json"
    write_route(config)
    key_file = None
    if "api_key" in overrides:
        key_file = tmp_path / "key"
        write_key(key_file, overrides.pop("api_key"))

    route = transcribe.resolve_llm_route(
        model=overrides.get("model"),
        api_base=overrides.get("api_base"),
        api_key_file=key_file,
        llm_config=config,
    )

    assert route.provider == "omlx"
    assert (route.model, route.base_url, route.api_key) == expected


def test_complete_explicit_postprocessing_route_bypasses_malformed_config(
    tmp_path: Path,
) -> None:
    config = tmp_path / "route.json"
    config.write_text("not json", encoding="utf-8")
    key_file = tmp_path / "key"
    write_key(key_file, "explicit-secret\n")

    route = transcribe.resolve_llm_route(
        model="manual-model",
        api_base="http://localhost:9000/v1/",
        api_key_file=key_file,
        llm_config=config,
    )

    assert route == transcribe.LlmRoute(
        provider="direct",
        model="manual-model",
        base_url="http://localhost:9000/v1",
        api_key="explicit-secret",
    )


def test_partial_explicit_postprocessing_route_requires_valid_managed_config(
    tmp_path: Path,
) -> None:
    config = tmp_path / "route.json"
    config.write_text("not json", encoding="utf-8")

    with pytest.raises(ValueError, match=re.escape(str(config))):
        transcribe.resolve_llm_route(
            model="manual-model",
            api_base="http://localhost:9000/v1",
            api_key_file=None,
            llm_config=config,
        )


def test_explicit_model_uses_direct_defaults_when_managed_file_is_absent(
    tmp_path: Path,
) -> None:
    route = transcribe.resolve_llm_route(
        model="manual-model",
        api_base=None,
        api_key_file=None,
        llm_config=tmp_path / "missing.json",
    )

    assert route == transcribe.LlmRoute(
        provider="direct",
        model="manual-model",
        base_url=transcribe.DEFAULT_API_BASE,
        api_key=transcribe.DEFAULT_API_KEY,
    )


def test_postprocessing_without_managed_route_or_explicit_model_is_refused(
    tmp_path: Path,
) -> None:
    path = tmp_path / "missing.json"

    with pytest.raises(ValueError, match=re.escape(str(path))):
        transcribe.resolve_llm_route(
            model=None,
            api_base=None,
            api_key_file=None,
            llm_config=path,
        )


@pytest.mark.parametrize(
    "failure",
    ["missing", "empty", "invalid-utf8", "directory", "insecure-mode"],
)
def test_api_key_file_failures_are_redacted(
    tmp_path: Path,
    failure: str,
) -> None:
    key_file = tmp_path / "key-file-secret-must-not-leak"
    if failure == "empty":
        write_key(key_file, "")
    elif failure == "invalid-utf8":
        key_file.write_bytes(b"\xffsecret-file-contents")
        key_file.chmod(0o600)
    elif failure == "directory":
        key_file.mkdir()
    elif failure == "insecure-mode":
        key_file.write_text("secret-file-contents", encoding="utf-8")
        key_file.chmod(0o644)

    with pytest.raises(ValueError) as exc_info:
        transcribe.resolve_llm_route(
            model="manual-model",
            api_base="http://localhost:9000/v1",
            api_key_file=key_file,
            llm_config=tmp_path / "missing-route.json",
        )

    message = str(exc_info.value)
    assert str(key_file) in message
    assert "secret-file-contents" not in message


def test_plain_asr_does_not_validate_llm_configuration(tmp_path: Path) -> None:
    config = tmp_path / "route.json"
    config.write_text("not json", encoding="utf-8")
    audio = tmp_path / "audio.wav"
    audio.touch()

    result = run_cli(
        "--llm-config",
        config,
        "--asr-model-dir",
        tmp_path / "missing-asr-model",
        audio,
    )

    assert result.returncode == 1
    assert "ASR model not found" in result.stderr
    assert "LLM configuration" not in result.stderr


def test_check_llm_config_validates_and_exits_before_asr(tmp_path: Path) -> None:
    config = tmp_path / "route.json"
    write_route(config)

    result = run_cli(
        "--llm-config",
        config,
        "--check-llm-config",
        "--asr-model-dir",
        tmp_path / "missing-asr-model",
    )

    assert result.returncode == 0, result.stderr
    assert "valid" in result.stdout.lower()
    assert "managed-secret" not in result.stdout + result.stderr
    assert "ASR model" not in result.stderr


def test_invalid_postprocessing_config_fails_before_asr_without_secret(
    tmp_path: Path,
) -> None:
    config = tmp_path / "route.json"
    secret = "never-print-this-secret"
    config.write_text(f'{{"api_key": "{secret}", invalid', encoding="utf-8")
    audio = tmp_path / "audio.wav"
    audio.touch()

    result = run_cli(
        "--llm-config",
        config,
        "--asr-model-dir",
        tmp_path / "missing-asr-model",
        "--prompt",
        "Clean this transcript",
        audio,
    )

    assert result.returncode != 0
    assert "LLM configuration" in result.stderr
    assert "ASR model" not in result.stderr
    assert secret not in result.stdout + result.stderr


def test_complete_explicit_cli_route_bypasses_malformed_config_before_asr(
    tmp_path: Path,
) -> None:
    config = tmp_path / "route.json"
    config.write_text("not json", encoding="utf-8")
    key_file = tmp_path / "key"
    write_key(key_file)
    audio = tmp_path / "audio.wav"
    audio.touch()

    result = run_cli(
        "--llm-config",
        config,
        "--asr-model-dir",
        tmp_path / "missing-asr-model",
        "--prompt",
        "Clean this transcript",
        "--model",
        "manual-model",
        "--api-base",
        "http://localhost:9000/v1",
        "--api-key-file",
        key_file,
        audio,
    )

    assert result.returncode == 1
    assert "ASR model not found" in result.stderr
    assert "LLM configuration" not in result.stderr
    assert "explicit-secret" not in result.stdout + result.stderr


def test_partial_explicit_cli_route_validates_config_before_asr(
    tmp_path: Path,
) -> None:
    config = tmp_path / "route.json"
    config.write_text("not json", encoding="utf-8")
    audio = tmp_path / "audio.wav"
    audio.touch()

    result = run_cli(
        "--llm-config",
        config,
        "--asr-model-dir",
        tmp_path / "missing-asr-model",
        "--prompt",
        "Clean this transcript",
        "--model",
        "manual-model",
        "--api-base",
        "http://localhost:9000/v1",
        audio,
    )

    assert result.returncode != 0
    assert "LLM configuration" in result.stderr
    assert "ASR model" not in result.stderr


class ModelsResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps({"data": [{"id": "model-b"}, {"id": "model-a"}]}).encode()


def test_urlopen_explicitly_loads_ssl_cert_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ca_file = tmp_path / "private-ca-bundle.pem"
    ca_file.write_text("test CA", encoding="utf-8")
    request = urllib.request.Request("https://api.test/v1/models")
    expected_context = object()
    expected_response = object()
    captured: dict[str, object] = {}

    def fake_create_default_context(*, cafile: str | None = None):
        captured["cafile"] = cafile
        return expected_context

    def fake_urlopen(
        actual_request: urllib.request.Request,
        timeout: int,
        context: object,
    ):
        captured.update(request=actual_request, timeout=timeout, context=context)
        return expected_response

    monkeypatch.setenv("SSL_CERT_FILE", str(ca_file))
    monkeypatch.setattr(transcribe.ssl, "create_default_context", fake_create_default_context)
    monkeypatch.setattr(transcribe.urllib.request, "urlopen", fake_urlopen)

    response = transcribe._urlopen(request, timeout=10)

    assert response is expected_response
    assert captured == {
        "cafile": str(ca_file),
        "request": request,
        "timeout": 10,
        "context": expected_context,
    }


def test_list_models_explicit_endpoint_and_key_bypass_managed_config_and_asr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "route.json"
    config.write_text("not json", encoding="utf-8")
    key_file = tmp_path / "key"
    write_key(key_file, "explicit-secret\n")
    captured_requests: list[urllib.request.Request] = []
    captured_timeouts: list[int] = []

    def fake_urlopen(
        request: urllib.request.Request, timeout: int, context: object
    ):
        assert context is not None
        captured_requests.append(request)
        captured_timeouts.append(timeout)
        return ModelsResponse()

    monkeypatch.setattr(transcribe.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--list-models",
            "--llm-config",
            str(config),
            "--api-base",
            "https://explicit.test/v1/",
            "--api-key-file",
            str(key_file),
            "--asr-model-dir",
            str(tmp_path / "missing-asr-model"),
        ],
    )

    transcribe.main()

    request = captured_requests[0]
    assert request.full_url == "https://explicit.test/v1/models"
    assert request.get_header("Authorization") == "Bearer explicit-secret"
    assert captured_timeouts == [10]
    assert capsys.readouterr().out == "model-a\nmodel-b\n"


def test_list_models_managed_defaults_and_explicit_endpoint_without_key(
    tmp_path: Path,
) -> None:
    config = tmp_path / "route.json"
    write_route(config)

    managed = transcribe.resolve_llm_route(
        model=None,
        api_base=None,
        api_key_file=None,
        llm_config=config,
        list_models=True,
    )
    explicit = transcribe.resolve_llm_route(
        model=None,
        api_base="http://localhost:9000/v1/",
        api_key_file=None,
        llm_config=tmp_path / "malformed-do-not-read.json",
        list_models=True,
    )

    assert managed.provider == "omlx"
    assert managed.base_url == "http://localhost:8000/v1"
    assert managed.api_key == "dummy-key"
    assert explicit.provider == "direct"
    assert explicit.base_url == "http://localhost:9000/v1"
    assert explicit.api_key == transcribe.DEFAULT_API_KEY


class StreamingResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def __iter__(self):
        return iter(
            [
                b'data: {"choices":[{"delta":{"content":"clean text"}}]}\n',
                b"data: [DONE]\n",
            ]
        )


def test_llm_process_sends_generic_openai_compatible_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_requests: list[urllib.request.Request] = []
    captured_timeouts: list[int] = []

    def fake_urlopen(
        request: urllib.request.Request, timeout: int, context: object
    ):
        assert context is not None
        captured_requests.append(request)
        captured_timeouts.append(timeout)
        return StreamingResponse()

    monkeypatch.setattr(transcribe.urllib.request, "urlopen", fake_urlopen)
    route = transcribe.LlmRoute(
        provider="omlx",
        model="test-model",
        base_url="https://api.test/v1",
        api_key="test-secret",
    )

    output = transcribe.llm_process("raw text", "Clean it", route)

    request = captured_requests[0]
    assert isinstance(request.data, bytes)
    payload = json.loads(request.data)
    expected = {
        "model": "test-model",
        "messages": [
            {"role": "system", "content": "Clean it"},
            {"role": "user", "content": "raw text"},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    assert payload == expected
    assert request.get_header("Authorization") == "Bearer test-secret"
    assert captured_timeouts == [600]
    assert output == "clean text"


class ArbitraryStreamingResponse:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def __iter__(self):
        return iter(self.lines)


@pytest.mark.parametrize(
    "lines",
    [
        [b"data: not-json\n", b"data: [DONE]\n"],
        [b"data: []\n", b"data: [DONE]\n"],
        [b'{"ignored":"not-sse"}\n', b"data: [DONE]\n"],
        [b'data: {"error":"upstream failed"}\n', b"data: [DONE]\n"],
        [b'data: {"choices":[42]}\n', b"data: [DONE]\n"],
        [b'data: {"choices":[{"delta":"invalid"}]}\n', b"data: [DONE]\n"],
        [b'data: {"choices":[{"delta":{"content":42}}]}\n', b"data: [DONE]\n"],
        [b'data: {"choices":[{"delta":{"content":"partial"}}]}\n'],
        [b"data: [DONE]\n"],
    ],
)
def test_llm_process_rejects_malformed_incomplete_or_empty_streams(
    lines: list[bytes],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_urlopen(
        _request: urllib.request.Request, timeout: int, context: object
    ):
        assert timeout == 600
        assert context is not None
        return ArbitraryStreamingResponse(lines)

    monkeypatch.setattr(transcribe.urllib.request, "urlopen", fake_urlopen)
    route = transcribe.LlmRoute(
        provider="omlx",
        model="test-model",
        base_url="https://api.test/v1",
        api_key="stream-secret-must-not-leak",
    )

    with pytest.raises(SystemExit) as exc_info:
        transcribe.llm_process("raw text", "Clean it", route)

    assert exc_info.value.code == 1
    output = capsys.readouterr()
    combined = output.out + output.err
    assert "stream-secret-must-not-leak" not in combined


def test_cli_forwards_the_resolved_route_and_transcript(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = tmp_path / "route.json"
    write_route(config)
    model_dir = tmp_path / "asr-model"
    model_dir.mkdir()
    audio = tmp_path / "audio.wav"
    audio.touch()

    class FakeAsr:
        @classmethod
        def from_dir(cls, path: Path):
            assert path == model_dir
            return cls()

        def transcribe(self, *_args: object, **_kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(text="raw transcript")

    class FakeAudio:
        def __len__(self) -> int:
            return transcribe.SAMPLE_RATE

    cohere_module = ModuleType("mlx_speech.generation.cohere_asr")
    setattr(cohere_module, "CohereAsrModel", FakeAsr)
    monkeypatch.setitem(sys.modules, "mlx_speech", ModuleType("mlx_speech"))
    monkeypatch.setitem(
        sys.modules, "mlx_speech.generation", ModuleType("mlx_speech.generation")
    )
    monkeypatch.setitem(sys.modules, "mlx_speech.generation.cohere_asr", cohere_module)
    monkeypatch.setattr(
        transcribe,
        "load_audio",
        lambda _path: FakeAudio(),
    )
    captured: dict[str, object] = {}

    def fake_llm_process(
        text: str,
        prompt: str,
        route: object,
    ) -> str:
        captured.update(
            text=text,
            prompt=prompt,
            route=route,
        )
        return "clean transcript"

    monkeypatch.setattr(transcribe, "llm_process", fake_llm_process)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--llm-config",
            str(config),
            "--asr-model-dir",
            str(model_dir),
            "--prompt",
            "Clean it",
            str(audio),
        ],
    )

    transcribe.main()

    output = capsys.readouterr()
    assert captured["text"] == "raw transcript\n"
    assert captured["prompt"] == "Clean it"
    route = captured["route"]
    assert isinstance(route, transcribe.LlmRoute)
    assert route.provider == "omlx"
    assert route.model == "Qwen3.6-27B-oQ4e-mtp"
    assert output.out == "clean transcript\n"


def test_help_describes_managed_configuration_without_exposing_a_secret(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    config = home / ".config/promptdeploy/default-llm.json"
    config.parent.mkdir(parents=True)
    secret = "help-must-not-read-this-secret"
    write_route(config, api_key=secret)

    result = run_cli("--help", env={**os.environ, "HOME": str(home)})

    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "default-llm.json" in output
    assert "--llm-config" in output
    assert "--check-llm-config" in output
    assert "--api-key-file" in output
    assert "explicit" in output.lower()
    assert re.search(r"--api-key(?:\s|$)", output) is None
    assert secret not in output


@pytest.mark.parametrize(
    "raw_arguments",
    [
        ["--api-key", "raw-secret-must-not-leak"],
        ["--api-key=raw-secret-must-not-leak"],
    ],
)
def test_removed_raw_api_key_option_is_rejected_without_echoing_secret(
    raw_arguments: list[str],
) -> None:
    result = run_cli(*raw_arguments)

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "--api-key has been removed" in output
    assert "--api-key-file" in output
    assert "raw-secret-must-not-leak" not in output
