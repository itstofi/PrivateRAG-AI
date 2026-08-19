from frontend.components.privacy import format_storage_location, sanitize_system_status


def test_storage_location_hides_absolute_user_path() -> None:
    assert (
        format_storage_location("/Users/example/projects/private-rag/data")
        == "Local data directory · data"
    )


def test_storage_location_handles_windows_and_trailing_separators() -> None:
    assert (
        format_storage_location("C:\\Users\\alice\\PrivateRAG\\data\\")
        == "Local data directory · data"
    )


def test_storage_location_handles_roots_and_empty_values() -> None:
    assert format_storage_location("/") == "Local data directory · data"
    assert format_storage_location("C:\\") == "Local data directory · data"
    assert format_storage_location("") == "Local data directory · data"


def test_system_status_copy_redacts_storage_path() -> None:
    raw = {
        "storage_location": "/Users/example/private-rag/data",
        "ollama": {"connected": True},
    }

    sanitized = sanitize_system_status(raw)

    assert sanitized["storage_location"] == "Local data directory · data"
    assert raw["storage_location"] == "/Users/example/private-rag/data"
