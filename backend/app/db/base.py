from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase


def utc_now(*args, **kwargs) -> datetime:
    """
    Returns naive UTC datetime compatible with PostgreSQL TIMESTAMP WITHOUT TIME ZONE (asyncpg) and SQLite.
    Accepts optional args/kwargs so it can be safely used as a SQLAlchemy Column default/onupdate callback.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass
