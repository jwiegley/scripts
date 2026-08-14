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
        "version": 2,
        "model": "DeepSeek-V4-Flash-0731-oQ8e-mtp",
        "base_url": "https://hera.lan:8443/v1/",
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


def test_load_route_requires_exact_versioned_fields(tmp_path: Path) -> None:
    path = tmp_path / "route.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "model": "DeepSeek-V4-Flash-0731-oQ8e-mtp",
                "base_url": "https://hera.lan:8443/v1/",
            }
        ),
        encoding="utf-8",
    )

    route = transcribe.load_llm_route(path)

    assert route.model == "DeepSeek-V4-Flash-0731-oQ8e-mtp"
    assert route.base_url == "https://hera.lan:8443/v1"
    assert route.api_key == transcribe.DEFAULT_API_KEY


def test_load_route_rejects_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"

    with pytest.raises(ValueError, match=re.escape(str(path))):
        transcribe.load_llm_route(path)


def test_load_route_rejects_invalid_json_without_exposing_contents(
    tmp_path: Path,
) -> None:
    path = tmp_path / "route.json"
    secret = "must-not-appear-in-errors"
    path.write_text(f'{{"api_key": "{secret}", invalid', encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        transcribe.load_llm_route(path)

    message = str(exc_info.value)
    assert str(path) in message
    assert secret not in message


@pytest.mark.parametrize("document", [[], "route", 1, None])
def test_load_route_requires_a_json_object(
    tmp_path: Path, document: object
) -> None:
    path = tmp_path / "route.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="object"):
        transcribe.load_llm_route(path)


@pytest.mark.parametrize("version", [0, 1, 3, "2", None])
def test_load_route_rejects_unsupported_versions(
    tmp_path: Path, version: object
) -> None:
    path = tmp_path / "route.json"
    write_route(path, version=version)

    with pytest.raises(ValueError, match="version 2"):
        transcribe.load_llm_route(path)


@pytest.mark.parametrize("field", ["model", "base_url"])
@pytest.mark.parametrize("value", [None, "", "   ", 42, True, [], {}])
def test_load_route_rejects_missing_or_empty_string_fields(
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
        transcribe.load_llm_route(path)

    assert field in str(exc_info.value)


@pytest.mark.parametrize("field", ["provider", "api_key", "token", "headers", "extra"])
def test_load_route_rejects_every_extra_field(tmp_path: Path, field: str) -> None:
    path = tmp_path / "route.json"
    value = "must-not-appear-in-errors"
    write_route(path, **{field: value})

    with pytest.raises(ValueError) as exc_info:
        transcribe.load_llm_route(path)

    assert value not in str(exc_info.value)


@pytest.mark.parametrize(
    "base_url",
    [
        "https://user:private-value@api.test/v1",
        "https://api.test/v1?token=private-value",
        "https://api.test/v1#private-value",
        "https://api.test/v1?",
        "https://api.test/v1#",
        "ftp://api.test/v1",
        "https:///v1",
    ],
)
def test_load_route_rejects_unsafe_base_urls_without_exposing_them(
    tmp_path: Path, base_url: str
) -> None:
    path = tmp_path / "route.json"
    write_route(path, base_url=base_url)

    with pytest.raises(ValueError) as exc_info:
        transcribe.load_llm_route(path)

    assert "private-value" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"model": "manual-model"}, ("manual-model", "https://hera.lan:8443/v1", "dummy-key")),
        ({"api_base": "https://override.test/v1/"}, ("DeepSeek-V4-Flash-0731-oQ8e-mtp", "https://override.test/v1", "dummy-key")),
        ({"api_key": "file-secret"}, ("DeepSeek-V4-Flash-0731-oQ8e-mtp", "https://hera.lan:8443/v1", "file-secret")),
    ],
)
def test_route_resolution_applies_cli_precedence_independently(
    tmp_path: Path,
    overrides: dict[str, str],
    expected: tuple[str, str, str],
) -> None:
    route_file = tmp_path / "route.json"
    write_route(route_file)
    key_file = None
    if "api_key" in overrides:
        key_file = tmp_path / "key"
        write_key(key_file, overrides.pop("api_key"))

    route = transcribe.resolve_llm_route(
        model=overrides.get("model"),
        api_base=overrides.get("api_base"),
        api_key_file=key_file,
        llm_route=route_file,
    )

    assert (route.model, route.base_url, route.api_key) == expected


