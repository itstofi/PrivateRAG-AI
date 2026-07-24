from app.storage.database import SessionLocal, init_database
from app.storage.repositories import WorkspaceRepository


def main() -> None:
    init_database()
    with SessionLocal() as session:
        repository = WorkspaceRepository(session)
        existing = next(
            (item for item in repository.list() if item.name == "Fictional Samples"), None
        )
        workspace = existing or repository.create("Fictional Samples")
        print(workspace.id)


if __name__ == "__main__":
    main()
