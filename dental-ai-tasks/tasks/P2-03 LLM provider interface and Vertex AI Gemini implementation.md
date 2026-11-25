---
id: P2-03
title: LLM provider interface, Vertex AI Gemini implementation and model router
milestone: P2
epic: E2.1
size: L
labels: area:ai, area:backend, type:feature, phi
depends_on: P0-13, P0-14, P1-01, P1-07, P2-01
status: approved
---

# P2-03: LLM provider interface, Vertex AI Gemini implementation and model router

## 1. Summary
Build the only path from our backend to an LLM, plus the rules that pick which model (or no model) handles each request. This task also absorbs **P2-06 (model router)**.

1. **Provider interface** `LlmProvider` (`backend/app/integrations/vertex_ai/`) with three operations:
   - `stream()`: streamed text tokens;
   - `structured()`: one JSON object validated against a Pydantic model (used by P2-05 extraction);
   - cancellation of an in-flight stream within 200 ms (voice barge-in).
2. **Gemini implementation** `VertexGeminiProvider`:
   - Google Gen AI SDK (`google-genai`) with `vertexai=True` only, never an API key;
   - model IDs and location from config (P0-13 / P1-01);
   - per-tier deadlines; one retry on the tier's fallback model;
   - typed errors; no grounding tools; automatic function calling off;
   - metrics and logs with IDs, tiers, token counts and timings only.
3. **Model router** `ModelRouter.route()`: deterministic rules that map each request to `template`, `config` (no LLM call), or an LLM tier `lite` / `flash` / `pro`, with a `reason_code`.
4. **`FakeLlmProvider`** for tests and for every task that builds on the LLM before Vertex AI is reachable.

Done means:
- P2-04 and P2-05 can call `stream()` and `structured()` through one interface, and swapping in the fake needs no code change;
- startup refuses an API key, the `global` location or a model outside the allow-list;
- a stream stops within 200 ms of `cancel()`;
- a failing primary model is retried once on its fallback, and after that the caller gets `LlmUnavailable`;
- static answers and templates make zero LLM calls;
- no prompt or reply text ever appears in logs, metrics or traces.

## 2. Why this matters
Plan §3.2 and §3.3: Gemini is reached **only** through Vertex AI in the BAA-covered project, with **GA models only** and model IDs configurable. Principle 5 (swappable providers) means no other module imports the Google SDK. If every flow called the SDK directly, one careless call could use an API key, the `global` endpoint or a preview model and send PHI outside the BAA.

Plan §4.3 (model routing) is what keeps the system fast and cheap:
- templates and config lookups cost nothing and take no time;
- a Flash-class model handles most turns;
- a Pro-class model is used only when the conversation is genuinely hard.

Plan §4.4: the LLM's time to first token (≤ 300 ms target) is the biggest part of the voice-to-voice budget (≤ 1.5 s p50), and barge-in must stop the LLM stream "immediately". Pilot targets helped by this task: voice-to-voice latency, ≥ 70% bookings without callback (extraction quality), and 0 PHI in logs.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **Vertex AI vs AI Studio:** Google offers Gemini through two APIs. The **Gemini Developer API** (AI Studio, authenticated with an API key) is **not** covered by our BAA and is denied by P0-06's org policy. **Vertex AI** (`aiplatform.googleapis.com`, now branded "Gemini Enterprise Agent Platform") uses the Cloud Run service account through Application Default Credentials (ADC) and is covered. GLOSSARY: "Vertex AI", "ADC".
- **Google Gen AI SDK (`google-genai`):** one Python SDK for both APIs. `genai.Client(vertexai=True, project=..., location=...)` selects Vertex AI. Async calls live under `client.aio`. Docs: https://googleapis.github.io/python-genai/ and https://docs.cloud.google.com/vertex-ai/generative-ai/docs/sdks/overview.
  - **Verify:** the older `vertexai.generative_models` module is deprecated and has a removal date; record the date in the PR. We do not use it.
  - **Verify:** the SDK also reads environment variables (`GOOGLE_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_GENAI_USE_VERTEXAI`). Confirm the exact names in the SDK README, because our startup check refuses the key variables.
