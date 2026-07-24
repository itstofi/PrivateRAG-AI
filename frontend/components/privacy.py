import streamlit as st


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
