from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def build_engine(settings: Settings | None = None) -> Engine:
    config = settings or get_settings()
    connect_args = {"check_same_thread": False} if config.database_url.startswith("sqlite") else {}
    engine = create_engine(config.database_url, connect_args=connect_args)

    if config.database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragmas(dbapi_connection: object, _connection_record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_database(target_engine: Engine | None = None) -> None:
    from app.storage import models  # noqa: F401

    if target_engine is not None:
        Base.metadata.create_all(bind=target_engine)
        return

    project_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(project_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(project_root / "migrations"))
    alembic_config.set_main_option("sqlalchemy.url", get_settings().database_url)
    table_names = set(inspect(engine).get_table_names())
    legacy_tables = {"workspaces", "documents", "chats", "messages"}
    if legacy_tables.issubset(table_names) and "alembic_version" not in table_names:
        command.stamp(alembic_config, "0001")
    command.upgrade(alembic_config, "head")


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
