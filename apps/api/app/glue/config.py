# Scaffold-owned glue file (KNM-085). Modules register at the markers below; do not edit the marked lines by hand.
# knm:imports

config: list[dict[str, object]] = [
    # knm:entries
    {"key": "PORT", "default": "8000"},  # knm:module fastapi
    {"key": "DATABASE_URL", "default": "file:./data/app.db"},  # knm:module sqlalchemy-db
    {"key": "JWT_SECRET", "default": ""},  # knm:module jwt-auth
    {"key": "CACHE_TTL_SECONDS", "default": "30"},  # knm:module memory-cache
    # knm:entries-end
]
