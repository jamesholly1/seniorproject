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


# ---------------------------------------------------------------------------
# Diagnose-and-explain loop.
#
# These helpers are what tie the quiz and the chat tutor together:
#   - generate_hint(): while answering, nudge a stuck user toward the concept
#     WITHOUT revealing which option is correct (Socratic hint).
#   - generate_explanation(): after a wrong answer, explain the underlying
#     concept in depth so the learner understands *why*, then they can ask
#     follow-ups in the chat.
#
# Both degrade gracefully offline (no key / no library / API error) so the
# quiz remains usable during a live demo.
# ---------------------------------------------------------------------------

# A safe, non-revealing hint to use when the API is unavailable. It never names
# an option, so it can never give the answer away.
_OFFLINE_HINT = (
    "Hint: re-read the lesson's key takeaways and focus on the exact wording of "
    "the question. Rule out the options that describe a different idea, then keep "
    "the one that matches the definition you learned."
)


def _hint_system_prompt(lesson_id):
    """
    System prompt for a Socratic hint. The hard rule is: nudge, do NOT reveal.
    """
    rules = (
        "You are the AI tutor for JRG Financial Solutions. A learner is taking a "
        "multiple-choice quiz and is stuck on a question.\n\n"
        "Give exactly ONE short hint (2-3 sentences) that nudges them to reason it "
        "out for themselves.\n\n"
        "STRICT RULES (never break these):\n"
        "- Do NOT reveal or restate the correct option.\n"
        "- Do NOT say 'the answer is...' or point to a specific letter/number.\n"
        "- Instead, point them at the underlying concept or the part of the lesson "
        "to think about, and suggest how to eliminate options that don't fit.\n"
        "- Stay educational and encouraging. No financial advice."
    )
    lesson_text = LESSON_CONTEXT.get(lesson_id)
    if lesson_text:
        rules += "\n\nRelevant lesson content to ground your hint:\n" + lesson_text
    return rules


def _explain_system_prompt(lesson_id):
    """
    System prompt for an in-depth explanation of a missed question. Here we DO
    want the full concept (the learner has already seen the correct answer).
    """
    rules = (
        "You are the AI tutor for JRG Financial Solutions. A learner just answered a "
        "quiz question incorrectly and wants to understand the concept behind it.\n\n"
        "Explain the UNDERLYING CONCEPT in depth and plain language — not just the "
        "fact that one option was right. Help them see why their answer was a common "
        "misunderstanding and how to reason about it next time. Use a short example "
        "if it helps. End by inviting a follow-up question.\n\n"
        "RULES:\n"
        "- Educational only. No personalized financial advice or buy/sell calls.\n"
        "- Ground the explanation in the lesson content when relevant.\n"
        "- Be honest if the lesson doesn't cover something."
    )
    lesson_text = LESSON_CONTEXT.get(lesson_id)
    if lesson_text:
        rules += "\n\nRelevant lesson content:\n" + lesson_text
    return rules


def _format_options(options):
    """Render an options list as 'A) ...' lines for a prompt. Safe on None."""
    if not options:
        return ""
    letters = "ABCDEFGH"
    lines = [f"{letters[i]}) {opt}" for i, opt in enumerate(options)]
    return "\n".join(lines)


def generate_hint(question, lesson_id, options=None):
    """
    Return a Socratic hint string that nudges the learner without revealing the
    answer. Never raises and never returns None — falls back to a safe offline
    hint if the API is unavailable or errors out.
    """
    client = _get_client()
    if client is None or client == "no_library":
        return _OFFLINE_HINT

    user_msg = f"Quiz question: {question}"
    opts = _format_options(options)
    if opts:
        user_msg += f"\n\nOptions:\n{opts}"
    user_msg += "\n\nGive me a hint — but do not tell me the answer."

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            system=_hint_system_prompt(lesson_id),
            messages=[{"role": "user", "content": user_msg}],
        )
        text = (response.content[0].text or "").strip()
        return text or _OFFLINE_HINT
    except Exception:
        return _OFFLINE_HINT


def build_missed_question_seed(question, user_answer, correct_answer):
    """
    Build the user-visible chat message that seeds the 'explain more' flow. This
    is what gets appended to the tutor conversation so the explanation has clear
    context and the user can naturally ask follow-ups afterward.
    """
    return (
        "I just missed this quiz question and want to understand the concept.\n\n"
        f"Question: {question}\n"
        f"My answer: {user_answer}\n"
        f"Correct answer: {correct_answer}\n\n"
        "Explain the underlying concept in depth so I understand *why* — then I'll "
        "ask follow-ups."
    )