def test_complete_explicit_postprocessing_route_bypasses_malformed_route(
    tmp_path: Path,
) -> None:
    route_file = tmp_path / "route.json"
    route_file.write_text("not json", encoding="utf-8")

    route = transcribe.resolve_llm_route(
        model="manual-model",
        api_base="http://localhost:9000/v1/",
        api_key_file=None,
        llm_route=route_file,
    )

    assert route == transcribe.LlmRoute(
        model="manual-model",
        base_url="http://localhost:9000/v1",
        api_key=transcribe.DEFAULT_API_KEY,
    )


def test_partial_explicit_postprocessing_route_requires_valid_route(
    tmp_path: Path,
) -> None:
    route_file = tmp_path / "route.json"
    route_file.write_text("not json", encoding="utf-8")

    with pytest.raises(ValueError, match=re.escape(str(route_file))):
        transcribe.resolve_llm_route(
            model="manual-model",
            api_base=None,
            api_key_file=None,
            llm_route=route_file,
        )


def test_explicit_model_uses_direct_defaults_when_route_file_is_absent(
    tmp_path: Path,
) -> None:
    route = transcribe.resolve_llm_route(
        model="manual-model",
        api_base=None,
        api_key_file=None,
        llm_route=tmp_path / "missing.json",
    )

    assert route == transcribe.LlmRoute(
        model="manual-model",
        base_url=transcribe.DEFAULT_API_BASE,
        api_key=transcribe.DEFAULT_API_KEY,
    )


def test_postprocessing_without_route_or_explicit_model_is_refused(
    tmp_path: Path,
) -> None:
    path = tmp_path / "missing.json"

    with pytest.raises(ValueError, match=re.escape(str(path))):
        transcribe.resolve_llm_route(
            model=None,
            api_base=None,
            api_key_file=None,
            llm_route=path,
        )


