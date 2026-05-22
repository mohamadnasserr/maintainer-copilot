import httpx

from app.infra.config import Settings


def require_vault(settings: Settings) -> None:
    if settings.app_env == "test":
        return
    try:
        response = httpx.get(f"{settings.vault_addr}/v1/sys/health", timeout=2)
    except httpx.HTTPError as exc:
        raise RuntimeError("Vault is unreachable; refusing to boot") from exc
    if response.status_code not in {200, 429, 472, 473, 501, 503}:
        raise RuntimeError("Vault health check failed; refusing to boot")

