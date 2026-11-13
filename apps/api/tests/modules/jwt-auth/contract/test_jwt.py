import time

import jwt
import pytest

from app.auth.jwt import AuthConfigError, AuthSettings, verify_token

SECRET = "s" * 40


def settings(**kw):
    return AuthSettings(jwt_secret=kw.pop("jwt_secret", SECRET), **kw)


def token(payload=None, secret=SECRET, alg="HS256"):
    body = {"sub": "u1", "exp": int(time.time()) + 3600, "iat": int(time.time()), **(payload or {})}
    return jwt.encode(body, secret, algorithm=alg)


def test_a_valid_token_gives_user_tenant_and_roles():
    claims = verify_token(token({"tenantId": "t1", "roles": ["admin", "staff"]}), settings())
    assert claims.user_id == "u1"
    assert claims.tenant_id == "t1"
    assert claims.roles == ["admin", "staff"]
    assert claims.claims["sub"] == "u1"


def test_tenant_and_roles_are_optional_and_non_strings_are_dropped():
    claims = verify_token(token({"roles": ["admin", 7, None]}), settings())
    assert claims.tenant_id is None
    assert claims.roles == ["admin"]
    assert verify_token(token({"tenantId": 5, "roles": "admin"}), settings()).roles == []


def test_a_token_in_the_shape_the_node_api_issues_is_accepted():
    now = int(time.time())
    node_style = jwt.encode(
        {"tenantId": "t9", "roles": ["owner"], "sub": "u9", "iat": now, "exp": now + 60}, SECRET, algorithm="HS256"
    )
    claims = verify_token(node_style, settings())
    assert (claims.user_id, claims.tenant_id, claims.roles) == ("u9", "t9", ["owner"])


def test_wrong_secret_expired_and_tampered_tokens_are_rejected():
    for bad in (token(secret="x" * 40), token({"exp": int(time.time()) - 10}), token()[:-2] + "xx"):
        with pytest.raises(jwt.PyJWTError):
            verify_token(bad, settings())


def test_only_hs256_is_accepted():
    unsigned = jwt.encode({"sub": "u1", "exp": int(time.time()) + 60}, None, algorithm="none")
    for bad in (unsigned, token(alg="HS512")):
        with pytest.raises(jwt.PyJWTError):
            verify_token(bad, settings())


def test_expiry_and_subject_are_required():
    no_exp = jwt.encode({"sub": "u1"}, SECRET, algorithm="HS256")
    no_sub = jwt.encode({"exp": int(time.time()) + 60}, SECRET, algorithm="HS256")
    empty_sub = token({"sub": ""})
    for bad in (no_exp, no_sub, empty_sub):
        with pytest.raises(jwt.PyJWTError):
            verify_token(bad, settings())


def test_issuer_and_audience_are_checked_only_when_configured():
    assert verify_token(token({"iss": "x", "aud": "y"}), settings()).user_id == "u1"
    with pytest.raises(jwt.PyJWTError):
        verify_token(token({"iss": "other"}), settings(jwt_issuer="me"))
    with pytest.raises(jwt.PyJWTError):
        verify_token(token({"aud": "other"}), settings(jwt_audience="api"))
    assert (
        verify_token(token({"iss": "me", "aud": "api"}), settings(jwt_issuer="me", jwt_audience="api")).user_id == "u1"
    )


def test_a_missing_or_short_secret_fails_closed():
    for secret in ("", "short"):
        with pytest.raises(AuthConfigError):
            verify_token(token(), settings(jwt_secret=secret))
