import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Maintainers Copilot", layout="wide")
st.title("Maintainers Copilot")
st.caption("Internal pandas maintainer chat, memory inspector, and widget configuration.")

tab_chat, tab_widget, tab_memory = st.tabs(["Chat", "Widget Config", "Memory"])


def call_chat_api(message: str, conversation_id: str) -> dict:
    response = httpx.post(
        f"{API_URL}/chat",
        json={
            "message": message,
            "conversation_id": conversation_id,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()

with tab_chat:
    st.subheader("Pandas Maintainer Chat")
    st.write(
        "Ask about pandas issues, maintainer context, API behavior, docs gaps, "
        "or previous resolved issues."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = "streamlit-local-pandas"

    for chat_message in st.session_state.messages:
        with st.chat_message(chat_message["role"]):
            st.markdown(chat_message["content"])

    user_message = st.chat_input("Ask about pandas maintainer context...")

    if user_message:
        st.session_state.messages.append(
            {"role": "user", "content": user_message}
        )

        with st.chat_message("user"):
            st.markdown(user_message)

        with st.chat_message("assistant"):
            with st.spinner("Searching pandas issue corpus..."):
                try:
                    result = call_chat_api(
                        user_message,
                        st.session_state.conversation_id,
                    )
                    answer = result.get("answer", "")
                    sources = result.get("sources", [])

                    st.markdown(answer)
                    st.caption(f"Conversation ID: `{result.get('conversation_id')}`")

                    if sources:
                        with st.expander("Sources"):
                            for source in sources:
                                st.markdown(f"**{source.get('title', 'Untitled')}**")
                                st.markdown(f"[Open source issue]({source.get('source_url', '')})")
                                st.markdown(f"Score: `{source.get('score')}`")

                                metadata = source.get("metadata", {})
                                issue_number = metadata.get("issue_number")
                                labels = metadata.get("labels", [])

                                if issue_number:
                                    st.markdown(f"Issue: `#{issue_number}`")

                                if labels:
                                    st.markdown(f"Labels: `{', '.join(labels)}`")

                                st.divider()

                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer}
                    )

                except Exception as exc:
                    error_message = f"Chat API failed: {exc}"
                    st.error(error_message)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_message}
                    )


with tab_widget:
    st.subheader("Widget Configuration")
    widget_id = st.text_input("Widget ID", value="local-pandas")

    snippet = (
        f'<script src="http://localhost:8000/widget.js" '
        f'data-widget-id="{widget_id}"></script>'
    )

    st.code(snippet, language="html")
    st.info("Full database-backed widget editing belongs in app/services/widget_service.py.")

with tab_memory:
    st.subheader("Memory Inspector")

    conversation_id = st.text_input(
        "Conversation ID",
        value=st.session_state.get("conversation_id", "streamlit-local-pandas"),
    )

    if st.button("Load long-term memory"):
        try:
            response = httpx.get(
                f"{API_URL}/chat/memory/{conversation_id}",
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            st.metric("Audit log rows", data.get("audit_count", 0))

            memories = data.get("memories", [])

            if not memories:
                st.info("No long-term memories found for this conversation.")
            else:
                for memory in memories:
                    st.markdown(f"### Memory #{memory.get('id')}")
                    st.markdown(f"**Type:** `{memory.get('memory_type')}`")
                    st.markdown(f"**Actor:** `{memory.get('actor')}`")
                    st.markdown(f"**Created:** `{memory.get('created_at')}`")
                    st.markdown(memory.get("content", ""))
                    st.divider()

        except Exception as exc:
            st.error(f"Failed to load memory: {exc}")