from __future__ import annotations

import random
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from core.memory import MemoryStore, now_utc, parse_iso, to_iso


CONFESSION_PHRASES = [
    "사귈래?",
    "우리 사귀자",
    "내 여자친구 해줄래",
    "연인으로 만나고 싶어",
    "사귀자",
    "사귈래",
]

MEAL_KEYWORDS = ["밥", "먹었", "먹었어", "먹음", "점심", "저녁", "아침", "야식"]
SLEEP_KEYWORDS = ["잠", "잤어", "자는 중", "졸려", "잠들"]
PLAN_KEYWORDS = ["약속", "만남", "일정", "계획", "스케줄", "모임"]

POSITIVE_KEYWORDS = ["좋아", "보고싶", "설레", "행복"]
GRATITUDE_KEYWORDS = ["고마워", "감사", "고맙"]
RUDE_KEYWORDS = ["싫어", "짜증", "꺼져", "죽어", "재수"]

NOONA_LINES = [
    "아…",
    "음.",
    "오늘 하루가 좀 길다.",
    "괜히 말이 많아지네.",
    "지금 그 생각 중이었어.",
    "그거 좀 공감된다.",
    "지금 딱 그 상태야.",
    "이상하게 편해.",
    "원래 이런 말 잘 안 해.",
    "지금은 이 정도가 좋아.",
]

YEON_LINES = [
    "헉",
    "앗",
    "ㅋㅋ",
    "저 지금 불닭 땡겨요…",
    "오늘 하루가 좀 길다.",
    "괜히 말이 많아지네요.",
    "지금 딱 그 상태예요.",
    "이상하게 편해요.",
    "원래 이런 말 잘 안 해요.",
    "지금은 이 정도가 좋아요.",
]

CONFESSION_FAIL_NOONA = [
    "음…",
    "고마워, 그렇게 생각해준 건.",
    "근데 지금은 이대로가 좋아.",
]

CONFESSION_FAIL_YEON = [
    "아…",
    "말해줘서 고마워요.",
    "근데 지금은 좀 천천히 가고 싶어요.",
]

CONFESSION_ACCEPT_NOONA = [
    "음…",
    "나도 그렇게 생각했어.",
    "그럼 우리 사귀자.",
]

CONFESSION_ACCEPT_YEON = [
    "헉",
    "저도 그래요.",
    "그럼 우리 사귀어요.",
]

REACTION_TOKENS = {
    "noona": ["아…", "음", "잠깐"],
    "yeonhanae": ["헉", "앗", "ㅋㅋ", "잠깐만요"],
}

PROACTIVE_REACTION_SEED = ["아…", "음", "헉", "잠깐", "앗"]
PROACTIVE_EVENT_SEED = [
    "방금 회의 끝났어",
    "집 가는 길이야",
    "카페 잠깐 들렀어",
    "헬스 앞까지 왔는데",
    "버스 기다리는 중",
    "비 오기 시작했어",
    "갑자기 배고파졌어",
    "지금 잠깐 쉬는 중",
]
PROACTIVE_COMMENT_SEED = [
    "괜히 그렇네",
    "딱히 이유는 없어",
    "그냥 그렇다",
    "지금 이 느낌",
    "말 안 해도 될까 하다",
    "생각이 좀 많아졌어",
]

QUESTION_ENDINGS = ["야", "해", "임", "지", "죠", "니", "냐", "까", "까요", "일까"]

_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


def set_memory_store(store: MemoryStore) -> None:
    global _store
    _store = store


def is_confession(text: str) -> bool:
    for phrase in CONFESSION_PHRASES:
        if phrase in text:
            return True
    return False


def should_accept_confession(state: dict) -> bool:
    return state.get("rel_score", 0) >= 70 and state.get("trust", 0) >= 70


def update_realtime(state: dict, now: datetime) -> None:
    prev = parse_iso(state.get("last_user_message_at"))
    if prev and now - prev <= timedelta(minutes=7):
        state["realtime_until"] = to_iso(now + timedelta(minutes=7))


def extract_facts(state: dict, text: str, now: datetime) -> None:
    if any(keyword in text for keyword in MEAL_KEYWORDS):
        state["last_meal_time"] = to_iso(now)
        state["last_meal_desc"] = text[:40]
    if any(keyword in text for keyword in SLEEP_KEYWORDS):
        state["last_sleep_time"] = to_iso(now)
    if any(keyword in text for keyword in PLAN_KEYWORDS):
        state["last_plan_time"] = to_iso(now)
        state["last_plan_desc"] = text[:40]

    prefs = state["user_preferences"]
    if any(keyword in text for keyword in ["좋아", "좋아함", "취향", "최애"]):
        if text not in prefs["likes"]:
            prefs["likes"].append(text)
    if any(keyword in text for keyword in ["싫어", "별로", "못 먹어", "안 좋아해"]):
        if text not in prefs["dislikes"]:
            prefs["dislikes"].append(text)


def update_scores(state: dict, text: str) -> None:
    if any(keyword in text for keyword in POSITIVE_KEYWORDS):
        state["rel_score"] = min(100, state.get("rel_score", 0) + 3)
        state["trust"] = min(100, state.get("trust", 0) + 2)
    if any(keyword in text for keyword in GRATITUDE_KEYWORDS):
        state["rel_score"] = min(100, state.get("rel_score", 0) + 2)
        state["trust"] = min(100, state.get("trust", 0) + 3)
    if any(keyword in text for keyword in RUDE_KEYWORDS):
        state["rel_score"] = max(0, state.get("rel_score", 0) - 8)
        state["trust"] = max(0, state.get("trust", 0) - 10)