- **Model tiers (P0-13, DECISIONS #65, #66, #68):**

  | Tier | Plan §4.3 use | Config key | Proposed primary | Fallback |
  |---|---|---|---|---|
  | `lite` | Short acknowledgements that aren't templates | `GEMINI_MODEL_LITE` | `gemini-3.5-flash-lite` | `gemini-3.1-flash-lite` |
  | `flash` | Extraction (JSON) and normal replies | `GEMINI_MODEL_FLASH` | `gemini-3.8-flash` | `gemini-3.5-flash` |
  | `pro` | Ambiguous, multi-part, complaint turns | `GEMINI_MODEL_PRO` | `gemini-4-argon` if verified | `gemini-3.8-flash` with a higher thinking budget |

  Final IDs come from `docs/adr/0001-gemini-models.md` (P0-13). This task reads them from config and never hard-codes them.
- **Location:** `VERTEX_LOCATION=us-central1` for the MVP, reached through the restricted VIP inside VPC Service Controls (DECISIONS #89). `global` is never allowed (DECISIONS #65).
- **Time to first token (TTFT):** the time from sending the request to receiving the first streamed text. It drives how soon the patient hears or sees a reply. GLOSSARY: "TTFT".
- **Thinking budget:** newer Gemini models can "think" before answering, which improves hard answers but adds latency and tokens. **Verify:** the current SDK field (`thinking_config` with `thinking_budget` or `thinking_level`, depending on the model family) and which values each chosen model accepts.
- **Finish reason:** every Gemini response ends with a reason (for example `STOP`, `MAX_TOKENS`, `SAFETY`). **Verify:** the full enum in `google.genai.types.FinishReason`.
- **What already exists:**
  - **P1-01:** `Settings` with `VERTEX_PROJECT`, `VERTEX_LOCATION` (validator: `us` or `us-*`), `GEMINI_MODEL_LITE/FLASH/PRO`, `GEMINI_ALLOWED_MODELS` (validator: no `preview`/`exp`/`latest`, must be in the list); error base classes; test fixtures.
  - **P1-07:** `structlog` logger with a field allow-list; `stage_timer(Stage.LLM_FIRST_TOKEN | Stage.LLM_TOTAL, model_tier=...)`; metric `dai.stage.latency`; `audit_now()` for security events.
  - **P0-14:** data flow F02 (`api` → Gemini: compact, masked context; GA models; no grounding; durable cache off); ADR 0003 (Pipecat never calls Gemini itself; voice uses this provider).
  - **P2-01:** `TurnOutcome.reply_intent`, `Extraction`, `ConversationState.not_understood`; the turn processor that calls P2-05 (extraction) and P2-04 (reply).
  - **P1-22:** `backend/app/tools/gemini_declarations.json` (function declarations), if a caller wants the model to propose tool calls.

## 4. Scope
**In scope**
- **Package `backend/app/integrations/vertex_ai/`:**
  - `provider.py`: `LlmProvider` protocol, request and result models, `LlmStream`;
  - `errors.py`: typed errors;
  - `gemini.py`: `VertexGeminiProvider`;
  - `fake.py`: `FakeLlmProvider` (scripted responses, latency and failure injection);
  - `factory.py`: `get_llm_provider()` (FastAPI dependency) chosen by `LLM_PROVIDER`;
  - `startup.py`: credential and configuration checks run at app startup.
- **Package `backend/app/orchestrator/router/`:**
  - `router.py`: `ModelRouter`, `RouteInput`, `RouteDecision`;
  - `rules.py`: the ordered routing table (data, not if-chains spread around).
- **Settings additions** (extends P1-01): fallback model IDs, deadlines, output limits, thinking budgets, `LLM_PROVIDER`.
- **Telemetry:** stage timers, token counters, routing log events.
- **Tests:** unit tests with the fake and with a stubbed SDK client; a `live` test marker that runs against Vertex AI in `<prefix>-dev` with synthetic data.
- **Docs:** `docs/llm.md` (how to call the provider, how routing works, how to add a rule, how to change a model).

**Out of scope** (and which task covers it)
- Choosing model IDs, the spike and the `cacheConfig` project setting → P0-13
- Prompt text, the compact context, masking, reply templates and their wording, injection defences → P2-04 (absorbs P2-07 and P2-11)
- The extraction schema, prompt and eval set → P2-05
- Running tool calls the model proposes, allow-lists and preconditions → P2-08 (gateway) and P1-22 (tools)
- The emergency rule detector (runs before any LLM) → P2-20
- Voice pipeline, sentence chunking for TTS, speculative calls on partial transcripts → P3
- Quotas, Provisioned Throughput and load tests → P5-06 / P3-15
- Model-change eval regression → P5-01

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-13 (approved) | Model IDs per tier, fallbacks, ADR, `cacheConfig` applied | Use the Proposed IDs in §3 in `.env.dev`; the code reads config, so final IDs need no code change |
| P0-14 (approved) | F02 rules; Pipecat boundary | Rules are restated in §9 |
| P1-01 (approved) | `Settings`, validators, error base classes | Extend `Settings` as in §6 |
| P1-07 (approved) | Logger, allow-list, `stage_timer`, `audit_now` | Use the signatures in §3; tests use P1-07's log-capture fixture |
| P2-01 (approved) | `reply_intent`, `Extraction`, `not_understood` | The router takes plain values (`RouteInput`), so it is testable without P2-01 running |
| Vertex AI access in `<prefix>-dev` (P0-06, P1-02) | API enabled, service account with `roles/aiplatform.user` | All unit tests use `FakeLlmProvider` or a stubbed SDK client; only `-m live` tests need the project |
| P2-04 / P2-05 (parallel) | Callers | They code against `LlmProvider` and `FakeLlmProvider` from this spec |

## 6. Interface contract

### Settings additions (`backend/app/core/config.py`, extends P1-01)
```python
LLM_PROVIDER: Literal["vertex", "fake"] = "vertex"      # "fake" allowed only when ENV in {local, test}

GEMINI_MODEL_LITE_FALLBACK: str | None = None           # Proposed (DECISIONS #160); must be in GEMINI_ALLOWED_MODELS
GEMINI_MODEL_FLASH_FALLBACK: str | None = None
GEMINI_MODEL_PRO_FALLBACK: str | None = None

# Deadlines in milliseconds (Proposed, DECISIONS #161). P3-15 tunes them.
LLM_TTFT_DEADLINE_MS_LITE: int = Field(default=1500, ge=200, le=10000)
LLM_TTFT_DEADLINE_MS_FLASH: int = Field(default=2000, ge=200, le=10000)
LLM_TTFT_DEADLINE_MS_PRO: int = Field(default=4000, ge=200, le=20000)
LLM_TOTAL_DEADLINE_MS_LITE: int = Field(default=8000, ge=1000, le=30000)
LLM_TOTAL_DEADLINE_MS_FLASH: int = Field(default=10000, ge=1000, le=30000)
LLM_TOTAL_DEADLINE_MS_PRO: int = Field(default=15000, ge=1000, le=60000)

LLM_MAX_OUTPUT_TOKENS_REPLY: int = Field(default=256, ge=32, le=2048)     # short spoken-style replies
LLM_MAX_OUTPUT_TOKENS_STRUCTURED: int = Field(default=512, ge=64, le=4096)
LLM_THINKING_BUDGET_LITE: int = 0                        # Verify field semantics per model (§3)
LLM_THINKING_BUDGET_FLASH: int = 0
LLM_THINKING_BUDGET_PRO: int = 1024
ROUTER_LONG_TURN_CHARS: int = Field(default=400, ge=100, le=4000)
```
The P1-01 model validator is extended to check the three `*_FALLBACK` IDs with the same rules (no `preview`/`exp`/`latest`, must be in `GEMINI_ALLOWED_MODELS`). A fallback may equal another tier's primary (for example the `pro` fallback is the `flash` primary).

### Request and result models (`provider.py`)
```python
Tier = Literal["lite", "flash", "pro"]
Purpose = Literal["reply", "extract", "emergency_check", "other"]

class LlmMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    role: Literal["user", "model"]
    text: str

class LlmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tier: Tier
    purpose: Purpose
    system: str                          # system instruction (P2-04 builds it)
    messages: tuple[LlmMessage, ...]     # compact context, already masked by P2-04
    tools: tuple[dict, ...] = ()         # Gemini function declarations from P1-22 (optional)
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_output_tokens: int | None = None # default from settings by method
    session_id: uuid.UUID | None = None  # for logs/metrics correlation only; never sent to Google
    turn_seq: int | None = None

class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    cached_tokens: int = 0

class FunctionCallProposal(BaseModel):
    name: str
    args: dict[str, Any]                 # validated later by P2-08 / P1-22; never executed here

class LlmChunk(BaseModel):
    text: str = ""
    function_call: FunctionCallProposal | None = None

class LlmResult(BaseModel):
    model: str                           # model ID actually used
    tier: Tier
    fallback_used: bool
    finish: Literal["stop", "max_tokens", "blocked", "other"]
    usage: TokenUsage
    ttft_ms: int | None
    total_ms: int

T = TypeVar("T", bound=BaseModel)

class StructuredResult(LlmResult, Generic[T]):
    value: T                             # validated instance of the requested model
```

### Provider protocol
```python
class LlmStream(Protocol):
    def __aiter__(self) -> AsyncIterator[LlmChunk]: ...
    async def cancel(self) -> None: ...        # idempotent; stops within 200 ms; no further chunks
    @property
    def result(self) -> LlmResult | None: ...  # set when the stream ends (also after cancel: finish="other")

class LlmProvider(Protocol):
    def stream(self, req: LlmRequest) -> LlmStream: ...
    async def structured(self, req: LlmRequest, schema: type[T]) -> StructuredResult[T]: ...
    async def aclose(self) -> None: ...
```
Rules every implementation follows:
- `stream()` starts the request lazily on first iteration, so a caller can create it and cancel before any network call.
- Cancelling is also possible by cancelling the asyncio task that iterates; both paths close the HTTP stream.
- `structured()` never streams to the caller. It returns only a value that passed `schema.model_validate()`.
- Neither method ever logs `system`, `messages`, `text`, `args` or the raw response.

### Errors (`errors.py`, subclasses of P1-01's `AppError`)
| Error | When | Caller's action |
|---|---|---|
| `LlmUnavailable(reason_code)` | Primary and fallback both failed with a retryable error (429, 5xx, deadline, network) | Template reply `llm_unavailable` (P2-04); extraction counts as not understood (§7 step 9) |
| `LlmBlocked` | Finish reason is a safety/blocklist/prohibited-content block (Verify enum names) | Template reply `rephrase_please`; logged with `reason_code=llm_blocked` |
| `LlmBadOutput` | `structured()` got invalid JSON or failed schema validation on primary and fallback | Extraction counts as not understood |
| `LlmBadRequest` | 400 / invalid argument (our bug: bad schema, too-long input) | Not retried; error log; `LlmUnavailable` behaviour for the patient |
| `LlmConfigError` | 401 / 403 / 404 model not found / permission denied | Not retried; error log + alert (P1-07 `log_5xx`-style metric `dai.llm.config_error`); patient gets `llm_unavailable` |
| `LlmCancelled` | `cancel()` was called | Not an error for the caller; never logged at warning level |

`reason_code` values: `rate_limited`, `server_error`, `ttft_deadline`, `total_deadline`, `network`, `bad_output`, `llm_blocked`, `bad_request`, `config`.

### Retry and fallback policy (Proposed, DECISIONS #160)
1. Call the tier's primary model with the tier's TTFT and total deadlines.
2. **Retryable failures:** HTTP 429, 500, 502, 503, 504, a network error, a TTFT deadline, or (for `structured()` only) `LlmBadOutput`.
3. On a retryable failure **before any chunk reached the caller**, call the tier's fallback model **once**, with fresh deadlines. If no fallback is configured, retry the primary once instead.
4. A failure **after** chunks reached the caller is not retried (the patient already saw or heard part of a reply). The stream ends with `LlmUnavailable(total_deadline|server_error)`; P2-04 appends the `llm_unavailable` template.
5. Never more than 2 attempts per request. Never switch location, never use `global`.
6. 400, 401, 403 and 404 are not retried.

### Router (`orchestrator/router/router.py`)
```python
class RouteInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    purpose: Purpose
    state: str                               # P2-01 state name
    reply_intent: str | None = None          # for purpose="reply" (from TurnOutcome)
    intent: str | None = None                # from the latest Extraction (e.g. "complaint")
    intent_count: int = 1                    # >1 = multi-part turn
    not_understood_in_state: int = 0         # ConversationState.not_understood[state]
    turn_chars: int = 0                      # length of the patient's latest text
    previous_attempt_failed: bool = False    # the same purpose already failed this turn

class RouteDecision(BaseModel):
    handler: Literal["template", "config", "llm"]
    tier: Tier | None = None                 # set when handler == "llm"
    template_id: str | None = None           # set when handler == "template"; P2-04 owns the text
    info_topic: str | None = None            # set when handler == "config"; a P1-22 get_clinic_information topic
    reason_code: str                         # which rule matched

class ModelRouter:
    def __init__(self, rules: Sequence[RouteRule] = DEFAULT_RULES, settings: Settings | None = None) -> None: ...
    def route(self, inp: RouteInput) -> RouteDecision: ...   # pure, sync, no I/O
```

### Routing table (`rules.py`, first match wins; Proposed, DECISIONS #162)
| # | Condition | Decision | `reason_code` |
|---|---|---|---|
| R1 | `purpose == "reply"` and `reply_intent` in `TEMPLATE_INTENTS` | `template`, `template_id = reply_intent` | `template` |
| R2 | `purpose == "reply"` and `reply_intent` in `CONFIG_INTENTS` | `config`, `info_topic` from the map | `static_answer` |
| R3 | `purpose == "emergency_check"` | `llm`, `flash` | `emergency_second_check` |
| R4 | `intent == "complaint"` | `llm`, `pro` | `complaint` |
| R5 | `intent_count > 1` | `llm`, `pro` | `multi_intent` |
| R6 | `not_understood_in_state >= 1` or `previous_attempt_failed` | `llm`, `pro` | `retry_after_not_understood` |
| R7 | `turn_chars > ROUTER_LONG_TURN_CHARS` | `llm`, `pro` | `long_turn` |
| R8 | `purpose == "reply"` and `reply_intent` in `LITE_INTENTS` | `llm`, `lite` | `short_reply` |
| R9 | anything else | `llm`, `flash` | `default` |

Initial sets (Proposed; flow tasks add their `reply_intent` names here by PR, and a unit test fails if a `reply_intent` used in a handler is in none of the sets and isn't meant for the default rule; see T16):
```python
TEMPLATE_INTENTS = frozenset({
    "greeting", "goodbye", "llm_unavailable", "rephrase_please", "busy_try_again",
    "emergency_tier1", "crisis", "read_back",          # safety and PHI read-back are always templates
    "confirm_summary", "confirm_registration", "confirm_callback",   # confirmation card + fixed question (DECISIONS #174)
    "session_expired", "channel_switched",
})
CONFIG_INTENTS = {           # answered by P1-22 get_clinic_information (clinic config), no LLM call
    "faq_hours": "hours", "faq_address": "address", "faq_phone": "phone",
    "faq_parking": "parking", "faq_insurance": "insurance", "faq_services": "services",
    "faq_languages": "languages", "faq_payment": "payment",
    "faq_new_patients": "new_patients", "faq_website": "website",
}
LITE_INTENTS = frozenset({"acknowledge", "thanks_reply", "small_talk"})
```
Notes:
- **Emergency text is never generated by a model.** `emergency_tier1` and `crisis` replies are templates (R1), approved under P0-03.
- `read_back` (reading back name, phone, date, time) is a template so the exact PHI wording is deterministic.
- Every confirmation step (`confirm_summary`, `confirm_registration`, `confirm_callback`) is a template with a written summary card, never LLM text (DECISIONS #174).
- R3 sends the emergency second check to `flash`, never `lite`; P2-20 decides what to do with the result.
- The router never reads PHI: `RouteInput` has no text, only counts and names.

### Log events and metrics (P1-07 allow-list additions: `model`, `model_tier` exist; add `purpose`, `handler`, `fallback_used`, `finish`, `input_tokens`, `output_tokens`, `thinking_tokens`, `ttft_ms`)
| Event / metric | Fields |
|---|---|
| `llm.call` (info, once per request) | `clinic_id`, `model`, `model_tier`, `purpose`, `fallback_used`, `finish`, `input_tokens`, `output_tokens`, `thinking_tokens`, `ttft_ms`, `duration_ms`, `turn_seq` |
| `llm.call_failed` (warning) | `clinic_id`, `model`, `model_tier`, `purpose`, `reason_code`, `attempt`, `provider_status` |
| `llm.cancelled` (debug) | `model_tier`, `purpose`, `duration_ms` |
| `router.decision` (debug in prod, info in dev) | `state`, `purpose`, `handler`, `model_tier`, `reason_code`, `turn_seq` |
| `dai.stage.latency` | stages `llm_first_token`, `llm_total`, attributes `model_tier`, `channel` |
| `dai.llm.tokens` (new counter) | attributes `model_tier`, `kind` (`input`/`output`/`thinking`) |
| `dai.llm.outcome` (new counter) | attributes `model_tier`, `result` (`ok`/`fallback_ok`/`unavailable`/`blocked`/`bad_output`/`config`) |
| `dai.router.decision` (new counter) | attributes `handler`, `model_tier`, `reason_code` |

### Example
```python
router = ModelRouter()
d = router.route(RouteInput(purpose="extract", state="AVAILABILITY", intent_count=1, turn_chars=42))
# RouteDecision(handler="llm", tier="flash", reason_code="default")

llm = get_llm_provider()
res = await llm.structured(
    LlmRequest(tier=d.tier, purpose="extract", system=SYSTEM_EXTRACT_V1,
               messages=(LlmMessage(role="user", text="next tuesday after 3 works"),)),
    schema=Extraction,
)
# res.value == Extraction(proposed_event="time_preference_given", slots={"preferred_time": {...}}, understood=True)
# res.model == "gemini-3.8-flash", res.fallback_used is False, res.ttft_ms == 380

d = router.route(RouteInput(purpose="reply", state="FAQ", reply_intent="faq_hours"))
# RouteDecision(handler="config", info_topic="hours", reason_code="static_answer")  -> get_clinic_information, no LLM call

s = llm.stream(LlmRequest(tier="flash", purpose="reply", system=SYSTEM_REPLY_V1, messages=ctx))
async for chunk in s:
    send_to_client(chunk.text)
    if barge_in.is_set():
        await s.cancel()      # no more chunks; HTTP stream closed within 200 ms
```

## 7. Implementation guide
1. **Settings.** Add the §6 fields to `Settings` and extend P1-01's model validator to cover the fallback IDs. Add a validator: `LLM_PROVIDER == "fake"` is rejected unless `ENV` is `local` or `test`.
2. **Startup checks (`startup.py`), called from the FastAPI lifespan** when `LLM_PROVIDER == "vertex"`:
   - refuse to start if `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set (Verify names, §3), or if `GOOGLE_GENAI_USE_VERTEXAI` is set to a false value;
   - refuse if `VERTEX_PROJECT` or `GEMINI_MODEL_FLASH` is empty (`lite` and `pro` may fall back to `flash` when empty, logged once at startup as `llm.tier_defaulted`);
   - log `llm.config` once with the model IDs and location (no secrets).
3. **Client construction (`gemini.py`).** One `genai.Client(vertexai=True, project=VERTEX_PROJECT, location=VERTEX_LOCATION)` per process, created in the lifespan and closed in `aclose()`. Never pass `api_key`. **Verify:** how to pass an HTTP timeout and whether the async client reuses connections (`http_options`); keep connections warm (plan §4.4) by reusing the one client.
4. **Request mapping.** Build `GenerateContentConfig` from `LlmRequest` (**Verify** each field name against the SDK):
   - `system_instruction=req.system`;
   - `temperature`, `max_output_tokens` (settings default per method);
   - thinking settings from `LLM_THINKING_BUDGET_<TIER>`;
   - for `structured()`: `response_mime_type="application/json"` plus the schema from `schema.model_json_schema()` (**Verify** whether to use `response_schema` or `response_json_schema`, and which JSON Schema keywords Vertex AI accepts; P1-22 already restricts tool schemas to that subset, reuse its helper);
   - `tools` from `req.tools` as function declarations only;
   - `automatic_function_calling` **disabled** (the SDK must never execute Python callables);
   - an assertion that no tool is `google_search`, `google_search_retrieval`, `google_maps` or code execution; violating it raises `LlmBadRequest` before any network call (test T7).
5. **Streaming with cancel.** Implement `GeminiStream`:
   - on first `__anext__`, start `client.aio.models.generate_content_stream(...)` inside an `asyncio.Task` that pushes chunks into an `asyncio.Queue(maxsize=32)`;
   - apply the TTFT deadline with `asyncio.wait_for` on the first chunk and the total deadline on the whole task;
   - `cancel()` sets a flag, cancels the task (which closes the underlying HTTP stream), drains the queue and returns; the iterator then stops;
   - record `stage_timer(Stage.LLM_FIRST_TOKEN)` at the first chunk and `Stage.LLM_TOTAL` at the end;
   - set `result` with usage from the final chunk's usage metadata (**Verify** field names: prompt, candidates, thoughts, cached token counts).
6. **Retry and fallback.** Wrap both methods in one `_with_fallback(tier, attempt_fn)` helper that implements §6's policy. Map SDK exceptions (**Verify:** `google.genai.errors.APIError` / `ClientError` / `ServerError` and their status attribute) to our errors. Keep the mapping table in one function and unit-test every row.
7. **Structured output.** Parse the response text with `schema.model_validate_json()`. On failure, raise `LlmBadOutput` (retryable once via fallback). Never log the invalid text; log only `reason_code=bad_output` and the Pydantic error **locations** (field paths, no values).
8. **Fake provider (`fake.py`).**
   ```python
   class FakeLlmProvider(LlmProvider):
       def __init__(self, script: Sequence[FakeStep] = ()) -> None: ...
       calls: list[LlmRequest]                       # for assertions (tests only; holds test text)
   @dataclass
   class FakeStep:
       chunks: Sequence[str] = ()                    # streamed pieces
       value: BaseModel | dict | None = None         # for structured()
       error: LlmError | None = None                 # injected failure
       ttft_ms: int = 0; chunk_delay_ms: int = 0     # simulated latency
       on_primary_only: bool = False                 # fail primary, succeed on fallback
   ```
   It honours deadlines, cancel and the fallback policy exactly as the real provider does (shared `_with_fallback`), so callers' tests exercise the real behaviour.
9. **Caller contract for failures (documented in `docs/llm.md`; P2-05 and P2-04 implement):**
   - P2-05 extraction catches `LlmUnavailable`, `LlmBadOutput` and `LlmBlocked` and returns `Extraction(understood=False, proposed_event=None)`. P2-01 then counts it in `not_understood[state]`, and at `conversation.not_understood_limit` (default 2) the existing `not_understood_limit` event moves the conversation to `CALLBACK_REQUEST`. No new state-machine event is needed.
   - P2-04 replies use the `llm_unavailable` or `rephrase_please` template (R1, no LLM call).
   - The callback flow's own replies are templates, so they still work when Gemini is down.
10. **Router.** Implement `rules.py` as an ordered list of `RouteRule(name, predicate, decide)` built from §6's table; `ModelRouter.route` returns the first match. Log `router.decision` and increment `dai.router.decision`. If a decision's tier has no model configured, use `flash` and set `reason_code` to `<rule>_tier_defaulted`.
11. **Factory.** `get_llm_provider()` returns the process-wide provider from `app.state` (FastAPI dependency); tests override it with `FakeLlmProvider`.
12. **Live tests** (`tests/integration/test_vertex_live.py`, marker `live`, skipped unless `VERTEX_LIVE_TESTS=1`): run T20–T22 in `<prefix>-dev` with synthetic text only.
13. **Docs and notifications.** Write `docs/llm.md`. Notify P2-04 (templates `llm_unavailable`, `rephrase_please`; reply intents and router sets), P2-05 (`structured()`, failure contract), P2-08 (`FunctionCallProposal` is never executed here), P2-20 (`emergency_check` purpose), P3-01 / P3-15 (cancel, TTFT metrics, deadlines), P5-01 (`LLM_PROVIDER=fake` for deterministic CI; live runs for evals), P5-06 (429 counters).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| `GOOGLE_API_KEY` present in the environment | App refuses to start with `LlmConfigError("api key env var set")` |
| `VERTEX_LOCATION=global` or a model ID with `preview` | P1-01 settings validation fails; app does not start |
| `GEMINI_MODEL_PRO` empty | `pro` routes use `flash`; `llm.tier_defaulted` logged once at startup |
| Primary returns 429 before any chunk | One call to the fallback; `fallback_used=True`; `dai.llm.outcome{result=fallback_ok}` |
| Primary and fallback both 429 | `LlmUnavailable(rate_limited)`; patient gets the `llm_unavailable` template; second time in the same state → `CALLBACK_REQUEST` via `not_understood_limit` |
| No chunk within the TTFT deadline | Request cancelled; fallback tried once |
| Stream breaks after 10 chunks were sent | No retry; `LlmUnavailable(server_error)` raised from the iterator; P2-04 appends the `llm_unavailable` template |
| `cancel()` called before iteration starts | No network call is made; iterator yields nothing |
| `cancel()` called twice | Second call is a no-op |
| Caller abandons the stream without cancel (exception, disconnect) | The task is cancelled in `__aexit__`/finaliser; no orphaned HTTP streams (T11) |
| Finish reason `MAX_TOKENS` on a reply | Chunks already sent are kept; `finish="max_tokens"`; counter incremented; no retry |
| Finish reason `MAX_TOKENS` on `structured()` | JSON is incomplete → `LlmBadOutput` → fallback once |
| Safety block | `LlmBlocked`; no retry (the fallback would likely block too); `rephrase_please` template |
| Model returns valid JSON with an extra field | Schema has `extra="forbid"` → `LlmBadOutput`; fallback once |
| Model proposes a function call that isn't in `req.tools` | Returned as `FunctionCallProposal`; P2-08 rejects it (`security.tool_denied`); the provider never executes it |
| 403 / 404 model not found (model retired, IAM wrong) | `LlmConfigError`; no retry; error log + `dai.llm.config_error`; patient gets `llm_unavailable` |
| `reply_intent` not in any router set | R9 default `flash` (unless T16 lists it as missing) |
| FAQ asked but the config value is empty | Router still returns `config`; P2-04/P2-18 handle the empty value with a template ("I don't have that, I can ask the office to call you") — never an LLM guess |
| Very long patient text (> `max_turn_chars`) | Already truncated by P2-01; router may pick `pro` via R7 |

## 9. Security, HIPAA and PHI
- **PHI handled:** the `system` and `messages` text that P2-04 builds may contain PHI (masked where possible: name, DOB, phone, reason). It flows **only** to Vertex AI in our BAA-covered project, in `us-central1`, over the restricted VIP inside VPC Service Controls (P0-14 F02). The provider adds nothing to it and stores none of it.
- **Rules enforced in code:**
  - Vertex AI only; no API key accepted (startup check, T1);
  - US location only, GA model IDs from the allow-list only (P1-01 validators, T2);
  - no grounding or code-execution tools (T7);
  - automatic function calling off; model output never executed;
  - `session_id` is never sent to Google (no labels or metadata with IDs).
- **Never logged, traced or put in metrics:** `system`, `messages`, chunk text, function-call `args`, raw responses, Pydantic error values. Only model, tier, purpose, counts, timings and codes (P1-07 allow-list). OpenTelemetry auto-instrumentation for httpx must keep body capture off (P1-07).
- **Data settings** (owned by P0-13): durable cache off, request-response logging off. This task adds a startup info log of the model IDs so reviewers can see what runs.
- **`FakeLlmProvider.calls`** keeps request text in memory for tests only; `LLM_PROVIDER=fake` is rejected outside `local`/`test`.
- **Audit:** no new audit events. `audit_now("security.injection_suspected")` stays with P2-04; tool denials with P2-08.

## 10. Testing
Commands:
```bash
cd backend && pytest tests/unit/integrations/vertex_ai tests/unit/orchestrator/router -q
VERTEX_LIVE_TESTS=1 pytest -m live tests/integration/test_vertex_live.py   # dev project, synthetic data
```
| # | Case | Expected |
|---|---|---|
| T1 | Startup with `GOOGLE_API_KEY` set | `LlmConfigError`; app does not start |
| T2 | Fallback ID with `preview`, or not in the allow-list | Settings validation error |
| T3 | `LLM_PROVIDER=fake` with `ENV=prod` | Settings validation error |
| T4 | Stubbed SDK client: request mapping | `system_instruction`, temperature, max tokens, thinking setting, JSON mime type and schema set as specified; automatic function calling disabled |
| T5 | Stream yields three chunks | Caller receives them in order; `result` has usage and `ttft_ms` |
| T6 | `cancel()` mid-stream with a stub that yields every 50 ms | No chunk after `cancel()` returns; task closed in ≤ 200 ms |
| T7 | `req.tools` containing `google_search` | `LlmBadRequest` before any network call |
| T8 | Primary 429 then fallback OK | One retry on the fallback model; `fallback_used=True` |
| T9 | Primary and fallback 503 | `LlmUnavailable(server_error)`; exactly 2 attempts |
| T10 | Failure after chunks were delivered | No retry; `LlmUnavailable` raised from the iterator |
| T11 | Iterating task cancelled by the caller | Underlying stream closed; no pending tasks at test end |
| T12 | TTFT deadline exceeded | Fallback tried; deadline reason recorded |
| T13 | `structured()` invalid JSON then valid on fallback | Returns the validated value; one retry |
| T14 | 400 / 403 / 404 | `LlmBadRequest` / `LlmConfigError`; no retry |
| T15 | Safety finish reason | `LlmBlocked`; no retry |
| T16 | Router table: every R1–R9 row, rule order (complaint + template intent → template wins), tier defaulting | Matches §6; also a test listing every `reply_intent` registered by flow handlers is either in a set or explicitly marked default |
| T17 | `config` and `template` decisions | `FakeLlmProvider.calls` stays empty through a full FAQ turn |
| T18 | Log capture with a PHI corpus (P1-07 fixture) in `system`, `messages` and response | No corpus value in any log line, metric attribute or span attribute |
| T19 | Fake and real provider share `_with_fallback` | Same outcomes for T8–T15 with the fake |
| T20 (live) | Streamed reply on `flash` in `<prefix>-dev` | Chunks received; usage recorded; TTFT logged |
| T21 (live) | `structured()` with the `Extraction` schema | Valid instance |
| T22 (live) | Cancel after the first chunk | No more chunks; no error logged at warning level |

## 11. Acceptance criteria
- [ ] P2-04 and P2-05 can use `LlmProvider` (`stream`, `structured`) and switching `LLM_PROVIDER` between `vertex` and `fake` needs no code change (T17, T19)
- [ ] The app does not start with an API-key variable, the `global` location, or a model ID outside the allow-list (T1–T3)
- [ ] No request contains grounding or code-execution tools, and automatic function calling is disabled (T4, T7)
- [ ] A stream stops within 200 ms of `cancel()` and leaves no open tasks (T6, T11, T22)
- [ ] A retryable failure before the first chunk is retried exactly once on the tier's fallback; nothing is retried after chunks were delivered or for 4xx errors (T8–T15)
- [ ] The router implements R1–R9 in order, and template and config decisions make zero LLM calls (T16, T17)
- [ ] Every LLM call logs model, tier, purpose, tokens, TTFT and duration, and records `llm_first_token` / `llm_total` latency (T5, T20)
- [ ] No prompt, reply or argument text appears in logs, metrics or traces (T18)
- [ ] Live tests T20–T22 pass in `<prefix>-dev`

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI (live tests run manually in dev and the run is linked in the PR)
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/llm.md` written; P1-07 allow-list updated with the new fields
- [ ] P2-04, P2-05, P2-08, P2-20, P3-01, P3-15, P5-01 and P5-06 issues notified

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P2-04 Context + prompts | `LlmProvider.stream()`; `ModelRouter` for `purpose="reply"`; templates `llm_unavailable`, `rephrase_please`, `busy_try_again`, `read_back`, emergency templates are theirs to word; router sets in `rules.py` to extend |
| P2-05 Extraction | `structured(req, Extraction)`; route with `purpose="extract"`; failure contract (§7 step 9) |
| P2-08 Tool gateway | `FunctionCallProposal` objects, never executed by the provider |
| P2-18 FAQ | `config` decisions with `info_topic` (a P1-22 `get_clinic_information` topic); no LLM for static answers |
| P2-20 Emergency | `purpose="emergency_check"` → `flash`; emergency replies are templates |
| P3-01 / P3-02 / P3-15 Voice | `cancel()` ≤ 200 ms; TTFT metrics per tier; deadlines in env vars; ADR 0003: Pipecat calls this provider, never its own Google LLM service |
| P5-01 Evals | `LLM_PROVIDER=fake` for deterministic CI; real provider for eval runs |
| P5-06 Load / quotas | `dai.llm.outcome{result}` and `llm.call_failed{reason_code=rate_limited}` |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should a tier's primary be skipped for a while after repeated failures (a circuit breaker)? | Not for the MVP: one fallback per request is enough at pilot traffic. Revisit with P5-06 load test results. | Tech lead |
| 2 | Are the TTFT deadlines right for voice? | Keep 1.5 / 2 / 4 s for chat; P3-15 measures and may lower them for voice using the env vars, no code change. | P3-15 owner |
| 3 | Does the `pro` model's thinking budget of 1024 hurt latency too much? | Start at 1024 and measure in P0-13's spike and P5-01 evals; it is an env var. | AI lead |

## 15. References
- Plan: §1 principle 5, §3.2, §3.3, §4.1, §4.3, §4.4, §6
- Google Gen AI SDK: https://googleapis.github.io/python-genai/
- Vertex AI SDK overview: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/sdks/overview
- Model versions and lifecycle: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions
- Structured output: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output
- Data governance: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance
- DECISIONS: #65, #66, #68, #73, #89, #160, #161, #162
- Related tasks: P0-13, P0-14, P1-01, P1-07, P1-19, P1-22, P2-01, P2-04, P2-05, P2-08, P2-18, P2-20, P3-01, P3-02, P3-15, P5-01, P5-06
