from typing import Any

import streamlit as st


def inject_product_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #152033;
            --muted: #657186;
            --line: #dfe4ec;
            --surface: #ffffff;
            --canvas: #f5f7fa;
            --navy: #101b2d;
            --blue: #2457d6;
            --green: #18794e;
            --amber: #9a6700;
        }
        .stApp { background: var(--canvas); color: var(--ink); }
        [data-testid="stSidebar"] { background: var(--navy); }
        [data-testid="stSidebar"] * { color: #eef3fb; }
        [data-testid="stSidebar"] [data-baseweb="radio"] label {
            padding: .35rem .3rem;
        }
        .block-container { max-width: 1240px; padding-top: 4.5rem; padding-bottom: 4rem; }
        h1, h2, h3 { letter-spacing: -.025em; color: var(--ink); }
        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            padding: 1rem;
            border-radius: .65rem;
        }
        div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface);
        }
        .product-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .product-title { font-size: 1.65rem; font-weight: 700; color: var(--ink); }
        .product-subtitle { color: var(--muted); margin-top: .2rem; }
        .badge-row { display: flex; flex-wrap: wrap; gap: .45rem; justify-content: flex-end; }
        .badge {
            display: inline-block;
            border: 1px solid var(--line);
            border-radius: 999px;
            background: var(--surface);
            color: #34425a;
            font-size: .78rem;
            font-weight: 600;
            padding: .3rem .65rem;
            white-space: nowrap;
        }
        .badge.good { color: var(--green); border-color: #a7d8c1; background: #f0faf5; }
        .badge.warn { color: var(--amber); border-color: #ecd49a; background: #fff9e8; }
        .empty-state {
            text-align: center;
            padding: 2.6rem 1.5rem;
            background: var(--surface);
            border: 1px dashed #c8d0dd;
            border-radius: .75rem;
            color: var(--muted);
        }
        .empty-state strong { color: var(--ink); font-size: 1.05rem; }
        .section-kicker {
            text-transform: uppercase;
            letter-spacing: .08em;
            color: var(--muted);
            font-size: .72rem;
            font-weight: 700;
            margin-bottom: .25rem;
        }
        @media (max-width: 760px) {
            .product-header { display: block; }
            .badge-row { justify-content: flex-start; margin-top: .8rem; }
            .block-container {
                padding-top: 4rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def product_header(status: dict[str, Any] | None) -> None:
    ollama = (status or {}).get("ollama", {})
    connected = bool(ollama.get("connected"))
    active_chunks = (status or {}).get("vector_store", {}).get("active_chunk_count", 0)
    ollama_badge = (
        '<span class="badge good">Ollama connected</span>'
        if connected
        else '<span class="badge warn">Ollama offline</span>'
    )
    st.markdown(
        f"""
        <div class="product-header">
          <div>
            <div class="product-title">PrivateRAG AI</div>
            <div class="product-subtitle">
              Local document intelligence with grounded source citations.
            </div>
          </div>
          <div class="badge-row">
            <span class="badge good">Local &amp; private</span>
            {ollama_badge}
            <span class="badge">{active_chunks} active chunks</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_intro(kicker: str, title: str, description: str) -> None:
    st.markdown(f'<div class="section-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.header(title)
    st.caption(description)


def empty_state(title: str, message: str) -> None:
    st.markdown(
        f'<div class="empty-state"><strong>{title}</strong><br><br>{message}</div>',
        unsafe_allow_html=True,
    )


def onboarding(status: dict[str, Any] | None, has_workspaces: bool) -> None:
    ollama = (status or {}).get("ollama", {})
    issues: list[str] = []
    if not ollama.get("connected"):
        issues.append("Start Ollama with `ollama serve`.")
    elif not ollama.get("embedding_model_available"):
        issues.append("Install the configured embedding model with `ollama pull nomic-embed-text`.")
    if not has_workspaces:
        issues.append(
            "Create your first workspace, then upload a fictional sample or private file."
        )
    if issues:
        with st.expander("First-run checklist", expanded=True):
            for index, issue in enumerate(issues, start=1):
                st.markdown(f"**{index}.** {issue}")
