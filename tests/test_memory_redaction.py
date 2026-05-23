from app.infra.redaction import redact


def test_memory_content_is_redacted_before_storage() -> None:
    raw_memory = "remember that token=ghp_abcdefghijklmnopqrstuvwxyz123456 should never leak"
    redacted = redact(raw_memory)

    assert "ghp_" not in redacted
    assert "[REDACTED]" in redacted


def test_memory_metadata_is_redacted_before_storage() -> None:
    raw_metadata = {
        "source": "manual-test",
        "debug": "api_key=sk-abcdefghijklmnopqrstuvwxyz123456",
    }

    redacted = redact(raw_metadata)
    as_text = str(redacted)

    assert "sk-" not in as_text
    assert "[REDACTED]" in as_text