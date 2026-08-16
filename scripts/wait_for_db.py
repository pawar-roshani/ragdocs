#!/usr/bin/env python3
"""Poll the database until it accepts connections, then exit 0.

Useful for local scripting outside docker-compose (which already uses a
proper healthcheck); kept as a small standalone utility for CI/dev use.
"""
import sys
import time

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def main(timeout_seconds: int = 30) -> int:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is ready.")
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"Waiting for database... ({exc.__class__.__name__})")
            time.sleep(1)

    print("Timed out waiting for database.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
