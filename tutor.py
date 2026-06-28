"""
tutor.py — AI Tutor for the JRG Financial Solutions learning platform.

What this does:
- Adds a chat-based tutor that answers investing questions in plain language.
- The tutor is *grounded* in our own lesson content (a simple RAG approach):
  whatever lesson the user currently has open in the Learn tab is read from the
  database and injected into the prompt, so answers stay tied to the curriculum
  instead of general knowledge.
- Conversations are persisted to the database (ai_conversations / ai_messages)
  so chat history survives reruns and logins, and ties to a user and a lesson.
- Guardrails keep it educational: it explains concepts but does NOT give
  personalized financial advice or buy/sell recommendations.

The Anthropic API is ONLY called when the user submits a message (via the chat
box). It never fires on its own or on the app's auto-refresh.
"""

import os
import streamlit as st
from dotenv import load_dotenv

from database import (
    get_lesson,
    create_conversation,
    add_message,
    get_conversation_messages,
    get_user_conversations,
)

# Load ANTHROPIC_API_KEY from the .env file in the project root.
load_dotenv()

# Cheapest current model — plenty for a tutor. To use a smarter (pricier) model,
# swap this for "claude-sonnet-4-6".
MODEL = "claude-haiku-4-5-20251001"


def _build_system_prompt(lesson_id):
    """
    Build the system prompt: guardrails + the current lesson's content (if any).
    Lesson content is read from the database so there is one source of truth.
    """
    guardrails = (
        "You are the AI tutor for JRG Financial Solutions, a platform that teaches "
        "young adults the basics of investing and quantitative trading strategies.\n\n"
        "YOUR JOB:\n"
        "- Explain investing and quant concepts in plain, beginner-friendly language.\n"
        "- Keep answers concise and clear. Use short examples when helpful.\n"
        "- When the user is on a lesson, ground your answers in that lesson's content.\n"
        "- You may quiz the user on the current lesson if they ask you to.\n\n"
        "STRICT RULES (do not break these):\n"
        "- You are an educational tutor, NOT a financial advisor.\n"
        "- Never give personalized financial advice, buy/sell recommendations, or "
        "price predictions. If asked what to buy/sell or whether something is a good "
        "investment, explain the relevant concept instead and remind the user you are "
        "here to teach, not to advise.\n"
        "- Stay on educational topics about investing, markets, and the lessons. If a "
        "question is unrelated, gently steer back to the learning material.\n"
        "- If you are unsure or the lesson doesn't cover something, say so honestly."
    )

    lesson = get_lesson(lesson_id) if lesson_id else None
    if lesson:
        lesson_text = lesson.get("content") or lesson.get("summary") or ""
        guardrails += (
            f'\n\nThe user is currently viewing the lesson titled "{lesson["title"]}". '
            "Base your answers on it when relevant:\n" + lesson_text
        )
    else:
        guardrails += (
            "\n\nThe user is not currently inside a specific lesson. Answer general "
            "beginner investing questions while following the rules above."
        )

    return guardrails


def _get_client():
    """
    Create the Anthropic client. Returns None if the key or library is missing,
    so the app shows a friendly message instead of crashing.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return "no_library"
    return Anthropic(api_key=api_key)


def _load_persisted_conversation(user_id):
    """
    On first open this session, pull the user's most recent conversation out of
    the database so their history is there waiting for them. Sets
    tutor_conversation_id and tutor_messages in session_state.
    """
    convos = get_user_conversations(user_id)
    if convos:
        conversation_id = convos[0]["conversation_id"]
        st.session_state.tutor_conversation_id = conversation_id
        st.session_state.tutor_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in get_conversation_messages(conversation_id)
            if m["role"] in ("user", "assistant")
        ]
    else:
        st.session_state.tutor_conversation_id = None
        st.session_state.tutor_messages = []


def show_tutor_tab():
    """
    Render the AI Tutor chat tab.
    """
    st.header("🤖 AI Tutor")
    st.caption(
        "Ask questions about the lessons in plain language. "
        "The tutor explains concepts — it does not give financial advice."
    )

    client = _get_client()
    if client is None:
        st.warning(
            "No Anthropic API key found. Add ANTHROPIC_API_KEY to your .env file "
            "in the project root, then restart the app."
        )
        return
    if client == "no_library":
        st.warning("The 'anthropic' package isn't installed. Run: pip install anthropic")
        return

    user_id = st.session_state.get("user_id")

    # Which lesson is the user currently on? (Set by the Learn tab; a lesson_id.)
    current_lesson = st.session_state.get("learn_lesson")
    lesson = get_lesson(current_lesson) if current_lesson else None
    if lesson:
        st.info(f"Context: answering based on the lesson \"{lesson['title']}\".")
    else:
        st.info("Context: general investing questions (open a lesson for grounded answers).")

    # Load any persisted conversation once per session (only when logged in).
    if user_id and "tutor_conversation_id" not in st.session_state:
        _load_persisted_conversation(user_id)
    if "tutor_messages" not in st.session_state:
        st.session_state.tutor_messages = []
    if "tutor_conversation_id" not in st.session_state:
        st.session_state.tutor_conversation_id = None

    # Render the conversation so far.
    for msg in st.session_state.tutor_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input — the API is ONLY called when the user submits here.
    user_input = st.chat_input("Ask the tutor a question...")
    if user_input:
        # Start a persisted conversation on the first message (logged-in users).
        if user_id and st.session_state.tutor_conversation_id is None:
            st.session_state.tutor_conversation_id = create_conversation(
                user_id, title=user_input[:60], lesson_id=current_lesson
            )

        # Show and store the user's message.
        st.session_state.tutor_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        if st.session_state.tutor_conversation_id:
            add_message(st.session_state.tutor_conversation_id, "user", user_input)

        # Call Claude with the guardrails + lesson context and full history.
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = client.messages.create(
                        model=MODEL,
                        max_tokens=700,
                        system=_build_system_prompt(current_lesson),
                        messages=st.session_state.tutor_messages,
                    )
                    answer = response.content[0].text
                except Exception as e:
                    answer = f"Sorry, something went wrong reaching the tutor: {e}"
            st.markdown(answer)

        # Store the assistant's reply.
        st.session_state.tutor_messages.append({"role": "assistant", "content": answer})
        if st.session_state.tutor_conversation_id:
            add_message(st.session_state.tutor_conversation_id, "assistant", answer)

    # Let the user start a fresh conversation.
    if st.session_state.tutor_messages:
        if st.button("New conversation"):
            st.session_state.tutor_messages = []
            st.session_state.tutor_conversation_id = None
            st.rerun()