def silence_stage(prev_user_at: Optional[datetime], now: datetime) -> int:
    if not prev_user_at:
        return 0
    diff = now - prev_user_at
    hours = diff.total_seconds() / 3600
    if 3 <= hours < 6:
        return 1
    if 6 <= hours < 12:
        return 2
    if 12 <= hours < 24:
        return 3
    return 0


def disallow_questions(state: dict, stage: int, now: datetime) -> bool:
    soft_until = parse_iso(state["flags"].get("soft_distance_until"))
    if soft_until and now < soft_until:
        return True
    return stage >= 2


def line_has_question(line: str) -> bool:
    if "?" in line:
        return True
    for ending in QUESTION_ENDINGS:
        if line.endswith(ending):
            return True
    return False


def filter_questions(lines: List[str]) -> List[str]:
    return [line for line in lines if not line_has_question(line)]


def ensure_bubbles(lines: List[str], persona_id: str, min_count: int, max_count: int) -> List[str]:
    bubbles = [line for line in lines if line]
    if len(bubbles) < min_count:
        reaction = random.choice(REACTION_TOKENS[persona_id])
        bubbles = [reaction] + bubbles
    if len(bubbles) < min_count:
        bubbles.append(random.choice(REACTION_TOKENS[persona_id]))
    if len(bubbles) > max_count:
        merged = bubbles[: max_count - 1]
        merged.append(" ".join(bubbles[max_count - 1 :]))
        bubbles = merged
    return bubbles


def generate_reply(state: dict, now: datetime, stage: int) -> List[str]:
    persona_id = state["persona_id"]
    rel_stage = state["rel_stage"]
    soft_until = parse_iso(state["flags"].get("soft_distance_until"))
    in_soft = soft_until and now < soft_until

    if persona_id == "noona":
        base_lines = NOONA_LINES
    else:
        base_lines = YEON_LINES

    count = 3 if rel_stage == "gf" else 2
    if in_soft:
        count = 2

    lines = random.sample(base_lines, k=min(count, len(base_lines)))

    if disallow_questions(state, stage, now):
        lines = filter_questions(lines)

    if not lines:
        lines = [random.choice(base_lines)]

    return ensure_bubbles(lines, persona_id, 2, 3)


def handle_user_message(user_id: str, text: str) -> List[str]:
    store = get_memory_store()
    state = store.load(user_id)

    now = now_utc()
    prev_user_at = parse_iso(state.get("last_user_message_at"))
    stage = silence_stage(prev_user_at, now)

    state["last_user_message_at"] = to_iso(now)
    update_realtime(state, now)
    extract_facts(state, text, now)
    update_scores(state, text)

    if is_confession(text):
        if should_accept_confession(state):
            state["rel_stage"] = "gf"
            state["flags"]["post_transition_until"] = to_iso(now + timedelta(hours=24))
            lines = (
                CONFESSION_ACCEPT_NOONA
                if state["persona_id"] == "noona"
                else CONFESSION_ACCEPT_YEON
            )
        else:
            state["flags"]["soft_distance_until"] = to_iso(now + timedelta(hours=48))
            lines = (
                CONFESSION_FAIL_NOONA
                if state["persona_id"] == "noona"
                else CONFESSION_FAIL_YEON
            )
        bubbles = ensure_bubbles(lines, state["persona_id"], 2, 3)
    else:
        bubbles = generate_reply(state, now, stage)

    state["last_bot_message_at"] = to_iso(now)
    store.save(user_id, state)
    return bubbles


def _time_window_prob(rel_stage: str, now: datetime) -> float:
    hour = now.astimezone(timezone.utc).hour
    if 8 <= hour < 10:
        return 0.20 if rel_stage == "some" else 0.30
    if 12 <= hour < 13:
        return 0.25 if rel_stage == "some" else 0.35
    if 15 <= hour < 17:
        return 0.15 if rel_stage == "some" else 0.25
    if 18 <= hour < 20:
        return 0.30 if rel_stage == "some" else 0.45
    if 21 <= hour < 23:
        return 0.35 if rel_stage == "some" else 0.55
    if hour == 23 or hour == 0:
        return 0.10 if rel_stage == "some" else 0.25
    return 0.10 if rel_stage == "some" else 0.20


def generate_proactive(user_id: str) -> List[str]:
    store = get_memory_store()
    state = store.load(user_id)
    now = now_utc()

    rel_stage = state["rel_stage"]
    today = now.date()
    last_proactive_at = parse_iso(state["today_context"].get("last_proactive_at"))
    if not last_proactive_at or last_proactive_at.date() != today:
        state["today_context"]["proactive_count_today"] = 0

    limit = 2 if rel_stage == "some" else 3
    if state["today_context"]["proactive_count_today"] >= limit:
        store.save(user_id, state)
        return []

    prob = _time_window_prob(rel_stage, now)
    soft_until = parse_iso(state["flags"].get("soft_distance_until"))
    if soft_until and now < soft_until:
        prob *= 0.6

    if random.random() > prob:
        store.save(user_id, state)
        return []

    bubbles = [
        random.choice(PROACTIVE_REACTION_SEED),
        random.choice(PROACTIVE_EVENT_SEED),
        random.choice(PROACTIVE_COMMENT_SEED),
    ]

    bubbles = ensure_bubbles(bubbles, state["persona_id"], 2, 3)
    bubbles = filter_questions(bubbles)

    state["today_context"]["last_proactive_at"] = to_iso(now)
    state["today_context"]["proactive_count_today"] += 1
    state["last_bot_message_at"] = to_iso(now)
    store.save(user_id, state)

    return bubbles
