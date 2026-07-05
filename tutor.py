"""
tutor.py — AI Tutor for the JRG Financial Solutions learning platform.

What this does:
- Adds a chat-based tutor that answers investing questions in plain language.
- The tutor is *grounded* in our own lesson content (a simple RAG approach):
  whatever lesson the user currently has open in the Learn tab is injected into
  the prompt, so answers stay tied to the curriculum instead of general knowledge.
- Guardrails keep it educational: it explains concepts but does NOT give
  personalized financial advice or buy/sell recommendations.

The Anthropic API is ONLY called when the user submits a message (via the chat
box). It never fires on its own or on the app's auto-refresh.
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load ANTHROPIC_API_KEY from the .env file in the project root.
load_dotenv()

# Cheapest current model — plenty for a tutor. To use a smarter (pricier) model,
# swap this for "claude-sonnet-4-6".
MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Lesson content for grounding (the "retrieval" source).
#
# The lessons live as Python/markdown inside learn.py, so we keep a plain-text
# version of each lesson here for the tutor to read. When a new lesson is added
# to learn.py, add a matching entry here keyed by the same lesson id.
# ---------------------------------------------------------------------------
LESSON_CONTEXT = {
    1: """
LESSON 1 — BUY AND HOLD

The concept:
Buy a stock or index once, do nothing, and sell at the end of your time horizon.
No timing, no signals, no rebalancing. It is the baseline strategy — every more
complex strategy must beat buy-and-hold after costs and taxes to be worth it.

Why it works (the math):
Stock prices roughly follow Geometric Brownian Motion. The expected log-return
grows over time because of equity drift, and short-term random noise averages out
over long horizons. CAGR (Compound Annual Growth Rate) summarizes the whole
holding period in one number: CAGR = (V_end / V_start)^(1/T) - 1, where T is years.
The S&P 500's historical CAGR is roughly 10% nominal (~7% after inflation).

Key metrics introduced:
- CAGR: annualized compound growth rate.
- Max Drawdown: the worst peak-to-trough decline; the main measure of risk/pain.
- Sharpe Ratio: return per unit of risk (above 1.0 is generally considered good).

Key takeaways:
1. Buy and hold is the benchmark every other strategy is measured against.
2. Time in the market beats timing the market — drift compounds daily.
3. Max drawdown is the real cost: you may watch a 30-50% drop and must hold.
""",
}


def _build_system_prompt(lesson_id):
    """
    Build the system prompt: guardrails + the current lesson's content (if any).
    This is the 'system prompt and guardrails' deliverable.
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

    lesson_text = LESSON_CONTEXT.get(lesson_id)
    if lesson_text:
        guardrails += (
            "\n\nThe user is currently viewing this lesson. Base your answers on it "
            "when relevant:\n" + lesson_text
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

    # Which lesson is the user currently on? (Set by the Learn tab.)
    current_lesson = st.session_state.get("learn_lesson")
    if current_lesson and current_lesson in LESSON_CONTEXT:
        st.info(f"Context: answering based on Lesson {current_lesson}.")
    else:
        st.info("Context: general investing questions (open a lesson for grounded answers).")

    # Conversation history lives in session state so it survives reruns.
    if "tutor_messages" not in st.session_state:
        st.session_state.tutor_messages = []

    # Render the conversation so far.
    for msg in st.session_state.tutor_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input — the API is ONLY called when the user submits here.
    user_input = st.chat_input("Ask the tutor a question...")
    if user_input:
        # Show and store the user's message.
        st.session_state.tutor_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

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

    # Let the user reset the conversation.
    if st.session_state.tutor_messages:
        if st.button("Clear conversation"):
            st.session_state.tutor_messages = []
            st.rerun()
