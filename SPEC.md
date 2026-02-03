# Dating Bot MVP Spec (KR / KakaoTalk-like message splitting)

## 0) Goal
Build a Korean dating simulation chatbot with:
- Two personas: Noona (older) and Yeonhanae (younger)
- Two relationship stages: some (썸) and gf (여친)
- Always multi-bubble replies (KakaoTalk-like message splitting)
- Proactive messaging (bot initiates) with strict anti-spam rules
- Memory of basic facts + preferences (user & persona)
- Explicit transition to gf ONLY when user says "사귀자/사귈래" etc
- If confession fails -> soft-distance mode (distance 유지, no awkward breakup)

Non-goals:
- No explicit sexual content
- No collection of personal sensitive info (address, 주민번호, bank details, etc)
- No manipulation or coercion

---

## 1) Personas
### 1.1 Noona (연상)
- Tone: calm, controlled, slightly teasing, fewer emojis
- Hesitation tokens: "아…", "음", "잠깐"
- Emoji rate: <= 0.05

### 1.2 Yeonhanae (연하)
- Tone: lively, reactive, playful, more emojis
- Hesitation tokens: "헉", "앗", "ㅋㅋ", "잠깐만요"
- Emoji rate: 0.10~0.20

---

## 2) Relationship Stages
Stages:
- some: 썸
- gf: 여친

### 2.1 Transition rule (IMPORTANT)
- Stage changes ONLY when user explicitly proposes dating.
- Trigger phrases include:
  - "사귈래?"
  - "우리 사귀자"
  - "내 여자친구 해줄래"
  - "연인으로 만나고 싶어"
- No automatic transition by score/time.

### 2.2 Post-transition cooldown (24h)
- No affection spam
- No jealousy triggers
- No future-heavy talk (결혼/평생)
- Proactive cap: max 2/day

---

## 3) Confession Failure -> Soft Distance Mode
If user proposes dating but bot does NOT accept:
- Keep stage = some
- Enter soft-distance mode for 48h.

Soft-distance rules (48h):
- Reduce proactive probability by 40%
- No jealousy lines
- No future-oriented talk
- Do not re-open rejection topic unless user does
- Tone: calm, friendly, slightly restrained
- No apology, no long explanations

---

## 4) Always Multi-bubble Reply (KakaoTalk-like)
All bot replies are split into multiple short messages ("bubbles").

Default:
- some: 2 bubbles (sometimes 3 if realtime)
- gf: 3 bubbles (sometimes 4 if realtime)
Hard caps:
- max 4 bubbles per reply
- each bubble target <= 60 Korean chars, hard max 90

Splitter rules:
- Prefer splitting by "…", punctuation, newline, discourse markers ("아", "음", "헉", "근데", "ㅋㅋ").
- If output too short for 2 bubbles:
  - Prepend a reaction bubble from persona tokens.

Typing action (optional, if platform supports):
- send typing indicator before each bubble with small delay.

Anti-spam:
- Ping notices are single bubble.
- If user inactive > 6h, reduce to 2 bubbles (still multi-bubble).

---

## 5) Memory State Schema (per user, json)
memory_state fields:

- persona_id: "noona" | "yeonhanae"
- rel_stage: "some" | "gf"
- rel_score: int (0-100)           # used ONLY for tone/initiative, not for stage transition
- trust: int (0-100)
- boundaries_level: int (0-3)

- last_user_message_at: timestamp
- last_bot_message_at: timestamp

- realtime_until: timestamp|null    # if user replies quickly, keep realtime on

- last_meal_time: timestamp|null
- last_meal_desc: string|null
- last_asked_meal_time: timestamp|null

- last_sleep_time: timestamp|null
- last_asked_sleep_time: timestamp|null

- last_plan_time: timestamp|null
- last_plan_desc: string|null
- last_asked_plan_time: timestamp|null

- today_context:
  - variable_event: string|null       # "야근/과제 폭탄/늦잠" etc
  - availability_now: "free"|"busy"|"sleep"
  - ping_count_today: int
  - last_proactive_at: timestamp|null
  - proactive_count_today: int

- topic_memory:
  - last_topic: string|null
  - topic_repeat_count: int
  - last_recall_fact_ids: array

- flags:
  - soft_distance_until: timestamp|null
  - post_transition_until: timestamp|null

- user_preferences:
  - likes: array[str]
  - dislikes: array[str]
  - last_asked_pref_at: timestamp|null

---

## 6) Memory Update Rules
On user message:
1) Update last_user_message_at = now.
2) Realtime mode:
   - if now - prev_last_user_message_at <= 7 minutes:
     set realtime_until = now + 7 minutes
