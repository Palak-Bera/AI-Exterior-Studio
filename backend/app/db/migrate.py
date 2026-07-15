"""Ensure SQLite (or other) material table has pricing columns."""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.logging_config import get_logger

logger = get_logger("db.migrate")


def ensure_material_pricing_columns(engine: Engine) -> None:
    """Add rate_inr / unit columns if missing (create_all does not alter existing tables)."""
    insp = inspect(engine)
    if "materials" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("materials")}
    statements: list[str] = []
    if "rate_inr" not in cols:
        statements.append("ALTER TABLE materials ADD COLUMN rate_inr FLOAT DEFAULT 0")
    if "unit" not in cols:
        statements.append("ALTER TABLE materials ADD COLUMN unit VARCHAR(16) DEFAULT 'sqm'")
    if not statements:
        return
    with engine.begin() as conn:
        for sql in statements:
            conn.execute(text(sql))
            logger.info("Migrated materials table: %s", sql)
