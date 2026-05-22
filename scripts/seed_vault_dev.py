import os

import httpx


def main() -> None:
    vault_addr = os.getenv("VAULT_ADDR", "http://localhost:8200")
    vault_token = (
        os.getenv("VAULT_TOKEN")
        or os.getenv("VAULT_ROOT_TOKEN")
        or os.getenv("VAULT_DEV_ROOT_TOKEN_ID")
        or "dev-root-token"
    )

    url = f"{vault_addr}/v1/secret/data/maintainers-copilot"

    payload = {
        "data": {
            "jwt_secret": "local-dev-jwt-secret",
            "database_password": "maintainers-local-password",
            "minio_access_key": "minioadmin",
            "minio_secret_key": "minioadmin",
        }
    }

    response = httpx.post(
        url,
        headers={"X-Vault-Token": vault_token},
        json=payload,
        timeout=5,
    )
    response.raise_for_status()

    print("Seeded Vault dev secrets at secret/data/maintainers-copilot")


if __name__ == "__main__":
    main()