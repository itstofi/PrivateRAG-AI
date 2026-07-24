import argparse
import shutil

from app.core.config import get_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset PrivateRAG AI local development data.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required acknowledgement that uploads, vectors, and chats will be removed.",
    )
    args = parser.parse_args()
    if not args.confirm:
        parser.error("refusing to reset without --confirm")

    settings = get_settings()
    data_root = settings.data_dir.expanduser().resolve()
    targets = [
        settings.upload_dir.expanduser().resolve(),
        settings.vector_dir.expanduser().resolve(),
        settings.database_dir.expanduser().resolve(),
    ]
    for target in targets:
        if not target.is_relative_to(data_root) or target == data_root:
            raise RuntimeError(f"Unsafe reset target: {target}")
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        (target / ".gitkeep").touch()
    print(f"Reset local development data under {data_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
