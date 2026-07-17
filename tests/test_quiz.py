#!/usr/bin/env python3
"""
Tests for the quiz feature and the diagnose-and-explain loop (quiz.py + the
tutor.py helpers that fuse the quiz and the chat tutor together).

Coverage:
  - AI question generation   -> generate_quiz() with a mocked Anthropic client
  - JSON parsing             -> _parse_quiz_json() across clean/dirty/broken input
  - Grading logic            -> grade_quiz()
  - Offline fallback         -> generate_quiz()/generate_hint()/generate_explanation()
                                when there is no key, no library, or an API error
  - Hint guardrail           -> hints nudge but never reveal the answer
  - Explain-more handoff      -> in-depth explanation seeding

No real network or database access happens here — the Anthropic client is always
mocked, so these run fast and offline in CI.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

import quiz
import tutor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(text):
    """
    Build a fake Anthropic client whose messages.create(...) returns a response
    shaped like the real SDK: response.content[0].text == `text`.
    """
    client = MagicMock()
    block = MagicMock()
    block.text = text
    client.messages.create.return_value = MagicMock(content=[block])
    return client


VALID_QUIZ_JSON = json.dumps({
    "questions": [
        {
            "question": "What is buy and hold?",
            "options": ["Buy once and hold", "Day trade", "Short everything", "Rebalance weekly"],
            "correct_index": 0,
            "explanation": "You buy once and hold to the end of your horizon.",
        },
        {
            "question": "What does CAGR measure?",
            "options": ["Worst day", "Annualized compound growth", "Share count", "Broker fees"],
            "correct_index": 1,
            "explanation": "CAGR is the annualized compound growth rate.",
        },
    ]
})


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

class TestParseQuizJson:
    def test_parses_clean_json(self):
        out = quiz._parse_quiz_json(VALID_QUIZ_JSON)
        assert out is not None
        assert len(out) == 2
        assert out[0]["question"] == "What is buy and hold?"
        assert out[0]["correct_index"] == 0
        assert out[1]["correct_index"] == 1

    def test_strips_markdown_fences(self):
        fenced = "```json\n" + VALID_QUIZ_JSON + "\n```"
        out = quiz._parse_quiz_json(fenced)
        assert out is not None and len(out) == 2

    def test_extracts_json_from_surrounding_prose(self):
        noisy = "Sure! Here is your quiz:\n" + VALID_QUIZ_JSON + "\nHope that helps."
        out = quiz._parse_quiz_json(noisy)
        assert out is not None and len(out) == 2

    def test_trims_whitespace_in_fields(self):
        raw = json.dumps({"questions": [{
            "question": "  spaced?  ",
            "options": [" a ", "b", "c", "d"],
            "correct_index": 0,
            "explanation": "  why  ",
        }]})
        out = quiz._parse_quiz_json(raw)
        assert out[0]["question"] == "spaced?"
        assert out[0]["options"][0] == "a"
        assert out[0]["explanation"] == "why"

    def test_missing_explanation_defaults_to_empty(self):
        raw = json.dumps({"questions": [{
            "question": "q?",
            "options": ["a", "b", "c", "d"],
            "correct_index": 2,
        }]})
        out = quiz._parse_quiz_json(raw)
        assert out[0]["explanation"] == ""

    @pytest.mark.parametrize("bad", [
        None,
        "",
        "not json at all",
        "{ not: valid json }",
        json.dumps({"questions": []}),                      # empty list
        json.dumps({"questions": "nope"}),                  # wrong type
        json.dumps({"nope": []}),                           # missing key
        json.dumps({"questions": [{"question": "q?"}]}),    # missing options/index
    ])
    def test_rejects_malformed(self, bad):
        assert quiz._parse_quiz_json(bad) is None

    def test_rejects_wrong_option_count(self):
        raw = json.dumps({"questions": [{
            "question": "q?", "options": ["a", "b", "c"],  # only 3
            "correct_index": 0, "explanation": "",
        }]})
        assert quiz._parse_quiz_json(raw) is None

    @pytest.mark.parametrize("idx", [-1, 4, 99, "0", 1.5, None])
    def test_rejects_bad_correct_index(self, idx):
        raw = json.dumps({"questions": [{
            "question": "q?", "options": ["a", "b", "c", "d"],
            "correct_index": idx, "explanation": "",
        }]})
        assert quiz._parse_quiz_json(raw) is None

    def test_rejects_blank_option(self):
        raw = json.dumps({"questions": [{
            "question": "q?", "options": ["a", "", "c", "d"],
            "correct_index": 0, "explanation": "",
        }]})
        assert quiz._parse_quiz_json(raw) is None


# ---------------------------------------------------------------------------
# AI question generation
# ---------------------------------------------------------------------------

class TestGenerateQuiz:
    def test_returns_ai_questions_on_valid_response(self):
        client = make_client(VALID_QUIZ_JSON)
        with patch.object(quiz, "_get_client", return_value=client):
            questions, source = quiz.generate_quiz(1)
        assert source == "ai"
        assert len(questions) == 2
        # The model was actually consulted.
        client.messages.create.assert_called_once()

    def test_prompt_is_grounded_in_lesson_content(self):
        client = make_client(VALID_QUIZ_JSON)
        with patch.object(quiz, "_get_client", return_value=client):
            quiz.generate_quiz(1)
        sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
        # Lesson 1 is "Buy and Hold" — its grounding text should be present.
        assert "BUY AND HOLD" in sent
        assert "JSON" in sent  # strict-format instruction survived


# ---------------------------------------------------------------------------
# Offline fallback
# ---------------------------------------------------------------------------

class TestOfflineFallback:
    def test_no_client_uses_fallback(self):
        with patch.object(quiz, "_get_client", return_value=None):
            questions, source = quiz.generate_quiz(1)
        assert source == "fallback"
        assert questions == quiz.FALLBACK_QUIZZES[1]

    def test_missing_library_uses_fallback(self):
        with patch.object(quiz, "_get_client", return_value="no_library"):
            questions, source = quiz.generate_quiz(1)
        assert source == "fallback"

    def test_api_error_falls_back(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("network down")
        with patch.object(quiz, "_get_client", return_value=client):
            questions, source = quiz.generate_quiz(1)
        assert source == "fallback"

    def test_unparseable_response_falls_back(self):
        client = make_client("this is not json")
        with patch.object(quiz, "_get_client", return_value=client):
            questions, source = quiz.generate_quiz(1)
        assert source == "fallback"

    def test_unknown_lesson_without_fallback_returns_none(self):
        with patch.object(quiz, "_get_client", return_value=None):
            questions, source = quiz.generate_quiz(999)
        assert questions is None and source is None

    def test_fallback_quizzes_are_well_formed(self):
        # The safety net must itself pass the same validation the parser enforces.
        for lesson_id, qs in quiz.FALLBACK_QUIZZES.items():
            for q in qs:
                assert len(q["options"]) == 4
                assert 0 <= q["correct_index"] < 4
                assert q["question"] and q["explanation"]


# ---------------------------------------------------------------------------
# Grading logic
# ---------------------------------------------------------------------------

class TestGradeQuiz:
    questions = [
        {"correct_index": 0},
        {"correct_index": 1},
        {"correct_index": 2},
    ]

    def test_all_correct(self):
        r = quiz.grade_quiz(self.questions, [0, 1, 2])
        assert r["correct_count"] == 3
        assert r["total"] == 3
        assert r["score_percent"] == 100
        assert all(item["is_correct"] for item in r["results"])

    def test_all_wrong(self):
        r = quiz.grade_quiz(self.questions, [1, 2, 0])
        assert r["correct_count"] == 0
        assert r["score_percent"] == 0

    def test_partial_score_rounds(self):
        # 2/3 -> 67%
        r = quiz.grade_quiz(self.questions, [0, 1, 0])
        assert r["correct_count"] == 2
        assert r["score_percent"] == 67

    def test_unanswered_counts_wrong(self):
        r = quiz.grade_quiz(self.questions, [0, None, 2])
        assert r["correct_count"] == 2
        assert r["results"][1]["is_correct"] is False
        assert r["results"][1]["selected"] is None

    def test_short_answer_list_is_tolerated(self):
        # Only one answer provided for three questions.
        r = quiz.grade_quiz(self.questions, [0])
        assert r["correct_count"] == 1
        assert r["results"][2]["selected"] is None

    def test_empty_quiz_does_not_divide_by_zero(self):
        r = quiz.grade_quiz([], [])
        assert r["total"] == 0
        assert r["score_percent"] == 0

    def test_results_preserve_order_and_indices(self):
        r = quiz.grade_quiz(self.questions, [0, 0, 2])
        assert [item["index"] for item in r["results"]] == [0, 1, 2]
        assert r["results"][0]["correct_index"] == 0


# ---------------------------------------------------------------------------
# Hint generation (nudge without revealing)
# ---------------------------------------------------------------------------

class TestGenerateHint:
    q = {
        "question": "What does CAGR measure?",
        "options": ["Worst day", "Annualized compound growth", "Shares", "Fees"],
        "correct_index": 1,
    }

    def test_offline_returns_safe_hint(self):
        with patch.object(tutor, "_get_client", return_value=None):
            hint = tutor.generate_hint(self.q["question"], 1, options=self.q["options"])
        assert hint == tutor._OFFLINE_HINT

    def test_offline_hint_never_reveals_an_option(self):
        # The static offline hint must not contain any of the answer options.
        with patch.object(tutor, "_get_client", return_value=None):
            hint = tutor.generate_hint(self.q["question"], 1, options=self.q["options"])
        for opt in self.q["options"]:
            assert opt.lower() not in hint.lower()

    def test_online_returns_model_text(self):
        client = make_client("Think about what 'annualized' implies over many years.")
        with patch.object(tutor, "_get_client", return_value=client):
            hint = tutor.generate_hint(self.q["question"], 1, options=self.q["options"])
        assert "annualized" in hint

    def test_system_prompt_forbids_revealing(self):
        client = make_client("a nudge")
        with patch.object(tutor, "_get_client", return_value=client):
            tutor.generate_hint(self.q["question"], 1, options=self.q["options"])
        system = client.messages.create.call_args.kwargs["system"]
        assert "Do NOT reveal" in system

    def test_api_error_falls_back_to_offline(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("boom")
        with patch.object(tutor, "_get_client", return_value=client):
            hint = tutor.generate_hint(self.q["question"], 1, options=self.q["options"])
        assert hint == tutor._OFFLINE_HINT


# ---------------------------------------------------------------------------
# Explanation generation (the 'explain more' handoff)
# ---------------------------------------------------------------------------

class TestGenerateExplanation:
    def test_offline_uses_known_explanation(self):
        with patch.object(tutor, "_get_client", return_value=None):
            text = tutor.generate_explanation(
                "What does CAGR measure?", "Worst day", "Annualized compound growth",
                1, known_explanation="CAGR is the annualized compound growth rate.",
            )
        assert "annualized compound growth rate" in text.lower()

    def test_offline_without_known_explanation_still_helps(self):
        with patch.object(tutor, "_get_client", return_value=None):
            text = tutor.generate_explanation(
                "Q?", "wrong", "right", 1, known_explanation="",
            )
        assert text  # non-empty, actionable guidance
        assert "right" in text

    def test_online_returns_in_depth_text(self):
        client = make_client("CAGR smooths multi-year growth into one annual figure...")
        with patch.object(tutor, "_get_client", return_value=client):
            text = tutor.generate_explanation(
                "What does CAGR measure?", "Worst day", "Annualized compound growth", 1,
            )
        assert "CAGR" in text

    def test_explanation_prompt_is_grounded(self):
        client = make_client("explanation")
        with patch.object(tutor, "_get_client", return_value=client):
            tutor.generate_explanation("Q?", "a", "b", 1)
        system = client.messages.create.call_args.kwargs["system"]
        assert "BUY AND HOLD" in system  # lesson 1 grounding injected

    def test_api_error_falls_back(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("boom")
        with patch.object(tutor, "_get_client", return_value=client):
            text = tutor.generate_explanation(
                "Q?", "a", "b", 1, known_explanation="known reason",
            )
        assert text == "known reason"


# ---------------------------------------------------------------------------
# Seed message builder
# ---------------------------------------------------------------------------

def test_build_missed_question_seed_includes_context():
    seed = tutor.build_missed_question_seed("What is CAGR?", "Worst day", "Annualized growth")
    assert "What is CAGR?" in seed
    assert "Worst day" in seed
    assert "Annualized growth" in seed


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))