from app.core.config import get_settings
from app.storage.database import init_database


def main() -> None:
    settings = get_settings()
    settings.ensure_directories()
    init_database()
    print(f"Initialized local database at {settings.database_dir.resolve()}")


if __name__ == "__main__":
    main()