@pytest.mark.parametrize(
    "failure",
    ["missing", "empty", "invalid-utf8", "directory", "insecure-mode", "multiline"],
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
    elif failure == "multiline":
        write_key(key_file, "secret-file-contents\nsecond-line")

    with pytest.raises(ValueError) as exc_info:
        transcribe.resolve_llm_route(
            model="manual-model",
            api_base="http://localhost:9000/v1",
            api_key_file=key_file,
            llm_route=tmp_path / "missing-route.json",
        )

    message = str(exc_info.value)
    assert str(key_file) in message
    assert "secret-file-contents" not in message


def test_multiline_api_key_cli_error_is_redacted(tmp_path: Path) -> None:
    key_file = tmp_path / "key"
    private_value = "never-print-first-line\nnever-print-second-line"
    write_key(key_file, private_value)

    result = run_cli(
        "--prompt",
        "Clean this transcript",
        "--model",
        "manual-model",
        "--api-base",
        "http://localhost:9000/v1",
        "--api-key-file",
        key_file,
    )

    assert result.returncode != 0
    assert "single line" in result.stderr
    assert "never-print" not in result.stdout + result.stderr


def test_plain_asr_does_not_validate_llm_route(tmp_path: Path) -> None:
    route_file = tmp_path / "route.json"
    route_file.write_text("not json", encoding="utf-8")
    audio = tmp_path / "audio.wav"
    audio.touch()

    result = run_cli(
        "--llm-route",
        route_file,
        "--asr-model-dir",
        tmp_path / "missing-asr-model",
        audio,
    )

    assert result.returncode == 1
    assert "ASR model not found" in result.stderr
    assert "LLM route" not in result.stderr


def test_check_llm_route_validates_and_exits_before_asr(tmp_path: Path) -> None:
    route_file = tmp_path / "route.json"
    write_route(route_file)

    result = run_cli(
        "--llm-route",
        route_file,
        "--check-llm-route",
        "--asr-model-dir",
        tmp_path / "missing-asr-model",
    )

    assert result.returncode == 0, result.stderr
    assert "valid" in result.stdout.lower()
    assert "ASR model" not in result.stderr


def test_invalid_postprocessing_route_fails_before_asr_without_contents(
    tmp_path: Path,
) -> None:
    route_file = tmp_path / "route.json"
    private_value = "never-print-this-value"
    route_file.write_text(f'{{"token": "{private_value}", invalid', encoding="utf-8")
    audio = tmp_path / "audio.wav"
    audio.touch()

    result = run_cli(
        "--llm-route",
        route_file,
        "--asr-model-dir",
        tmp_path / "missing-asr-model",
        "--prompt",
        "Clean this transcript",
        audio,
    )

    assert result.returncode != 0
    assert "LLM route" in result.stderr
    assert "ASR model" not in result.stderr
    assert private_value not in result.stdout + result.stderr


def test_complete_explicit_cli_route_bypasses_malformed_route_before_asr(
    tmp_path: Path,
) -> None:
    route_file = tmp_path / "route.json"
    route_file.write_text("not json", encoding="utf-8")
    key_file = tmp_path / "key"
    write_key(key_file)
    audio = tmp_path / "audio.wav"
    audio.touch()

    result = run_cli(
        "--llm-route",
        route_file,
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
    assert "LLM route" not in result.stderr
    assert "explicit-secret" not in result.stdout + result.stderr


def test_partial_explicit_cli_route_validates_route_before_asr(
    tmp_path: Path,
) -> None:
    route_file = tmp_path / "route.json"
    route_file.write_text("not json", encoding="utf-8")
    audio = tmp_path / "audio.wav"
    audio.touch()

    result = run_cli(
        "--llm-route",
        route_file,
        "--asr-model-dir",
        tmp_path / "missing-asr-model",
        "--prompt",
        "Clean this transcript",
        "--model",
        "manual-model",
        audio,
    )

    assert result.returncode != 0
    assert "LLM route" in result.stderr
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


def test_list_models_explicit_endpoint_and_key_bypass_route_and_asr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    route_file = tmp_path / "route.json"
    route_file.write_text("not json", encoding="utf-8")
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
            "--llm-route",
            str(route_file),
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


def test_list_models_configured_defaults_and_explicit_endpoint_without_key(
    tmp_path: Path,
) -> None:
    route_file = tmp_path / "route.json"
    write_route(route_file)

    configured = transcribe.resolve_llm_route(
        model=None,
        api_base=None,
        api_key_file=None,
        llm_route=route_file,
        list_models=True,
    )
    explicit = transcribe.resolve_llm_route(
        model=None,
        api_base="http://localhost:9000/v1/",
        api_key_file=None,
        llm_route=tmp_path / "malformed-do-not-read.json",
        list_models=True,
    )

    assert configured.base_url == "https://hera.lan:8443/v1"
    assert configured.api_key == transcribe.DEFAULT_API_KEY
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
    route_file = tmp_path / "route.json"
    write_route(route_file)
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
            "--llm-route",
            str(route_file),
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
    assert route.model == "DeepSeek-V4-Flash-0731-oQ8e-mtp"
    assert output.out == "clean transcript\n"


def test_help_describes_route_without_reading_it(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    xdg_config = home / "xdg"
    route_file = xdg_config / "transcribe/llm-route.json"
    route_file.parent.mkdir(parents=True)
    private_value = "help-must-not-read-this-value"
    route_file.write_text(private_value, encoding="utf-8")

    result = run_cli(
        "--help",
        env={
            **os.environ,
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(xdg_config),
        },
    )

    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert str(route_file) in "".join(output.split())
    assert "--llm-route" in output
    assert "--check-llm-route" in output
    assert "--api-key-file" in output
    assert "explicit" in output.lower()
    assert re.search(r"--api-key(?:\s|$)", output) is None
    assert private_value not in output


@pytest.mark.parametrize("xdg_value", [None, "", "relative/config"])
def test_default_route_ignores_unset_empty_or_relative_xdg_config_home(
    tmp_path: Path, xdg_value: str | None
) -> None:
    home = tmp_path / "home"
    env = {**os.environ, "HOME": str(home)}
    if xdg_value is None:
        env.pop("XDG_CONFIG_HOME", None)
    else:
        env["XDG_CONFIG_HOME"] = xdg_value

    result = run_cli("--help", env=env)

    assert result.returncode == 0
    output = "".join((result.stdout + result.stderr).split())
    assert str(home / ".config/transcribe/llm-route.json") in output


def test_tracked_source_has_no_retired_product_name() -> None:
    retired_name = "prompt" + "deploy"
    result = subprocess.run(
        ["git", "grep", "-n", "-i", retired_name, "--", "."],
        cwd=SCRIPT.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr


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
