"""RH Sentry lab launcher: fixed loopback binding; never deploy this module."""
from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from server import create_app


def main() -> None:
    secret = os.environ.get("RH_SENTRY_LAB_PASSWORD", "")
    if len(secret) < 16:
        raise SystemExit(
            "Set RH_SENTRY_LAB_PASSWORD to a new local temporary password "
            "of at least 16 characters before starting the lab."
        )
    db_path = Path(os.environ.get(
        "RH_SENTRY_LAB_DB",
        str(Path.home() / ".rh-sentry-lab" / "sentry-lab.sqlite3"),
    )).expanduser().resolve()
    print("RH Sentry LAB only: synthetic data, no real security monitoring.")
    print("Listening on 127.0.0.1:8001; never expose or deploy this lab.")
    uvicorn.run(create_app(db_path, secret), host="127.0.0.1", port=8001, log_level="info")


if __name__ == "__main__":
    main()
