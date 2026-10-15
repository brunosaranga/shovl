import math

from django.core.serializers.json import DjangoJSONEncoder


def storable(value):
    """
    A copy of value that Postgres will accept in a JSON column. Scan results hold text copied
    from the scanned API, and Postgres refuses three things SQLite stores without complaint:
    the NUL character (removed), broken Unicode such as a lone surrogate (replaced with "?"),
    and NaN or infinity (stored as null).
    """
    if isinstance(value, str):
        return value.replace("\x00", "").encode("utf-8", "replace").decode("utf-8")
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {
            (storable(key) if isinstance(key, str) else key): storable(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [storable(item) for item in value]
    return value


class StorableJSONEncoder(DjangoJSONEncoder):
    """Used by Scan.results, so every save is cleaned, whichever code path writes it."""

    def encode(self, o):
        return super().encode(storable(o))
