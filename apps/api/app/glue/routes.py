# Scaffold-owned glue file (KNM-085). Modules register at the markers below; do not edit the marked lines by hand.
# knm:imports

from app.entries.routes import mount as mount_entries  # app route (WI-029), not a module

routes: list[dict[str, object]] = [
    # knm:entries
    # knm:entries-end
    {"id": "entries", "mount": mount_entries},
]
