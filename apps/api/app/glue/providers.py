# Scaffold-owned glue file (KNM-085). Modules register at the markers below; do not edit the marked lines by hand.
# knm:imports
from app.db.provider import database_provider  # knm:module sqlalchemy-db

providers: list[dict[str, object]] = [
    # knm:entries
    {"id": "sqlalchemy-db", "register": database_provider},  # knm:module sqlalchemy-db
    # knm:entries-end
]
