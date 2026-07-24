from typing import Any

import streamlit as st


def render_citations(citations: list[dict[str, Any]]) -> None:
    if not citations:
        return
    st.markdown(f"**Sources · {len(citations)}**")
    for citation in citations:
        page = f" · page {citation['page_number']}" if citation.get("page_number") else ""
        section = f" · {citation['section']}" if citation.get("section") and not page else ""
        score = float(citation.get("relevance_score", 0))
        with st.expander(
            f"{citation['index']}. {citation['source_filename']}{page}{section} · "
            f"{score:.0%} semantic match"
        ):
            st.caption(
                f"Chunk {citation.get('chunk_number', 'n/a')} · "
                f"ID {citation.get('chunk_id', 'n/a')}"
            )
            st.write(citation.get("excerpt", ""))
            st.progress(
                min(max(score, 0.0), 1.0),
                text=f"Semantic similarity {score:.1%}",
            )


def render_conflicts(conflicts: list[dict[str, Any]]) -> None:
    if not conflicts:
        return
    with st.container(border=True):
        st.warning("Potentially conflicting values were found in the retrieved sources.")
        for conflict in conflicts:
            st.caption(
                f"{conflict['source_a']} ({', '.join(conflict['values_a'])}) vs "
                f"{conflict['source_b']} ({', '.join(conflict['values_b'])})"
            )
