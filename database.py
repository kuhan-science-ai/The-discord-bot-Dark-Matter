import aiosqlite
import logging
from typing import Any, Dict, List, Optional
import config

logger = logging.getLogger("database")

async def init_db() -> None:
    """Reads schema.sql and sets up database tables."""
    schema_path = config.ROOT_DIR / "schema.sql"
    if not schema_path.exists():
        logger.error(f"Schema file not found at {schema_path}")
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
        
    try:
        async with aiosqlite.connect(config.DB_PATH) as db:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            await db.executescript(schema_sql)
            await db.commit()
        logger.info(f"Database initialized successfully at {config.DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

async def execute(query: str, parameters: tuple = ()) -> None:
    """Executes a query (INSERT, UPDATE, DELETE) and commits changes."""
    try:
        async with aiosqlite.connect(config.DB_PATH) as db:
            await db.execute(query, parameters)
            await db.commit()
    except Exception as e:
        logger.error(f"Database write error executing query '{query}' with params {parameters}: {e}", exc_info=True)
        raise

async def fetchone(query: str, parameters: tuple = ()) -> Optional[Dict[str, Any]]:
    """Retrieves a single row from the database, returned as a dictionary."""
    try:
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, parameters) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    except Exception as e:
        logger.error(f"Database read (fetchone) error: {e}", exc_info=True)
        raise

async def fetchall(query: str, parameters: tuple = ()) -> List[Dict[str, Any]]:
    """Retrieves multiple rows from the database, returned as a list of dictionaries."""
    try:
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, parameters) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Database read (fetchall) error: {e}", exc_info=True)
        raise
