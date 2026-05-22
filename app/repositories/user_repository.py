import os
from typing import Any

import psycopg

DEFAULT_DATABASE_URL = (
    "postgresql://maintainers:maintainers-local-password@localhost:5432/maintainers"
)


class UserRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = (
            database_url
            or os.getenv("DATABASE_URL")
            or DEFAULT_DATABASE_URL
        )

    def create_user(
        self,
        email: str,
        password_hash: str,
        role: str = "user",
    ) -> dict[str, Any]:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (
                        email,
                        password_hash,
                        role
                    )
                    VALUES (
                        %(email)s,
                        %(password_hash)s,
                        %(role)s
                    )
                    RETURNING id, email, role, is_active, created_at
                    """,
                    {
                        "email": email.lower(),
                        "password_hash": password_hash,
                        "role": role,
                    },
                )
                row = cur.fetchone()

            conn.commit()

        user_id, returned_email, returned_role, is_active, created_at = row

        return {
            "id": user_id,
            "email": returned_email,
            "role": returned_role,
            "is_active": is_active,
            "created_at": created_at.isoformat(),
        }

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        email,
                        password_hash,
                        role,
                        is_active,
                        created_at
                    FROM users
                    WHERE email = %(email)s
                    """,
                    {
                        "email": email.lower(),
                    },
                )
                row = cur.fetchone()

        if row is None:
            return None

        user_id, returned_email, password_hash, role, is_active, created_at = row

        return {
            "id": user_id,
            "email": returned_email,
            "password_hash": password_hash,
            "role": role,
            "is_active": is_active,
            "created_at": created_at.isoformat(),
        }