---
id: P2-15
title: New patient registration flow (collect, confirm with a card, create without duplicates)
milestone: P2
epic: E2.3
size: M
labels: area:ai, area:backend, type:feature, phi
depends_on: P0-01, P0-04, P1-16, P1-19, P1-22, P2-01, P2-04, P2-05, P2-08, P2-12
status: approved
---

# P2-15: New patient registration flow (collect, confirm with a card, create without duplicates)

## 1. Summary
Build the `REGISTER` state handler. It runs after P2-12 concludes the person is new (`match_none_confirmed`).
1. It collects the remaining details: mobile phone (already given in `IDENTIFY`), optional email and optional address, as the clinic's config says.
2. It shows the **registration card** with every detail and asks the patient to check it (DECISIONS #174).
3. On "yes" it calls `create_patient` through the P2-08 gateway. That path has three duplicate barriers: P1-22's search fingerprint, P1-16's pre-check, and Open Dental's own duplicate rule.
4. On success the new patient becomes the verified active patient, and the conversation returns to what they came for (usually booking).

Any duplicate risk or failed create ends in the same neutral callback: "our team will finish your registration".

Done means:
- a new patient is created once, with exactly the confirmed details;
- no record is ever created when anything similar exists or the result is uncertain;
- a parent can register a child in the same chat, and staff get a task to link the guarantor;
- the patient never learns that a similar record exists.

## 2. Why this matters
Plan §4.5: "No match → confirm spelling and DOB once more → new patient flow" and "**Never auto-create** a patient when the result is ambiguous." P0-01 B4: the AI creates the record immediately when there is no duplicate risk; any doubt goes to a callback and staff create it.

New patients are the clinic's growth, so registration must be quick, especially in chat at night. A duplicate chart splits treatment history and insurance, and staff must merge it by hand. Pilot targets helped: **0 duplicate patients** and ≥ 70% bookings without callback (a new patient can book in one conversation).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P2, Text Chat Receptionist**.
- **Guarantor:** in Open Dental, the person responsible for a patient's account. For a child it is usually a parent. We don't set it; staff do (DECISIONS #185). GLOSSARY "Guarantor".
- **What already exists:**
  - **P1-16** (approved): `create(ctx, NewPatient, idempotency_key)`. `NewPatient` has `first_name`, `last_name`, `birthdate`, `mobile_phone_e164` (required), and optional `email`, `address_line1`, `address_line2`, `city`, `state`, `zip_code`. The create path:
    - a pre-check by last name + DOB across all statuses except Deceased (a match on first or preferred name → `DuplicatePatientError`, no POST);
    - `POST /patients` with `TxtMsgOk: "Unknown"`;
    - Open Dental's 400 duplicate rule → `DuplicatePatientError`;
    - reconcile after `OpenDentalUncertainWrite`;
    - read-back verification.
    - Open Dental's default `PatStatus` is `Patient`.
  - **P1-22** (approved): `create_patient` tool. Its handler requires `cand.outcome == "no_match"` with the same `search_fp`, plus `policies.new_patient_auto_create`; otherwise `duplicate_risk`. It then calls P1-16 with key `create_patient:{session_id}` and on success `mark_verified`. Error codes: `duplicate_risk`, `outcome_unknown`, `od_unavailable`.
  - **P2-08** (approved): `create_patient` preconditions are not `verified`, `not_verification_locked` and `confirmation_recorded` (kind `register`, operation hash over the normalized details); budget 1 per person.
  - **P2-12** (approved): `match_none_confirmed`, `flags.new_patient_declared`, normalizers (`normalize_name`, `parse_dob`, `parse_phone`), household (`start_new_person`, person frames).
  - **P2-04** (approved): `confirm_registration` template and the `register` card (First name, Last name, Date of birth, Mobile phone, Email, Address; first row names the patient).
  - **P2-05** (approved): extraction of `email`, `address`, `mobile_phone`, and `confirmation` = `yes` / `no` / `change` + `change_target`.
  - **P1-19** (approved): `policies.new_patient_auto_create: true` (P0-01 B4). **Additive here:** a `registration` section.
  - **P0-04** (approved): `REGISTER` collects `email`, `address`, `mobile_phone`; tools `search_patient`, `create_patient`; create refused or ambiguous → `CALLBACK_REQUEST`.

## 4. Scope
**In scope**
- `backend/app/orchestrator/flows/register.py`: `RegisterHandler` (P2-01 `StateHandler`).
- **P1-19 extension:** `registration` section (console-editable).
- Reply intents and templates added to P2-04's catalogue.
- The minor (under 18) staff task request (`guarantor_link`) and the `registration_needs_staff` callback reason, as inputs to P2-22.
- **Additive P2-08 change:** `create_callback_request` with a staff-only reason (`guarantor_link`) needs no patient confirmation.
- Tests (handler, end-to-end with `od_fake`) and `docs/flows/register.md`.

**Out of scope** (and which task covers it)
- Identification and the decision that the person is new → P2-12
- Open Dental create, pre-check, reconcile → P1-16
- Callback case storage and admin email → P2-22
- Appointment booking after registration → P2-16 (new-patient variants via P1-20 `patient_type="new"`)
- WhatsApp consent → P4-02
- Insurance details, medical history forms → not in MVP (the clinic collects them at the visit)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-16, P1-22 (approved) | `create_patient` tool, errors | `od_fake` with the duplicate rule and write faults |
| P2-08 (approved) | Gateway, confirmation hash | Use the real gateway with fakes |
| P2-04, P2-05 (approved) | Card, templates, extraction | `FakeLlmProvider` scripted extraction |
| P2-12 (approved) | Entry event, flags, household | Enter `REGISTER` directly in tests with slots pre-filled |
| P2-22 (later) | `create_callback_request` real handler | P1-22 stub returns `not_available` → test asserts the request arguments |
| P1-19 (approved) | Config | Seed config plus the new section defaults |

## 6. Interface contract

### Config extension (P1-19): `registration`
```yaml
registration:
  ask_email: true            # ask once; the patient may skip
  ask_address: true          # ask once; the patient may skip
  address_required: false    # if true, no skip for address
  email_required: false      # if true, no skip for email
```
Console-editable (P4-11); optional section with these defaults, so `schema_version` stays 1. `policies.new_patient_auto_create` (file-only, P0-01 B4) still decides whether the AI may create at all.

### Handler flow (`register.py`)
```text
REGISTER.on_enter:
  if not config.policies.new_patient_auto_create:
      event create_refused (→ CALLBACK_REQUEST, reason registration_needs_staff); reply registration_staff_handoff
  mobile_phone := slots.phone (from IDENTIFY), unless the patient already gave a different mobile number
  reply ask for the next missing field (order: email, address), or show the card if none

REGISTER.on_turn(extraction):
  1. store email / address / mobile_phone values (P2-05 normalized); a "skip" / "no email" answer marks the field skipped
     (skip refused when *_required) → re-ask once with "this is required by the clinic"
  2. next missing field → ask (one at a time)
  3. all done → build PendingOperation(kind="register", details=normalized NewPatient fields)
     → reply confirm_registration with the register card (P2-04)
  4. confirmation == "change" + target → clear that field (or first/last name, DOB, mobile) → ask it again → new card
     (changing last name or DOB returns to IDENTIFY: a new search is needed for the duplicate barrier)
  5. confirmation == "yes" → tool call create_patient(first_name, last_name, dob, mobile_phone, email?, address?)
     result:
       ok                → mark_verified done by P1-22; household updated (P1-13)
                           if age < 18 → staff task guarantor_link (below)
                           event registered (→ resume the intent: APPOINTMENT_TYPE for book) ; reply registered_ok
       duplicate_risk    → event create_refused (→ CALLBACK_REQUEST); reply registration_staff_handoff
       outcome_unknown   → same as duplicate_risk (never retry a create with different data)
       od_unavailable    → event od_unavailable (global) → CALLBACK_REQUEST
       precondition_failed(not_verification_locked) → CALLBACK_REQUEST
```
- Event names `registered` and `create_refused` must match P0-04's YAML for `REGISTER` (P0-04 §8: "If create is refused or ambiguous → CALLBACK_REQUEST"). If the YAML uses other names, use those; add any missing name through P0-04's review.
- **Changing last name or DOB** goes back to `IDENTIFY`, because P1-22's `search_fp` must match the create input. Changing the first name, phone, email or address stays in `REGISTER`. P1-16's pre-check still compares the first name.
- The same `create_patient:{session_id}` idempotency key is used per person frame (`create_patient:{session_id}:{person}`). This is an additive change to DECISIONS #178's format, so a parent can register two children in one chat. P2-08's `idempotency_key()` takes `person`.

### Under-18 staff task (DECISIONS #189)
After a successful create, if the age at `today_local` (from DOB) is below 18:
```python
ToolCallRequest("create_callback_request", {
    "reason_code": "guarantor_link",          # staff-only: no call to the patient
    "urgency": "routine",
    "summary": "New minor patient registered by AI. Please link the guarantor (parent or guardian).",
})
```
- **No PHI in `summary`:** P2-22 attaches the PatNum and session from the server-side context.
- **P2-08 exception:** staff-only reason codes (`guarantor_link`) need no patient confirmation card, like the emergency exception. The admin email carries the case ID and link only (P0-01 B7).
- This runs for a minor whether or not a parent is in the household. A teen registering alone is allowed; staff follow up as usual.

### Callback reasons provided to P2-22
| `reason_code` | When | Patient told |
|---|---|---|
| `registration_needs_staff` | `duplicate_risk`, `outcome_unknown`, auto-create disabled, locked session | "Our team will finish your registration and call you back." |
| `guarantor_link` | Minor registered | Nothing extra (staff-only) |

For `registration_needs_staff`, the callback flow (P2-22) shows its own callback card with name, phone and preferred callback time before creating the case. The booking preference already collected (`preferred_time`, `reason_code`) is attached, so staff can book on the call.

### Reply intents and templates (added to P2-04)
| Intent | Text |
|---|---|
| `register_intro` | "Welcome! I'll just need a few details to set you up as a new patient." |
| `register_ask_email` | "What's your email address? You can say skip if you'd rather not share it." |
| `register_ask_address` | "And your home address, with ZIP code? You can say skip." |
| `register_required_field` | "The clinic needs your {field} to register you. Could you share it?" |
| `confirm_registration` | (P2-04, with the `register` card) |
| `registered_ok` | "You're registered, {first_name}. Let's find you an appointment." |
| `registration_staff_handoff` | "I'm not able to finish your registration here, but our team will complete it and call you back." |

All are templates (no LLM text).

### Open Dental status of the new record (DECISIONS #188)
- Created with Open Dental's default `PatStatus` = `Patient` (P1-16 sends no `PatStatus`), so the patient is found and verified as existing next time (P1-19 `existing_patient_statuses: [Patient, Inactive]`).
- `Prospective` is **not** used: P2-12 treats it as `blocked_status`, which would send every returning visit to a callback.
- New-patient appointments are flagged for staff review through P1-16's "AI-booked" note (P0-01 Q2).
- **Verify with the clinic (P0-01 follow-up):** that `Patient` is how their front desk creates new patients.

### Logs and metrics (no values)
| Item | Fields |
|---|---|
| `register.step` (debug) | `step` (`ask_email` / `ask_address` / `card` / `create`), `skipped` (field names), `turn_seq` |
| `register.outcome` (info) | `result` (`created` / `duplicate_risk` / `outcome_unknown` / `disabled` / `od_unavailable`), `minor` (bool), `person` (index) |
| `dai.register.outcome` (counter) | `result` |

## 7. Implementation guide
1. **Config.** Add `registration` to P1-19 (model, defaults, console API exposure for P4-11).
2. **Handler.** Implement `RegisterHandler` per §6; register it in P2-01. Use P2-12's normalizers for any corrected values.
3. **Card and hash.** Build the `register` card through P2-04 with `PendingOperation(kind="register")`. The details are the normalized `NewPatient` fields, so the P2-08 hash matches the tool input exactly.
4. **Idempotency per person.** Extend P2-08's `idempotency_key("create_patient", session_id=…, person=…)`. Update P1-22's handler call. Add the DECISIONS row (#190).
5. **Minor task.** After `registered`, compute the age and send the `guarantor_link` request. Add the staff-only exception to P2-08's precondition table.
6. **Events.** Confirm `registered` / `create_refused` names in the YAML, or add them through P0-04's review.
7. **Templates.** Add §6 templates to P2-04.
8. **End-to-end tests** with `od_fake` (§10).
9. **Docs and notifications.** `docs/flows/register.md` (Mermaid diagram, failure branches). Notify P2-22 (reasons, staff-only exception), P2-16 (resume after `registered`, `patient_type="new"`), P4-11 (config screen), P1-16 owners (status verify), P5-08.

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| Pre-check finds a similar patient | `duplicate_risk` → neutral handoff → callback; nothing created; patient not told why |
| Open Dental's own duplicate rule rejects the POST | Same as above (`DuplicatePatientError`) |
| Network drop after Open Dental created the record | P1-16 reconcile finds it → success (one record); if still unknown → `outcome_unknown` → callback, no second create |
| Patient taps yes twice | Second yes finds the confirmation consumed; P1-22 key replays the first result; one record |
| Patient changes last name on the card | Back to `IDENTIFY` for a fresh search (duplicate barrier), then a new card |
| Patient changes email on the card | Field cleared, re-asked, new card |
| Patient refuses to give a required address (`address_required: true`) | Asked once more; second refusal → `registration_staff_handoff` callback |
| `new_patient_auto_create: false` | Immediate handoff to callback with the booking preference attached |
| Parent registers two children | Separate person frames, separate cards, keys `create_patient:{session}:{person}`; each minor gets a `guarantor_link` task |
| Child's mobile phone is the parent's | Allowed; Open Dental's duplicate rule compares name + DOB + email/phone, so different names and DOBs don't collide (**Verify** in the P1-16 spike) |
| Email invalid | P2-05 marks it invalid → asked again |
| Voice: address hard to capture | Patient may skip (default); staff complete it at the visit |
| Session locked (P2-12) | `create_patient` denied → callback |
| Patient asks "do you already have me on file?" | Same neutral reply as any identification failure; never confirmed |

## 9. Security, HIPAA and PHI
- **PHI handled:** first and last name, DOB, mobile phone, email, address of the new patient. These live in encrypted slot memory (P2-01) in the active person frame, are shown back to the patient on the card in their own session, and are sent to Open Dental through P1-16 (clinic BAA).
- **Stored by us:** only the PatNum (P1-13 household, `sessions.verified_patnum`) and the idempotency row (P1-16). No copy of the details.
- **Never logged:** any field value; logs carry steps, skipped field **names**, outcome codes.
- **No oracle:** duplicate risk, uncertain outcome and disabled auto-create all produce the same handoff wording (P2-12 principle).
- **Callback summary:** fixed text without PHI; P2-22 links the case to the session server-side.
- **Audit:** `patient.create` (P1-22) on success; `callback.create` for the handoff and the staff task.

## 10. Testing
```bash
cd backend && pytest tests/unit/orchestrator/flows/test_register.py -q
pytest tests/integration/register -q          # od_fake with duplicate rule and write faults
```
| # | Case | Expected |
|---|---|---|
| T1 | Happy path: email and address given → card → yes | One patient in `od_fake` with exactly the card's details; `registered`; intent resumes |
| T2 | Email and address skipped | Created with name, DOB, mobile only |
| T3 | `address_required: true` with refusal twice | Handoff callback |
| T4 | Duplicate check before create: similar record seeded | `duplicate_risk`; no POST; neutral handoff |
| T5 | Open Dental duplicate 400 | Same as T4 |
| T6 | Uncertain write, record created | Reconciled; exactly one record |
| T7 | Uncertain write, unknown | `outcome_unknown` → callback; no second create |
| T8 | Double yes | One record |
| T9 | Change first name on card | Re-asked; new card; new hash; old yes invalid |
| T10 | Change last name or DOB on card | Back to `IDENTIFY`; new search before a new card |
| T11 | Minor registered | `guarantor_link` request sent without a card; `summary` has no PHI |
| T12 | Parent registers two children | Two records; per-person keys; two `guarantor_link` tasks |
| T13 | `new_patient_auto_create: false` | Handoff immediately; no create |
| T14 | No-oracle: duplicate vs uncertain vs disabled | Identical patient-facing replies |
| T15 | Log capture with the PHI corpus | No field values |

## 11. Acceptance criteria
- [ ] A new patient is created once, with exactly the details on the confirmed card (T1, T2, T8, T9)
- [ ] Duplicate check before create: any similar record or Open Dental duplicate rule leads to a callback, never a record (T4, T5)
- [ ] Ambiguous or uncertain results fall back to a callback and never create twice (T6, T7)
- [ ] Changing last name or DOB forces a fresh search (T10)
- [ ] Minors are registered and staff get a `guarantor_link` task; a parent can register several children in one chat (T11, T12)
- [ ] The clinic's `registration` config and `new_patient_auto_create` are respected (T3, T13)
- [ ] Patient-facing replies don't reveal why registration was handed off (T14); no PHI in logs (T15)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review: labelled `phi`)
- [ ] No PHI in logs
- [ ] `docs/flows/register.md` written; P1-19, P2-04, P2-08 updates merged; YAML event names confirmed
- [ ] P2-16, P2-22, P4-11 and P5-08 issues notified; clinic asked to confirm the `Patient` status

## 13. Hand-off
| Consumer | What they can rely on |
|---|---|
| P2-16 Booking | After `registered`, the active patient is verified and new (`patient_type="new"`, `is_new_patient=True`) |
| P2-22 Callback | Reasons `registration_needs_staff` (with booking preference) and `guarantor_link` (staff-only, no card) |
| P4-11 Console | `registration` config fields |
| P5-08 Security tests | No-oracle handoff, duplicate barriers |

## 14. Open questions
| # | Question | Recommended answer | Owner |
|---|---|---|---|
| 1 | Should we ask for insurance at registration? | No: P0-01 Q6 says the AI only lists insurers; coverage is handled by staff at the visit. | Product owner |
| 2 | Should a teen registering alone be stopped? | No: register, and the `guarantor_link` task lets staff contact the family. | Clinic |
| 3 | Should we capture "how did you hear about us"? | No for the MVP; it adds a question without helping the booking. | Product owner |

## 15. References
- Plan: §4.5, §4.9, §6
- P0-01 B4 (auto-create), Q2 (AI-booked flag), B7 (admin email content)
- Open Dental API Patients: https://www.opendental.com/site/apipatients.html
- DECISIONS: #174, #178, #181, #185, #187, #188, #189, #190
- Related tasks: P0-01, P0-04, P1-13, P1-16, P1-19, P1-22, P2-01, P2-04, P2-05, P2-08, P2-12, P2-16, P2-22, P4-11, P5-08
