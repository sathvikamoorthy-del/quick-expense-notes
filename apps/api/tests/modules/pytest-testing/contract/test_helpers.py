import os

from fastapi import FastAPI

from tests.helpers import client_for, with_env


def test_with_env_sets_removes_and_restores():
    os.environ["KNM_A"] = "1"
    os.environ.pop("KNM_B", None)
    with with_env(KNM_A=None, KNM_B="2"):
        assert "KNM_A" not in os.environ
        assert os.environ["KNM_B"] == "2"
    assert os.environ["KNM_A"] == "1"
    assert "KNM_B" not in os.environ
    del os.environ["KNM_A"]


def test_with_env_restores_after_an_error():
    os.environ.pop("KNM_C", None)
    try:
        with with_env(KNM_C="x"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert "KNM_C" not in os.environ


def test_client_for_returns_500_instead_of_raising():
    app = FastAPI()

    @app.get("/boom")
    def boom():
        raise RuntimeError("x")

    assert client_for(app).get("/boom").status_code == 500
