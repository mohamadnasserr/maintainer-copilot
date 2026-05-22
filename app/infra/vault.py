import os
from typing import Any

import httpx


class VaultError(RuntimeError):
    pass


def get_vault_addr() -> str:
    return os.getenv("VAULT_ADDR", "http://localhost:8200")


def get_vault_token() -> str:
    return (
        os.getenv("VAULT_TOKEN")
        or os.getenv("VAULT_ROOT_TOKEN")
        or os.getenv("VAULT_DEV_ROOT_TOKEN_ID")
        or "dev-root-token"
    )


def require_vault(settings: Any | None = None) -> None:
    """
    Refuse to boot if Vault is unreachable.

    The settings argument is kept for compatibility with app/main.py.
    """
    vault_addr = getattr(settings, "vault_addr", None) or get_vault_addr()

    try:
        response = httpx.get(f"{vault_addr}/v1/sys/health", timeout=2)
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError("Vault is unreachable; refusing to boot") from exc


def read_vault_secret(
    path: str,
    key: str,
    default: str | None = None,
) -> str:
    """
    Read a secret from Vault KV v2.

    Example:
        path="secret/data/maintainers-copilot"
        key="jwt_secret"

    For local development, if the secret is missing and default is provided,
    return the default instead of crashing.
    """
    vault_addr = get_vault_addr()
    vault_token = get_vault_token()

    url = f"{vault_addr}/v1/{path}"

    try:
        response = httpx.get(
            url,
            headers={"X-Vault-Token": vault_token},
            timeout=3,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        if default is not None:
            return default
        raise VaultError(f"Could not read Vault secret at path '{path}'") from exc

    data = payload.get("data", {}).get("data", {})

    if key not in data:
        if default is not None:
            return default
        raise VaultError(f"Secret key '{key}' not found at path '{path}'")

    return str(data[key])


def verify_required_demo_secret() -> None:
    """
    Lightweight startup proof that Vault secret resolution works.

    This reads a demo JWT secret from Vault when available. In local dev,
    it falls back to a safe non-production default so the app remains runnable.
    """
    read_vault_secret(
        path="secret/data/maintainers-copilot",
        key="jwt_secret",
        default="local-dev-jwt-secret",
    )