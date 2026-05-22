from app.infra.redaction import redact, redact_for_log


def test_redacts_github_token() -> None:
    raw = "token=ghp_abcdefghijklmnopqrstuvwxyz123456"
    redacted = redact(raw)

    assert "ghp_" not in redacted
    assert "[REDACTED]" in redacted


def test_redacts_openai_style_key() -> None:
    raw = "api_key=sk-abcdefghijklmnopqrstuvwxyz123456"
    redacted = redact(raw)

    assert "sk-" not in redacted
    assert "[REDACTED]" in redacted


def test_redacts_password() -> None:
    raw = "password=supersecret123"
    redacted = redact(raw)

    assert "supersecret123" not in redacted
    assert "[REDACTED]" in redacted


def test_redacts_nested_payload() -> None:
    payload = {
        "message": "authorization: Bearer abcdefghijklmnopqrstuvwxyz123456",
        "metadata": {
            "token": "api_key=sk-abcdefghijklmnopqrstuvwxyz123456",
        },
    }

    redacted = redact(payload)
    as_text = str(redacted)

    assert "Bearer abcdefghijklmnopqrstuvwxyz123456" not in as_text
    assert "sk-" not in as_text
    assert "[REDACTED]" in as_text


def test_redact_for_log_returns_safe_string() -> None:
    payload = {
        "message": "user pasted token=ghp_abcdefghijklmnopqrstuvwxyz123456",
        "password": "password=secret123",
    }

    log_text = redact_for_log(payload)

    assert "ghp_" not in log_text
    assert "secret123" not in log_text
    assert "[REDACTED]" in log_text