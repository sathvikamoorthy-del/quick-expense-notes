"""Small helpers for tests."""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient


def client_for(app: FastAPI) -> TestClient:
    """A client that returns 500 responses instead of raising, so error envelopes can be asserted."""
    return TestClient(app, raise_server_exceptions=False)


@contextmanager
def with_env(**values: str | None) -> Iterator[None]:
    """Sets (or, with None, removes) environment variables and always restores them."""
    old = {k: os.environ.get(k) for k in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
