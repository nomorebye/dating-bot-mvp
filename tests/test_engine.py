from datetime import timedelta

from core.engine import generate_proactive, handle_user_message, set_memory_store
from core.memory import MemoryStore, now_utc, parse_iso, to_iso


QUESTION_ENDINGS = ["야", "해", "임", "지", "죠", "니", "냐", "까", "까요", "일까"]


def has_question(text: str) -> bool:
    if "?" in text:
        return True
    return any(text.endswith(ending) for ending in QUESTION_ENDINGS)


def assert_no_questions(bubbles: list[str]) -> None:
    for bubble in bubbles:
        assert not has_question(bubble)


def setup_store(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.db"))
    set_memory_store(store)
    return store


def test_multi_bubble_always(tmp_path):
    setup_store(tmp_path)
    bubbles = handle_user_message("u1", "안녕")
    assert len(bubbles) >= 2


def test_silence_stage2_forbids_questions(tmp_path):
    store = setup_store(tmp_path)
    state = store.load("u1")
    state["last_user_message_at"] = to_iso(now_utc() - timedelta(hours=7))
    store.save("u1", state)

    bubbles = handle_user_message("u1", "안녕")
    assert_no_questions(bubbles)


def test_confession_trigger_changes_stage_only_on_explicit(tmp_path):
    store = setup_store(tmp_path)
    state = store.load("u1")
    state["rel_score"] = 80
    state["trust"] = 80
    store.save("u1", state)

    bubbles = handle_user_message("u1", "우리 사귀자")
    assert len(bubbles) >= 2
    state = store.load("u1")
    assert state["rel_stage"] == "gf"

    state["rel_stage"] = "some"
    store.save("u2", state)
    bubbles = handle_user_message("u2", "좋아해")
    state = store.load("u2")
    assert state["rel_stage"] == "some"


def test_confession_failure_triggers_soft_distance(tmp_path):
    store = setup_store(tmp_path)
    bubbles = handle_user_message("u1", "사귀자")
    assert len(bubbles) >= 2
    state = store.load("u1")
    assert state["rel_stage"] == "some"
    soft_until = parse_iso(state["flags"]["soft_distance_until"])
    assert soft_until is not None
    assert soft_until > now_utc()


def test_proactive_messages_no_questions(tmp_path, monkeypatch):
    store = setup_store(tmp_path)
    store.save("u1", store.load("u1"))

    monkeypatch.setattr("random.random", lambda: 0.0)
    bubbles = generate_proactive("u1")
    assert bubbles
    assert_no_questions(bubbles)
