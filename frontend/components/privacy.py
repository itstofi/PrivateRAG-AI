from typing import Any

import streamlit as st


def format_storage_location(storage_location: str) -> str:
    """Describe local storage without exposing an absolute user or host path."""
    normalized = storage_location.strip().replace("\\", "/").rstrip("/")
    is_windows_root = len(normalized) == 2 and normalized[1] == ":"
    directory_name = "data" if not normalized or is_windows_root else normalized.rsplit("/", 1)[-1]
    return f"Local data directory · {directory_name}"


def sanitize_system_status(system_status: dict[str, Any]) -> dict[str, Any]:
    """Return display-safe status data without mutating the API response."""
    sanitized = dict(system_status)
    if "storage_location" in sanitized:
        sanitized["storage_location"] = format_storage_location(
            str(sanitized["storage_location"] or "")
        )
    return sanitized


def privacy_panel() -> None:
    with st.container(border=True):
        st.markdown("**Privacy mode active**")
        st.caption("Application data stays inside the configured local storage boundary.")
        st.markdown(
            "Local inference and embeddings  \n"
            "Local documents and chat history  \n"
            "No cloud AI API or analytics  \n"
            "Offline-capable after installation"
        )
