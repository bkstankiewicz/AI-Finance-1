import uuid
import decimal
from datetime import datetime, date


def to_jsonable(value):
    """Recursively convert UUID/Decimal/datetime/date values into JSON/JSONB-safe primitives"""
    if isinstance(value, dict):
        return {key: to_jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