def generate_explanation(question, user_answer, correct_answer, lesson_id,
                         known_explanation=""):
    """
    Return an in-depth explanation of the concept behind a missed question.
    Never raises and never returns None. Offline, it falls back to the quiz's
    own one-line explanation (if available) plus a study nudge.
    """
    client = _get_client()
    if client is None or client == "no_library":
        base = (known_explanation or "").strip()
        if base:
            return (
                f"{base}\n\n(Offline mode: re-read the lesson section this covers and "
                f"notice how it differs from your answer, \"{user_answer}\". Add an "
                "Anthropic API key for a deeper, interactive explanation.)"
            )
        return (
            "Offline mode: the AI tutor needs an Anthropic API key for a full "
            "explanation. For now, re-read the lesson's key takeaways and focus on "
            f"why \"{correct_answer}\" fits the definition better than \"{user_answer}\"."
        )

    seed = build_missed_question_seed(question, user_answer, correct_answer)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=700,
            system=_explain_system_prompt(lesson_id),
            messages=[{"role": "user", "content": seed}],
        )
        text = (response.content[0].text or "").strip()
        if text:
            return text
    except Exception:
        pass

    # Last-resort fallback so the loop never dead-ends.
    base = (known_explanation or "").strip()
    return base or (
        "Sorry — I couldn't reach the tutor just now. Re-read the lesson and focus on "
        f"why \"{correct_answer}\" is the better fit, then try asking again."
    )


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
    live_chat = client is not None and client != "no_library"

    # The quiz still works offline (built-in fallback quizzes), so we never hard
    # return here — we just note that the live chat half needs a key/library.
    if client is None:
        st.warning(
            "No Anthropic API key found — the live chat tutor is disabled, but you "
            "can still take quizzes below. Add ANTHROPIC_API_KEY to your .env file "
            "in the project root and restart for AI tutoring."
        )
    elif client == "no_library":
        st.warning(
            "The 'anthropic' package isn't installed — the live chat tutor is "
            "disabled, but quizzes still work. Run: pip install anthropic"
        )

    # --- Diagnose: the quiz lives at the top of the tutor tab -----------------
    # One feature, one loop: the quiz finds weak spots, then hands missed
    # questions to the chat below for an in-depth explanation + follow-ups.
    from quiz import show_quiz_section
    learn_lesson = st.session_state.get("learn_lesson")
    with st.expander("📝 Quiz yourself (then dig into anything you miss)", expanded=True):
        show_quiz_section(learn_lesson)

    st.markdown("---")
    st.subheader("💬 Chat with the tutor")

    # The chat is grounded on whichever lesson is most relevant: a lesson handed
    # over from the quiz's 'explain more' takes priority, then the open lesson.
    current_lesson = st.session_state.get("tutor_lesson") or learn_lesson
    if current_lesson and current_lesson in LESSON_CONTEXT:
        st.caption(f"Answering based on Lesson {current_lesson}.")
    else:
        st.caption("General investing questions (open or quiz a lesson for grounded answers).")

    # Conversation history lives in session state so it survives reruns.
    if "tutor_messages" not in st.session_state:
        st.session_state.tutor_messages = []

    # If the quiz just handed over a missed question, point the user to it.
    if st.session_state.pop("tutor_just_seeded", False):
        st.success("Added your missed question to the chat below — ask follow-ups to go deeper.")

    if not st.session_state.tutor_messages:
        st.info(
            "Miss a quiz question above and tap **Explain more**, or just ask anything "
            "about the lessons here."
        )

    # Render the conversation so far.
    for msg in st.session_state.tutor_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input — the API is ONLY called when the user submits here.
    user_input = st.chat_input(
        "Ask the tutor a question..." if live_chat else "Add an API key to chat with the tutor",
        disabled=not live_chat,
    )
    if user_input and live_chat:
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

    # Let the user reset the conversation (and the handed-over lesson context).
    if st.session_state.tutor_messages:
        if st.button("Clear conversation"):
            st.session_state.tutor_messages = []
            st.session_state.pop("tutor_lesson", None)
            st.rerun()