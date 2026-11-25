---
id: P4-11
title: Appointment type mapping, booking rules and clinic info screens, plus emergency rules viewer with change requests
milestone: P4
epic: E4.2
size: L
labels: area:admin, area:frontend, type:feature
depends_on: P4-09, P1-19, P1-20, P1-15, P1-22, P0-02, P0-03, P1-13, P1-03
status: approved
---

# P4-11: Appointment type mapping, booking rules and clinic info screens, plus emergency rules viewer with change requests

> Consolidated task (#55). It absorbs P4-12 "Emergency rules editor with approval workflow and history" (see `tasks/_CONSOLIDATION.md`). Emergency rules stay **file-only with dentist sign-off** (P1-19, DECISIONS #14). This task gives them a read-only viewer, version history and a "Request a change" flow instead of an in-console editor (DECISIONS #264).

## 1. Summary
Add four pages to the admin console (P4-09 shell), so the clinic can tune how the AI books without a developer.

1. **Appointment types** (`/admin/settings/appointment-types`). For each of the 15 reason codes (P0-02), the admin can:
   - turn AI booking on or off;
   - choose what happens when it is off (callback or "not offered");
   - enable or disable each variant;
   - pick the providers and operatories from Open Dental's own lists.

   The visit length comes from the Open Dental appointment type and is shown read-only. It can be edited only for a variant that has no Open Dental type.
2. **Booking rules** (`/admin/settings/booking-rules`):
   - how far ahead the AI books (default 7 days, any value 1–365);
   - earliest booking lead time (routine and urgent);
   - number of options offered;
   - reserved blockouts;
   - cancel and reschedule notice;
   - what happens inside the notice window;
   - automatic new-patient creation.

   The identity-verification rules are shown read-only.
3. **Clinic info** (`/admin/settings/clinic-info`): address, parking, insurers accepted and their aliases, services, languages, payment, new-patient note and provider bios. The AI reads these texts to patients word for word.
4. **Emergency rules** (`/admin/settings/emergency-rules`):
   - read-only view of the active rules (status, reviewer, categories, phrases, tier actions, scripts);
   - their version history with diffs;
   - a **Request a change** form, which stores a change request and notifies the project team. The team applies it through the reviewed file process with the dentist's sign-off.

Before publishing a mapping or booking-rule change, **Check availability** shows how many open slots each changed reason would have in the next 7 days, now versus with the change. A setting that would silently stop all bookings is visible before it goes live.

The task is done when:
- the availability engine uses published changes without a redeploy;
- unapproved emergency rules can never go live;
- every change is versioned and audited.

## 2. Why this matters
Plan §7 says staff configure "reason → type → duration → providers; new-patient rules, verification fields, cancellation window". These settings decide every booking the AI makes. A wrong provider, a disabled variant or a too-short horizon means the AI offers nothing and sends everyone to a callback. A wrong operatory can put a patient in a room that isn't staffed.

Today these values come only from seed files (P0-02, P1-19). Without screens, every small change (a hygienist leaves, the clinic stops offering whitening) needs a developer and a release.

Emergency rules are different. They decide whether the AI tells someone to call 911. A wrong edit can cost a life, so the plan (§4.8) and DECISIONS #14 require a dentist's approval, and P1-19 locked them to the file process. The console shows them so the clinic can see exactly what the AI does, and gives a safe way to ask for changes.

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P4, WhatsApp, Reminders & Admin Console**.
- **Appointment type mapping (P0-02):** a fixed list of 15 reason codes (`new_patient_exam`, `recall_cleaning`, `toothache`, …, `other`). Each reason has:
  - `label`, `bookable_by_ai`, `when_not_bookable` (`callback` | `not_offered`);
  - a list of **variants**, chosen by patient type (new or existing) and age range. Each variant has:
    - an Open Dental appointment type (`od_appointment_type_num`, `od_name`, `duration_min`);
    - providers (`od_prov_num`, `od_abbr`);
    - `operatory_nums` (empty = any operatory).

  Adding or renaming a reason code is a product change (schema + P2-05 prompt). Adding a variant or changing age ranges is a structure change, made through the file.
- **Visit length (P1-20):** the availability engine takes the length from the Open Dental appointment type's `pattern` when `od_appointment_type_num` is set. `duration_min` is used only when there is no Open Dental type. So editing `duration_min` in our config would have no effect for typed variants. The console therefore shows the length as read-only ("Change it in Open Dental's appointment type") and allows editing only for untyped variants (DECISIONS #264).
- **Config service (P1-19):**
  - `PATCH /v1/admin/config {base_version, changes, change_note}` creates a version;
  - `POST /v1/admin/config/activate` makes it live;
  - after activation, P1-19 publishes `cfg:changed` and invalidates the Open Dental setup cache when `appointment_types` changed. P1-20 reads the active version for every new session, so changes apply **without a redeploy**. Sessions already in progress keep their pinned version (P1-19 pinning).
  - **Edit matrix:**
    - console-editable: `clinic`, `hours`, `holidays`, `scheduling`, `policies`, `callback`, `reminders`, `voice`, `clinic_info`, and in `appointment_types` only providers, operatories, `bookable_by_ai` and variant enable/disable;
    - view-only: `emergency_rules`, `verification`, `privacy`.

    A PATCH that touches a locked field gets 403 `config_section_locked`.
- **Scheduling and policies fields (P1-19):**
  - `scheduling`: `booking_horizon_days` (default 7, 1–365, DECISIONS #86), `min_lead_minutes` (routine, default 120), `min_lead_minutes_urgent` (Tier 2, default 30), `options_per_offer` (2–3), `reserved_blockouts.new_patient` / `.emergency` (Open Dental blockout DefNums), `other_blockouts_block_booking`;
  - `policies`: `cancel_min_notice_hours`, `reschedule_min_notice_hours`, `inside_notice_action` (`callback` | `allow`), `new_patient_auto_create`;
  - `verification` (file-only): `required: [full_name, dob]`, `one_of: [mobile_phone, zip_code]`, `max_attempts`.
- **Clinic info (P1-22):** `clinic_info.address`, `parking`, `insurers_accepted`, `insurance_note`, `insurer_aliases`, `services`, `languages`, `payment`, `new_patients`, `provider_bios`. The `get_clinic_information` tool returns these texts with no LLM rewriting. Rules: every text ≤ 300 characters, no placeholders, list items ≤ 60 characters, and `provider_bios` keys must be existing providers.
- **Emergency rules (P0-03):** `rules_version`, `status` (`draft` → `clinic_reviewed` → `approved`), `reviewed_by`, `reviewed_on`, `categories[]` (`id`, `tier` 1/2/3, `label`, `phrases`, `all_of_groups`), `tier_actions` and `scripts[]` (`id`, `text`). Production activates only `approved` rules (P1-19 rule, DECISIONS #14). Changes go through a release PR with prod approvals and the dentist's sign-off reference (P1-19 §6, P5-15).
- **Open Dental lists (P1-15):** `OpenDentalSetup.providers()` and `operatories()` (cached), and schedules with `blockout_def_num` / `blockout_name`. **Verify:** how to list blockout types (definition category 25) through the API, e.g. `GET /definitions?Category=25`. Until verified, the blockout picker lists only the blockout types seen in the next 30 days of schedules.
- **Console shell (P4-09):** `NAV` registry, `<Can>`, `useConfig()`, `SaveAndPublishDialog` (diff + change note), field error mapping, MSW mocks.

New glossary terms: availability preview, change request (config), visit length source.

## 4. Scope
**In scope**
- Four console pages and their `NAV` entries.
- Backend:
  - `GET /v1/admin/opendental/lookups` (providers, operatories, blockout types);
  - `POST /v1/admin/config/preview-availability`;
  - `/v1/admin/change-requests` (create, list);
  - a `section` filter on the config diff.
- P1-20 additive: `AvailabilityService.preview_counts()`, a side-effect-free count for a candidate config.
- P1-19 additive: allow `duration_min` edits only for variants without `od_appointment_type_num`; the `section` diff filter.
- DB: `config_change_requests` table (additive to P1-03).
- Permission `config:request` (additive to P1-13): ADMIN, DENTIST.
- Notification email for change requests (IDs only) through the P2-23 email sender.
- Tests, including "a published change is used by the next availability search without a redeploy".

**Out of scope** (and which task covers it)
- Editing emergency rules, verification or privacy in the console → never; file + release PR (P1-19, P5-15)
- Adding reason codes, variants or age ranges → file change by the project team (P0-02 process)
- Hours, holidays, profile → P4-09
- WhatsApp, reminder, voice and callback settings → P4-13
- Changing Open Dental appointment types or their length → done in Open Dental by the clinic
- Applying a change request → project team, outside the console (runbook)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P4-09 Shell (approved spec) | Layout, `NAV`, `<Can>`, `useConfig`, `SaveAndPublishDialog`, MSW | — |
| P1-19 Config (approved spec) | Config API, edit matrix, rules, `cfg:changed` | MSW handlers with `seed/example-dental` (including the full P0-02 example file and the P0-03 example) |
| P1-20 Availability (approved spec) | Slot computation | `preview_counts` is added here; unit-test it with the P1-20 fake Open Dental fixtures |
| P1-15 Open Dental (approved spec) | Providers, operatories, blockout types | The P1-15 fake setup cache |
| P1-22 (approved spec) | `clinic_info` model and rules | — |
| P0-02 / P0-03 (approved specs) | Schemas and example files | — |
| P2-23 Email (approved spec) | Sending a notification email | Log-only sender in dev |

## 6. Interface contract

### 6.1 Pages and permissions
| Route | View | Edit |
|---|---|---|
| `/admin/settings/appointment-types` | `config:read` | `config:write` |
| `/admin/settings/booking-rules` | `config:read` | `config:write` |
| `/admin/settings/clinic-info` | `config:read` | `config:write` |
| `/admin/settings/emergency-rules` | `config:read` or `config:request` | — (view only); **Request a change** needs `config:request` |

`NAV` additions (P4-09 registry): "Appointment types", "Booking rules", "Clinic info" and "Emergency rules", all in the group "Clinic settings", `ownerTask: "P4-11"`. The DENTIST role (no `config:read`) sees only "Emergency rules", because it has `config:request` and views the page through it.

### 6.2 Appointment types page
For each reason (fixed order from the file):

```
┌ Cleaning and checkup (recall_cleaning) ──────────────────────── [AI books ●] ┐
│ When AI can't book: (•) Ask our team to call back  ( ) Say we don't offer it online │
│ Variant                 Visit type (Open Dental)   Length    Providers          Rooms        On │
│ Existing, 18+           Recall                    60 min🔒   [HYG1 ✕][HYG2 ✕] [Op 2 ✕][Op 3 ✕]  ● │
│ Existing, 3–17          Child Recall              40 min🔒   [HYG1 ✕]          Any room       ● │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Field | Editable | Control | Rule |
|---|---|---|---|
| `bookable_by_ai` | yes | toggle | — |
| `when_not_bookable` | yes | radio | `callback` \| `not_offered` |
| variant `enabled` | yes | toggle | At least one enabled variant when `bookable_by_ai` (else a P1-19 error) |
| `providers` | yes | multi-select from lookups (name + abbreviation; hidden providers excluded) | ≥ 1 when enabled |
| `operatory_nums` | yes | multi-select from lookups, or "Any room" | — |
| `duration_min` | only if `od_appointment_type_num` is null | number, step = `od_time_increment_min` | 10–240 |
| length (typed variant) | no | 🔒 with tooltip "Set by the Open Dental appointment type '<od_name>'" | — |
| label, patient types, ages, Open Dental type | no | text | "Contact the project team to change" |

- `emergency_exam` shows a note: "Used only for urgent (Tier 2) bookings."
- `other` is always `bookable_by_ai: false` (P0-02 rule; toggle disabled).
- Saving sends one merge-patch for `appointment_types` with only the changed reasons, through `SaveAndPublishDialog`. The diff reads, for example, "Cleaning and checkup: providers HYG1, HYG2 → HYG1" or "Whitening consult: AI books on → off".

### 6.3 Booking rules page
| Field | Control | Range / options |
|---|---|---|
| `scheduling.booking_horizon_days` | number + "days ahead" | 1–365, default 7 |
| `scheduling.min_lead_minutes` | number + unit (minutes/hours) | 0–1440 |
| `scheduling.min_lead_minutes_urgent` | same | 0–240 |
| `scheduling.options_per_offer` | radio | 2 \| 3 |
| `scheduling.reserved_blockouts.new_patient` | multi-select of blockout types | from lookups |
| `scheduling.reserved_blockouts.emergency` | multi-select of blockout types | from lookups; the same type can't be in both |
| `scheduling.other_blockouts_block_booking` | toggle | default on |
| `policies.cancel_min_notice_hours` | number | 0–168 |
| `policies.reschedule_min_notice_hours` | number | 0–168 |
| `policies.inside_notice_action` | radio | `callback` ("Ask our team to call") \| `allow` |
| `policies.new_patient_auto_create` | toggle | — |
| `verification.*` | read-only box | "Patients are identified by full name and date of birth, plus one of mobile phone or ZIP code. Max 3 attempts. These rules are fixed for safety." |

Ranges not already in P1-19 are **Proposed** here and added to P1-19's rules (additive), so the server enforces them too.

Helper texts explain each field in plain words, e.g. for the horizon: "The AI books up to this many days from today. Patients asking for a later date are offered a callback."

### 6.4 Clinic info page
- Address fields, parking, insurance note, payment and new-patient note: textareas with live counters (≤ 300).
- Insurers, services and languages: tag lists (item ≤ 60).
- Insurer aliases: per insurer, a tag list of other names.
- Provider bios: one textarea per active provider from lookups (≤ 300).
- Banner: **"Patients see this text exactly as written. Don't include patient information."**
- Preview pane: shows how the AI would answer "Do you take Delta Dental?" or "Where do I park?", rendered by the same code as `get_clinic_information` (P1-22), with no LLM call.

### 6.5 Emergency rules page (view only)
- **Header:** `rules_version`, status badge (Approved / Clinic reviewed / Draft), "Reviewed by Dr. A. Smith on Dec 12, 2026", and "Changes need a dentist's approval and are made by the project team."
- **Categories table:** grouped by tier (Tier 1: "AI tells the patient to call 911", Tier 2: "urgent visit", Tier 3: "routine"), showing label, phrases, and "all-of" groups rendered as "swelling/swollen/puffy **and** eye/neck/throat".
- **Scripts:** the exact text the AI says, per script ID, with `{clinic_name}` shown as the clinic's name.
- **History:** versions where `emergency_rules` changed (`GET /v1/admin/config/versions` + `diff?section=emergency_rules`), with who imported, the note (which includes the dentist sign-off reference) and the diff.
- **Request a change** (needs `config:request`): a dialog with
  - **what** (`add_phrase`, `remove_phrase`, `change_tier`, `change_script`, `other`),
  - a free-text **description** (≤ 2000 characters, with the warning "Don't include patient names or details"),
  - and a checkbox "A dentist at our clinic agrees with this request" (recorded, not a sign-off).

  It creates a change request; the list below shows the clinic's requests with status.

### 6.6 Backend endpoints
```
GET  /v1/admin/opendental/lookups                          Permission config:read
200 {"providers":  [{"prov_num": 4, "abbr": "HYG1", "name": "Amy Ray", "is_hygienist": true, "hidden": false}],
     "operatories":[{"op_num": 2, "name": "Op 2", "hidden": false}],
     "blockout_types": [{"def_num": 31, "name": "New patients"}, {"def_num": 32, "name": "Emergency"}],
     "blockout_source": "definitions" | "schedules_30d",
     "as_of": "2026-12-08T17:00:00Z"}
     (from the P1-15 setup cache; hidden items are returned flagged so existing selections still display)

POST /v1/admin/config/preview-availability                 Permission config:write; rate limit 6/min per clinic
{"base_version": 12, "changes": {"appointment_types": {…}, "scheduling": {…}},
 "reason_codes": ["recall_cleaning", "toothache"]}         (max 6; default = reasons touched by changes)
200 {"window_days": 7, "items": [
       {"reason_code": "recall_cleaning", "patient_type": "existing", "current": 14, "proposed": 0},
       {"reason_code": "recall_cleaning", "patient_type": "new",      "current": 3,  "proposed": 3}],
     "warnings": ["Cleaning and checkup (existing): no openings in the next 7 days with the new settings."]}
422 invalid candidate config (same error format as PATCH)   409 stale base_version   503 Open Dental unavailable

POST /v1/admin/change-requests                             Permission config:request
{"section": "emergency_rules", "kind": "add_phrase", "description": "...", "dentist_agrees": true}
201 {"id": "uuid", "status": "OPEN"}
GET  /v1/admin/change-requests?section=emergency_rules     Permission config:read or config:request
200 {"items": [{"id", "section", "kind", "status", "created_by", "created_at", "resolved_at", "resolution_note"}]}
     (the description is returned only to the creator and ADMIN)
```
- The **preview** uses `AvailabilityService.preview_counts()` (§6.7), not `find()`. It stores no offers, no slot locks and no session.
- On a change request, the backend sends an email through the P2-23 sender to `CONFIG_CHANGE_REQUEST_EMAIL` (env, the project team's address). The subject is "Config change request <id> (<clinic slug>, emergency_rules)" and the body has only a console link and the kind. The description is **not** in the email.

### 6.7 P1-20 addition: `preview_counts`
```python
class PreviewItem(BaseModel):
    reason_code: str
    patient_type: Literal["new", "existing"]
    current: int
    proposed: int

class AvailabilityService:
    async def preview_counts(self, ctx: ClinicODContext, *, current: ClinicConfig, proposed: ClinicConfig,
                             reason_codes: list[str], window_days: int = 7) -> list[PreviewItem]: ...
    # For each reason and patient type, select the variant (adult age 30 for "existing", 30 for "new"; children
    # variants counted with age 8), run the same slot computation as find() over [now + min_lead, now + window_days]
    # (capped by booking_horizon_days), and count distinct start times. Reads schedules with Priority.INTERACTIVE
    # and the P1-15 cache; never writes Redis offers or locks.
```

### 6.8 DB and permission additions
`config_change_requests` (additive to P1-03):

| Column | Type | Constraints | PHI |
|---|---|---|---|
| `id` | uuid | PK | - |
| `clinic_id` | uuid | FK | - |
| `section` | text | `emergency_rules`, `verification`, `privacy`, `appointment_types_structure` | - |
| `kind` | text | `add_phrase`, `remove_phrase`, `change_tier`, `change_script`, `other`; **addition (P6-01, DECISIONS #280):** `pilot_enable` (second-person approval to switch a pilot channel on or change `ai_hours` / `unlisted_only`) | - |
| `description_enc` | bytea | NOT NULL; field-level encrypted (P1-05 KMS), because staff might type patient details despite the warning | P (possible) |
| `dentist_agrees` | bool | NOT NULL | - |
| `status` | text | `OPEN`, `IN_REVIEW`, `DONE`, `REJECTED` | - |
| `created_by` | uuid | FK `staff_users` | - |
| `resolution_note` | text | NULL; written by the project team (no PHI) | - |
| `created_at`, `resolved_at` | timestamptz | | - |

- The project team updates the status with the ops CLI: `python -m app.cli change-request resolve <id> --status DONE --note "Applied in config v14 (PR #…)"`.
- Audit: `config.change_request.create` and `.resolve`.
- **P1-13 permission:** `CONFIG_REQUEST = "config:request"` for ADMIN and DENTIST.

## 7. Implementation guide
1. **Read** P4-09 (shell components), P1-19 (edit matrix, rules, API, pinning), P0-02 (mapping schema and rules), P0-03 (rules schema), P1-20 (`find` steps, variant selection), P1-22 (`clinic_info`, `get_clinic_information` rendering) and P1-15 (setup cache).
2. **Verify** the blockout-types source (§3) and record it in `docs/integrations/open-dental-api-facts.md`.
3. **P1-19 additive:** allow `duration_min` edits only when `od_appointment_type_num` is null; add the ranges from §6.3 not yet present; add `section` to `GET /v1/admin/config/diff`. Add the tests.
4. **P1-20 additive:** `preview_counts()` built from the same internal functions as `find()` (refactor the shared part; no copy-paste), plus tests that preview and `find` agree on a fixture.
5. **Backend endpoints** (§6.6) with permissions, rate limit and clinic scope; the change-request table and CLI.
6. **Pages:** Appointment types, then Booking rules, Clinic info and Emergency rules, with `NAV` entries and MSW mocks.
7. **Check availability:** a button on Appointment types and Booking rules. It calls preview with the unsaved changes and shows a table plus warnings. Publish stays allowed after a warning, but the dialog repeats it: "Cleaning will have no openings."
8. **No-redeploy test** (§10 I1).
9. **Docs:** `docs/admin/settings.md` (what each field does, in plain words) and `docs/runbooks/config-change-requests.md`.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Admin removes the last provider of an enabled variant | Client blocks it; the server rule (P1-19) also rejects it with a field error. |
| A selected provider was hidden in Open Dental | Shown with a "hidden in Open Dental" tag. The P1-19 `od_check` warning is shown. The admin can remove it. |
| Admin tries to edit the length of a typed variant | Not possible (🔒). A crafted PATCH → 403 `config_section_locked`. |
| `bookable_by_ai` on but every variant disabled | Field error "Turn on at least one variant or stop AI booking for this reason." |
| Preview shows 0 openings for a reason | Warning in the table and in the publish dialog; publishing is still allowed (the clinic may want it). |
| Preview while Open Dental is down | "Couldn't check availability right now." Publishing is still allowed. |
| Preview called too often | 429 with `Retry-After` (Open Dental rate budget). |
| Same blockout type picked for new patients and emergency | Client blocks it; the server rule also rejects it. |
| Horizon set to 365 | Allowed. Helper text: "Long horizons mean more requests to Open Dental per search." (P1-20 searches progressively.) |
| Clinic info text contains "{…}" or > 300 chars | Field error (P1-22 rules). |
| DENTIST opens Emergency rules | Can view and request changes; no other settings pages in the menu. |
| FRONT_DESK opens Emergency rules | Can view (`config:read`); no Request button. |
| Someone tries to PATCH `emergency_rules` via the API | 403 `config_section_locked` (P1-19 T18). |
| An imported rules file has `status: clinic_reviewed` in prod | Activation refused by P1-19; the page keeps showing the active approved version. |
| Session in progress while the admin publishes | That session keeps its pinned config. New sessions use the new one (P1-19 pinning). |
| Change request description contains a patient name | Stored encrypted; not in the email; visible only to the creator and ADMIN. |

## 9. Security, HIPAA and PHI
- **PHI:** the settings themselves contain none (clinic and provider data). The only possible PHI is free text a staff member types into a change request. It is encrypted at rest, kept out of emails and logs, and shown only to the creator and ADMIN.
- **Preview** reads Open Dental schedules (which include appointments) but returns **counts only**. It never returns patient names, times or AptNums, and nothing is stored.
- **Safety:** the emergency rules, verification and privacy sections stay locked to the reviewed file process. "Unapproved rules never go live" is enforced by P1-19 (prod activates only `approved`). This task adds no path around it, and a test proves the console API can't change them.
- **Access:** `config:write` (ADMIN) for edits, `config:request` (ADMIN, DENTIST) for requests, and clinic scope on every query.
- **Audit:** `config.version_created` / `config.activated` (P1-19), `config.preview` (counts only, no details), `config.change_request.create` / `.resolve`.
- Logs never contain clinic info texts or change-request descriptions.

## 10. Testing
**Unit** (frontend, Vitest):
- **F1:** the mapping form produces a minimal merge-patch (only changed reasons).
- **F2:** typed-variant length is locked and untyped is editable.
- **F3:** validation messages for empty providers or all variants off.
- **F4:** booking-rule ranges.
- **F5:** the clinic-info counters and the 300 limit.
- **F6:** emergency rules rendering (tiers, all-of groups, scripts).
- **F7:** `NAV` for DENTIST shows only Emergency rules under settings.

**Backend** (pytest):

| # | Case | Expected |
|---|---|---|
| B1 | PATCH `appointment_types` providers by ADMIN | 201; new version; diff shows the provider change |
| B2 | PATCH `duration_min` on a typed variant | 403 `config_section_locked` |
| B3 | PATCH `duration_min` on an untyped variant within range | 201 |
| B4 | PATCH `emergency_rules` | 403 |
| B5 | FRONT_DESK PATCH anything | 403 |
| B6 | `preview_counts`: removing the only provider's operatory | `proposed` = 0, warning present |
| B7 | `preview_counts` and `find()` on the same fixture and config | Same set of start times |
| B8 | Preview writes nothing to Redis (no offers, no locks) | Redis key count unchanged |
| B9 | Change request by DENTIST | 201; audit; email has no description |
| B10 | Change request listing as FRONT_DESK | Description omitted |
| B11 | `lookups` excludes other clinics; hidden providers flagged | — |

**Integration:**
- **I1 (no redeploy):** start the API; ADMIN turns `recall_cleaning` `bookable_by_ai` off and publishes; a **new** patient session searching for a cleaning gets the `not_bookable` path; a session started before the change keeps the old config. No restart in between.
- **I2:** importing an emergency rules file with `status: clinic_reviewed` in a prod-like env is refused, and the viewer still shows the previous approved version.

**E2E** (Playwright):
- **E1:** ADMIN edits the providers of a reason → Check availability → publish → history shows the version.
- **E2:** DENTIST submits an emergency change request and sees it in the list as OPEN.
- **E3:** READ_ONLY sees all settings pages disabled.

```bash
cd backend && pytest tests/unit/admin tests/unit/availability/test_preview.py tests/integration/admin -q
cd frontend && pnpm test && pnpm test:e2e -- settings
```

## 11. Acceptance criteria
- [ ] The availability engine picks up published mapping and booking-rule changes for new sessions without a redeploy (I1)
- [ ] Unapproved emergency rules never go live, and the console has no way to change them (B4, I2)
- [ ] Emergency rules, their history and diffs are viewable; ADMIN and DENTIST can submit change requests, which are stored, audited and notified without PHI in the email (B9, E2)
- [ ] Providers, operatories, AI booking on/off, fallback and variant on/off are editable from Open Dental-backed lists (B1, E1)
- [ ] Visit length is read-only for Open Dental-typed variants and editable only for untyped ones (B2, B3)
- [ ] Booking rules are editable within their ranges; the booking horizon defaults to 7 and accepts 1–365
- [ ] Check availability shows current vs proposed counts for the next 7 days, returns counts only and stores nothing (B6–B8)
- [ ] Clinic info is editable with the P1-22 limits and a "patients see this" warning
- [ ] Every change is a new audited config version; READ_ONLY and FRONT_DESK can't edit (B5, E3)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed
- [ ] No PHI in logs
- [ ] Docs / README updated (`docs/admin/settings.md`, change-request runbook)
- [ ] Blockout-types source verified and recorded
- [ ] Additive edits merged: P1-19 (duration rule, ranges, diff `section`), P1-20 (`preview_counts`), P1-03 (`config_change_requests`), P1-13 (`config:request`)

## 13. Hand-off
| Consumer | What it can rely on |
|---|---|
| P1-20 / P2-16 | Published mapping and rules arrive through P1-19 versions; no code change needed |
| P4-13 | `lookups` endpoint (provider names for activity views), `NAV` pattern, preview pattern for its own settings |
| P5-15 Emergency sign-off | Change requests list (`section=emergency_rules`) as the intake for rule changes |
| P4-17 / P6 | `docs/admin/settings.md` for clinic training |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| How to list Open Dental blockout types through the API (definition category 25)? | Developer (Verify) | Step 2 |
| Should the clinic's dentist be able to approve emergency rule changes inside the console later (a real approval workflow), instead of the file process? Proposed: not in the MVP; revisit after the pilot with the compliance advisor | Product owner + clinical lead | P6 review |

## 15. References
- Plan §7 (admin console), §4.6 (booking), §4.8 (emergency handling)
- DECISIONS #14, #86, #142, #152, #199, #262, #264
- Related tasks: P0-02, P0-03, P1-03, P1-13, P1-15, P1-19, P1-20, P1-22, P2-16, P2-20, P2-23, P4-09, P4-13, P5-15