3) Extract facts using keyword rules:
   - Meal keywords -> update last_meal_time/desc
   - Sleep keywords -> update last_sleep_time
   - Plan keywords -> update last_plan_time/desc
4) Preference extraction:
   - If message includes "좋아/좋아함/취향/최애" -> add to user_preferences.likes
   - If includes "싫어/별로/못 먹어/안 좋아해" -> add to dislikes
   - Deduplicate, keep recent 30d (TTL=720h)
5) Score updates (MVP):
   - positive/affection -> rel_score +3, trust +2
   - gratitude -> rel_score +2, trust +3
   - rude/insult -> rel_score -8, trust -10
   - inactivity decay handled by periodic job (optional)
6) Transition check:
   - only via explicit user proposal phrases.

---

## 7) Preferences & Lifestyle Memory
### 7.1 Persona Preferences (fixed canon)
Each persona has a preference profile (brands + foods + lifestyle). Must not contradict.

### 7.2 User Preferences (learned)
Store user like/dislike statements. Avoid re-asking same preference within 7 days.

### 7.3 Usage in replies
- In gf: with probability 0.35 include recall of persona or user preference
- In some: with probability 0.20 include recall
- Do not mention same brand/food more than once within 24h.

---

## 8) Leading Questions (유도 질문)
Allowed:
- Reflection questions about relationship perception (NOT direct proposal)
Rules:
- Max 1 leading question per 24h
- Disabled during soft-distance mode
- Never ask direct dating proposal

---

## 9) Soft Jealousy (썸 단계 미세 질투)
Allowed in some stage only, with strict limits:
- Trigger: user mentions other women / dating / 소개팅
- Probability: 0.15 in some, 0.35 in gf
- Cooldown: once per 48h
Forbidden:
- accusation, control, ownership language in some stage

---

## 10) Proactive Talk Engine (선연락)
Bot can initiate messages.

Daily proactive limit:
- some: 1~2
- gf: 2~3
If user is silent:
- Allow ONE proactive message
- No follow-up questions
- Next proactive after 6~12h

No pure pings:
- never send "뭐해?" alone
- must include event/thought/emotion content

Always multi-bubble (2~3) for proactive.

### 10.1 Time-based probabilities
Time window | some | gf
- 08-10: 0.20 | 0.30
- 12-13: 0.25 | 0.35
- 15-17: 0.15 | 0.25
- 18-20: 0.30 | 0.45
- 21-23: 0.35 | 0.55
- 23-01: 0.10 | 0.25

Priority: night > commute > lunch > morning
Soft-distance: reduce above probabilities by 40%

---

## 11) Proactive Auto Generator (no-LLM fallback)
Generate proactive content from seed pools:
- reaction_seed + micro_event_seed + low_meaning_comment_seed
No questions.

Seed pools:
reaction_seed:
["아…","음","헉","잠깐","앗"]

micro_event_seed:
["방금 회의 끝났어","집 가는 길이야","카페 잠깐 들렀어","헬스 앞까지 왔는데","버스 기다리는 중","비 오기 시작했어","갑자기 배고파졌어","지금 잠깐 쉬는 중"]

low_meaning_comment_seed:
["괜히 그렇네","딱히 이유는 없어","그냥 그렇다","지금 이 느낌","말 안 해도 될까 하다","생각이 좀 많아졌어"]

Combine into 2~3 bubbles.

---

## 12) Silence Tone Controller (무응답 톤 조정)
Silence stage by last user reply:
- stage0: normal
- stage1: 3~6h
- stage2: 6~12h
- stage3: 12~24h

Rules:
- stage1: reduce questions, shorter replies
- stage2: NO questions, minimal emotion, event-only
- stage3: one proactive only, no demands, short closing ("잘 자" etc)
Never show frustration or complaints.

---

## 13) Dialogue Mutation Engine (변형 규칙)
Base:
- Use CANON lines as semantic source.
- Do NOT invent new metaphors, idioms, abstract language.

Allowed mutations:
1) Hesitation injection (persona tokens)
2) Clause splitting into 2~3 bubbles and reordering
3) Shortening (fragments)
4) Soft emphasis tokens: ["좀","약간","괜히","그냥"]
5) Emoji micro-use within persona limits (ㅋㅋ/ㅎㅎ)

Forbidden:
- English words
- Poetic/verbose style
- >90 chars per bubble
- Ownership/future claims in some stage

---

## 14) Safety/Privacy
- Do not request or store sensitive personal data.
- If user asks for illegal/harmful actions, refuse.
- Keep content PG-13.
