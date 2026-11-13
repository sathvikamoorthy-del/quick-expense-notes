from app.http.settings import Settings


def test_defaults():
    s = Settings()
    assert s.port == 8000
    assert s.is_development
    assert s.cors_origin_list == []


def test_reads_the_environment(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("PORT", "9001")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example.com, https://b.example.com")
    s = Settings()
    assert not s.is_development
    assert s.port == 9001
    assert s.cors_origin_list == ["https://a.example.com", "https://b.example.com"]
