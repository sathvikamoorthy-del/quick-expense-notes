"""Server entry: `python -m app.http.server` or `uvicorn app.http.server:app --reload`."""

import logging

from app.http.app import create_app
from app.http.settings import get_settings

logging.basicConfig(level=get_settings().log_level.upper())
app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.http.server:app",
        host="127.0.0.1",
        port=settings.port,
        reload=settings.is_development,
    )


if __name__ == "__main__":
    run()
