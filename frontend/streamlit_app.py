import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

# Streamlit executes this file with `frontend/` as the first import path. Add the
# repository root so package imports work both from source and from an installed wheel.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.api_client import ApiClient, ApiError  # noqa: E402
from frontend.components.citations import render_citations, render_conflicts  # noqa: E402
from frontend.components.privacy import privacy_panel  # noqa: E402
from frontend.components.product import (  # noqa: E402
    empty_state,
    inject_product_styles,
    onboarding,
    page_intro,
    product_header,
)

st.set_page_config(
    page_title="PrivateRAG AI",
    page_icon=":material/lock:",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_product_styles()

client = ApiClient(os.getenv("API_BASE_URL", "http://localhost:8000"))


def api(method: str, path: str, *, quiet: bool = False, **kwargs: Any) -> Any:
    try:
        return client.request(method, path, **kwargs)
    except ApiError as exc:
        if not quiet:
            st.error(str(exc))
        return None


def select_workspace(
    workspaces: list[dict[str, Any]], key: str, label: str = "Workspace"
) -> str | None:
    if not workspaces:
        empty_state("No workspaces yet", "Create a workspace to separate documents and chats.")
        return None
    by_name = {item["name"]: item["id"] for item in workspaces}
    selected = st.selectbox(label, list(by_name), key=key)
    return by_name[selected]


def available_models(model_status: dict[str, Any]) -> tuple[list[str], str]:
    default = model_status.get("selected_chat_model", "llama3.2:3b")
    installed = model_status.get("chat_models", model_status.get("models", []))
    return (installed or [default], default)


def chat_view(
    workspaces: list[dict[str, Any]],
    system_status: dict[str, Any] | None,
    model_status: dict[str, Any],
) -> None:
    page_intro(
        "Grounded answers",
        "Chat",
        "Ask questions inside one workspace. Retrieved evidence never crosses "
        "workspace boundaries.",
    )
    if not workspaces:
        empty_state(
            "Create a workspace first",
            "Open Workspaces, create a local collection, then add at least one document.",
        )
        return

    controls, conversation = st.columns([3, 8], gap="large")
    with controls:
        with st.container(border=True):
            st.markdown("**Query context**")
            workspace_id = select_workspace(workspaces, "chat_workspace")
            if not workspace_id:
                return
            model_options, default_model = available_models(model_status)
            default_index = (
                model_options.index(default_model) if default_model in model_options else 0
            )
            model = st.selectbox("Local chat model", model_options, index=default_index)
            selected_workspace = next(item for item in workspaces if item["id"] == workspace_id)
            st.caption(
                f"{selected_workspace['document_count']} documents · "
                f"{selected_workspace['active_chunk_count']} active chunks"
            )

        chats = api("GET", f"/api/chats?workspace_id={workspace_id}") or []
        chat_by_id = {item["id"]: item for item in chats}
        chat_ids = [None, *chat_by_id]
        if "requested_chat_history_id" in st.session_state:
            requested_chat_id = st.session_state.pop("requested_chat_history_id")
            st.session_state.chat_history_id = (
                requested_chat_id if requested_chat_id in chat_ids else None
            )
        elif st.session_state.get("chat_history_id") not in chat_ids:
            st.session_state.chat_history_id = None
        chat_id = st.selectbox(
            "Chat history",
            chat_ids,
            key="chat_history_id",
            format_func=lambda value: (
                "Start a new chat"
                if value is None
                else f"{chat_by_id[value]['title']} · {value[:6]}"
            ),
        )
        selected_title = chat_by_id[chat_id]["title"] if chat_id else "New chat"
        if st.button("New chat", use_container_width=True):
            st.session_state.requested_chat_history_id = None
            st.rerun()

        if chat_id:
            with st.popover("Manage chat", use_container_width=True):
                renamed = st.text_input("Title", value=selected_title, max_chars=160)
                if st.button("Save title", use_container_width=True) and api(
                    "PATCH", f"/api/chats/{chat_id}", json={"title": renamed}
                ):
                    st.rerun()
                exported = api("GET", f"/api/chats/{chat_id}/export", quiet=True)
                st.download_button(
                    "Export Markdown",
                    data=exported or "",
                    file_name=f"chat-{chat_id[:8]}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
                confirm = st.checkbox("I understand this deletes the local chat.")
                if st.button(
                    "Delete chat",
                    disabled=not confirm,
                    type="primary",
                    use_container_width=True,
                ):
                    api("DELETE", f"/api/chats/{chat_id}")
                    st.session_state.requested_chat_history_id = None
                    st.rerun()

    with conversation:
        messages: list[dict[str, Any]] = []
        if chat_id:
            chat = api("GET", f"/api/chats/{chat_id}")
            messages = (chat or {}).get("messages", [])
        if not messages:
            empty_state(
                "Ask your first grounded question",
                "Answers use only indexed evidence. Every supplied source can be expanded below "
                "the response.",
            )
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                render_conflicts(message.get("retrieval_config", {}).get("detected_conflicts", []))
                render_citations(message.get("citations", []))

        ollama = (system_status or {}).get("ollama", {})
        embedding_ready = bool(ollama.get("embedding_model_available"))
        indexed_ready = bool(selected_workspace["active_chunk_count"])
        input_disabled = not ollama.get("connected") or not embedding_ready or not indexed_ready
        if input_disabled:
            reasons = []
            if not ollama.get("connected"):
                reasons.append("Ollama is offline")
            if ollama.get("connected") and not embedding_ready:
                reasons.append("the embedding model is not installed")
            if not indexed_ready:
                reasons.append("this workspace has no indexed chunks")
            st.info("Chat is waiting because " + ", ".join(reasons) + ".")
        question = st.chat_input("Ask a question about this workspace", disabled=input_disabled)
        if not question:
            return

        runtime = api("GET", "/api/settings") or {}
        payload = {
            "workspace_id": workspace_id,
            "question": question,
            "chat_id": chat_id,
            "model": model,
            "retrieval": {
                "top_k": runtime.get("top_k", 5),
                "similarity_threshold": runtime.get("similarity_threshold", 0.25),
                "use_mmr": st.session_state.get("use_mmr", False),
                "max_context_chars": st.session_state.get("max_context_chars", 12000),
                "temperature": runtime.get("temperature", 0.1),
            },
        }
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            answer_placeholder = st.empty()
            answer = ""
            citations: list[dict[str, Any]] = []
            conflicts: list[dict[str, Any]] = []
            new_chat_id = chat_id
            with st.status("Retrieving local evidence…", expanded=False) as stream_status:
                try:
                    for event in client.stream("/api/chat/stream", payload):
                        event_type = event.get("type")
                        if event_type == "metadata":
                            citations = event.get("citations", [])
                            conflicts = event.get("conflicts", [])
                            new_chat_id = event.get("chat_id")
                            stream_status.update(label="Generating with Ollama…")
                        elif event_type == "token":
                            answer += event.get("content", "")
                            answer_placeholder.markdown(answer + "▌")
                        elif event_type == "done":
                            answer = event.get("answer", answer)
                            answer_placeholder.markdown(answer)
                            stream_status.update(label="Answer complete", state="complete")
                        elif event_type == "error":
                            raise ApiError(event.get("error", "The answer stream failed."))
                    render_conflicts(conflicts)
                    render_citations(citations)
                    if new_chat_id and not chat_id:
                        st.session_state.requested_chat_history_id = new_chat_id
                        st.rerun()
                except (ApiError, ValueError) as exc:
                    stream_status.update(label="Answer failed", state="error")
                    answer_placeholder.error(str(exc))


def documents_view(workspaces: list[dict[str, Any]], system_status: dict[str, Any] | None) -> None:
    page_intro(
        "Local ingestion",
        "Documents",
        "Validate, process, reindex, and remove private files from a selected workspace.",
    )
    workspace_id = select_workspace(workspaces, "document_workspace")
    if not workspace_id:
        return

    ollama = (system_status or {}).get("ollama", {})
    embedding_ready = bool(ollama.get("embedding_model_available"))
    with st.container(border=True):
        st.markdown("**Add documents**")
        uploads = st.file_uploader(
            "PDF, DOCX, TXT, or Markdown · maximum size follows local settings",
            type=["pdf", "docx", "txt", "md"],
            accept_multiple_files=True,
        )
        if not embedding_ready:
            st.warning(
                "Install the configured embedding model before indexing. Existing data remains "
                "available for management."
            )
        if st.button(
            "Validate and index",
            type="primary",
            disabled=not uploads or not embedding_ready,
        ):
            progress = st.progress(0.0, text="Preparing local ingestion")
            successes = 0
            for index, upload in enumerate(uploads or [], start=1):
                progress.progress((index - 1) / len(uploads), text=f"Processing {upload.name}")
                result = api(
                    "POST",
                    "/api/documents/upload",
                    data={"workspace_id": workspace_id},
                    files={"file": (upload.name, upload.getvalue(), upload.type)},
                )
                if result and result["summary"]["status"] == "indexed":
                    successes += 1
            progress.progress(1.0, text=f"Indexed {successes} of {len(uploads or [])} files")
            if successes:
                st.success("Local indexing finished.")
                st.rerun()

    documents = api("GET", f"/api/documents?workspace_id={workspace_id}") or []
    st.subheader("Indexed library")
    if not documents:
        empty_state(
            "This workspace is empty",
            "Upload a supported document above. Files, vectors, and metadata stay local.",
        )
        return
    for document in documents:
        with st.container(border=True):
            identity, status_column, actions = st.columns([5, 2, 2])
            identity.markdown(f"**{document['original_filename']}**")
            identity.caption(
                f"{document['file_type'].upper()} · {document['file_size'] / 1024:.1f} KB · "
                f"{document['page_count']} readable pages · {document['chunk_count']} chunks"
            )
            identity.caption(
                f"Embedding model: {document.get('embedding_model') or 'legacy index'}"
            )
            state = document["status"]
            if state == "indexed":
                status_column.success("Indexed")
            elif state == "failed":
                status_column.error("Failed")
            else:
                status_column.info(state.title())
            if document.get("processing_error"):
                status_column.caption(document["processing_error"])

            if actions.button(
                "Reindex",
                key=f"reindex-{document['id']}",
                disabled=not embedding_ready,
                use_container_width=True,
            ):
                with st.spinner(f"Reindexing {document['original_filename']} locally…"):
                    if api("POST", f"/api/documents/{document['id']}/reindex"):
                        st.rerun()
            with actions.popover("Delete", use_container_width=True):
                st.warning("This removes the file, vectors, and document metadata.")
                confirm = st.checkbox(
                    "Confirm local deletion", key=f"confirm-document-{document['id']}"
                )
                if st.button(
                    "Delete permanently",
                    key=f"delete-{document['id']}",
                    disabled=not confirm,
                    type="primary",
                    use_container_width=True,
                ):
                    api("DELETE", f"/api/documents/{document['id']}")
                    st.rerun()
            with st.expander("Technical metadata"):
                st.json(document)


def workspaces_view(workspaces: list[dict[str, Any]]) -> None:
    page_intro(
        "Isolation boundary",
        "Workspaces",
        "Keep unrelated document collections, retrieval results, and conversations separate.",
    )
    created_name = st.session_state.pop("workspace_created", None)
    if created_name:
        st.success(f'Workspace "{created_name}" created.')

    create, guidance = st.columns([5, 4], gap="large")
    with create, st.form("create_workspace", clear_on_submit=True):
        st.markdown("**Create a workspace**")
        name = st.text_input(
            "Name",
            max_chars=100,
            placeholder="For example: Research papers",
        )
        submitted = st.form_submit_button("Create workspace", type="primary")
        if submitted:
            cleaned_name = name.strip()
            if not cleaned_name:
                st.warning("Enter a workspace name before creating it.")
            elif api("POST", "/api/workspaces", json={"name": cleaned_name}):
                st.session_state.workspace_created = cleaned_name
                st.rerun()
    with guidance:
        st.info(
            "Retrieval always applies a workspace metadata filter. Deleting a workspace also "
            "removes its local files, vectors, chats, and messages."
        )

    st.subheader("Local workspaces")
    if not workspaces:
        empty_state(
            "No workspaces created",
            "Create one above to establish the first document isolation boundary.",
        )
        return
    for workspace in workspaces:
        with st.container(border=True):
            title, stats, actions = st.columns([4, 4, 2])
            title.markdown(f"### {workspace['name']}")
            title.caption(f"Workspace ID · {workspace['id']}")
            stat_columns = stats.columns(3)
            stat_columns[0].metric("Documents", workspace["document_count"])
            stat_columns[1].metric(
                "Active chunks",
                workspace["active_chunk_count"],
                help=f"{workspace['chunk_count']} chunks across all embedding models",
            )
            stat_columns[2].metric("Chats", workspace["chat_count"])
            with actions.popover("Manage", use_container_width=True):
                renamed = st.text_input(
                    "Workspace name",
                    value=workspace["name"],
                    key=f"workspace-name-{workspace['id']}",
                )
                if st.button(
                    "Save name",
                    key=f"rename-workspace-{workspace['id']}",
                    use_container_width=True,
                ) and api(
                    "PATCH",
                    f"/api/workspaces/{workspace['id']}",
                    json={"name": renamed},
                ):
                    st.rerun()
                st.divider()
                confirm = st.checkbox(
                    "Delete files, vectors, and chats",
                    key=f"confirm-workspace-{workspace['id']}",
                )
                if st.button(
                    "Delete workspace",
                    key=f"delete-workspace-{workspace['id']}",
                    disabled=not confirm,
                    type="primary",
                    use_container_width=True,
                ):
                    api("DELETE", f"/api/workspaces/{workspace['id']}")
                    st.rerun()


def settings_view(model_status: dict[str, Any]) -> None:
    page_intro(
        "Runtime configuration",
        "Settings",
        "Changes apply to the current API process. Copy final values to .env for persistence.",
    )
    current = api("GET", "/api/settings") or {}
    models_tab, retrieval_tab, ingestion_tab = st.tabs(
        ["Models and Ollama", "Retrieval", "Ingestion"]
    )
    with st.form("settings"):
        with models_tab:
            ollama_url = st.text_input(
                "Ollama URL", value=current.get("ollama_base_url", "http://localhost:11434")
            )
            installed = model_status.get("models", [])
            st.caption(
                "Installed models: " + (", ".join(installed) if installed else "none detected")
            )
            chat_model = st.text_input(
                "Default chat model",
                value=current.get("ollama_chat_model", "llama3.2:3b"),
            )
            embedding_model = st.text_input(
                "Embedding model",
                value=current.get("ollama_embedding_model", "nomic-embed-text"),
            )
            temperature = st.slider(
                "Temperature", 0.0, 2.0, float(current.get("temperature", 0.1)), 0.05
            )
            st.warning(
                "Changing the embedding model activates a separate vector collection. Reindex "
                "documents to make them searchable with the new model."
            )
        with retrieval_tab:
            top_k = st.slider("Top-K sources", 1, 50, int(current.get("top_k", 5)))
            threshold = st.slider(
                "Similarity threshold",
                0.0,
                1.0,
                float(current.get("similarity_threshold", 0.25)),
                0.01,
            )
            use_mmr = st.checkbox(
                "Diversify sources with Maximum Marginal Relevance",
                value=st.session_state.get("use_mmr", False),
            )
            max_context = st.number_input(
                "Maximum context characters",
                1000,
                100000,
                st.session_state.get("max_context_chars", 12000),
            )
        with ingestion_tab:
            chunk_size = st.number_input(
                "Chunk size", 100, 10000, int(current.get("chunk_size", 900))
            )
            overlap = st.number_input(
                "Chunk overlap", 0, 5000, int(current.get("chunk_overlap", 150))
            )
            max_mb = st.number_input(
                "Maximum upload size (MB)",
                1,
                1024,
                int(current.get("max_upload_size_mb", 25)),
            )
            st.caption("Changing chunk settings affects newly indexed or reindexed documents.")
        if st.form_submit_button("Apply runtime settings", type="primary"):
            result = api(
                "PATCH",
                "/api/settings",
                json={
                    "ollama_base_url": ollama_url,
                    "ollama_chat_model": chat_model,
                    "ollama_embedding_model": embedding_model,
                    "temperature": temperature,
                    "top_k": top_k,
                    "similarity_threshold": threshold,
                    "chunk_size": chunk_size,
                    "chunk_overlap": overlap,
                    "max_upload_size_mb": max_mb,
                },
            )
            if result:
                st.session_state.use_mmr = use_mmr
                st.session_state.max_context_chars = max_context
                st.success("Runtime settings applied.")


def status_view(system_status: dict[str, Any] | None) -> None:
    page_intro(
        "Local diagnostics",
        "System health",
        "Inspect each local dependency without hiding model or storage failures.",
    )
    if not system_status:
        empty_state(
            "Local API unavailable",
            "Start the backend with `make run-api`, then refresh this page.",
        )
        return
    ollama = system_status["ollama"]
    vector = system_status["vector_store"]
    cards = st.columns(4)
    cards[0].metric("Ollama", "Connected" if ollama.get("connected") else "Offline")
    cards[1].metric("SQLite", "Ready")
    cards[2].metric("Active vectors", vector.get("active_chunk_count", 0))
    cards[3].metric("Documents", system_status["document_count"])
    with st.container(border=True):
        st.markdown("**Model readiness**")
        chat_ready = ollama.get("chat_model_available", False)
        embedding_ready = ollama.get("embedding_model_available", False)
        first, second = st.columns(2)
        first.success("Default chat model installed") if chat_ready else first.warning(
            "Default chat model unavailable"
        )
        second.success("Embedding model installed") if embedding_ready else second.warning(
            "Embedding model unavailable"
        )
        if not ollama.get("connected"):
            st.code("ollama serve", language="bash")
        elif not embedding_ready:
            st.code("ollama pull nomic-embed-text", language="bash")
    with st.expander("Technical status response"):
        st.json(system_status)
    st.caption(f"Local storage · {system_status['storage_location']}")
    privacy_panel()


with st.sidebar:
    st.markdown("## PrivateRAG AI")
    st.caption("Local document intelligence")
    section = st.radio(
        "Navigation",
        ["Chat", "Documents", "Workspaces", "Settings", "System health"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Data boundary")
    st.markdown("Local files · Local vectors · Local chats")

system_status = api("GET", "/api/status", quiet=True)
model_status = api("GET", "/api/models", quiet=True) or {}
workspaces = api("GET", "/api/workspaces", quiet=True) or []

product_header(system_status)
onboarding(system_status, bool(workspaces))

if section == "Chat":
    chat_view(workspaces, system_status, model_status)
elif section == "Documents":
    documents_view(workspaces, system_status)
elif section == "Workspaces":
    workspaces_view(workspaces)
elif section == "Settings":
    settings_view(model_status)
else:
    status_view(system_status)
