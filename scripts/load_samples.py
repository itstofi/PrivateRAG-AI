import mimetypes
from pathlib import Path

import httpx

from app.core.config import get_settings


def main() -> int:
    settings = get_settings()
    base_url = settings.api_base_url
    try:
        workspaces = httpx.get(f"{base_url}/api/workspaces", timeout=10, trust_env=False)
        workspaces.raise_for_status()
        workspace = next(
            (item for item in workspaces.json() if item["name"] == "Fictional Samples"),
            None,
        )
        if workspace is None:
            response = httpx.post(
                f"{base_url}/api/workspaces",
                json={"name": "Fictional Samples"},
                timeout=10,
                trust_env=False,
            )
            response.raise_for_status()
            workspace = response.json()
        for path in sorted(Path("sample_documents").glob("*")):
            if path.suffix.lower() not in {".pdf", ".docx", ".txt", ".md"}:
                continue
            with path.open("rb") as sample:
                response = httpx.post(
                    f"{base_url}/api/documents/upload",
                    data={"workspace_id": workspace["id"]},
                    files={
                        "file": (
                            path.name,
                            sample,
                            mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                        )
                    },
                    timeout=300,
                    trust_env=False,
                )
            if response.status_code == 409:
                print(f"Skipped duplicate: {path.name}")
            else:
                response.raise_for_status()
                print(f"Indexed: {path.name}")
    except httpx.HTTPError as exc:
        print(f"Could not load samples through {base_url}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
