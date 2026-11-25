---
id: PX-NN
title: Short imperative title
milestone: PX
epic: EX.Y
size: S | M | L
labels: area:xxx, type:feature
depends_on: PX-NN, PX-NN
status: draft
---

# PX-NN: Short imperative title

## 1. Summary
Two or three sentences: what gets built and what "done" looks like.

## 2. Why this matters
Where this task sits in the system and what breaks or is blocked without it. Mention the user-visible effect (patient or clinic staff) if there is one. Cite plan sections (e.g. §4.5).

## 3. Background you need
Concepts, external systems and terms a newcomer must understand first, each explained in 1–3 sentences. Link the official docs. Add new terms to GLOSSARY.md.
Start with this standard paragraph, copied unchanged except for the phase (it keeps every issue self-contained):
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **PX, <phase name>**.

## 4. Scope
**In scope**
- …

**Out of scope** (and which task covers it)
- … → PX-NN

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| PX-NN | … | mock / stub / fixture / test credentials |

## 6. Interface contract
The exact public surface this task provides (and what it consumes): function signatures, data models, JSON schemas, endpoints, events, DB tables, config keys and error types. Include an example input and output.

## 7. Implementation guide
Numbered steps in the order a developer should do them, with file paths. Explain non-obvious choices. Mark our own choices "Proposed:" and anything unconfirmed about external APIs "Verify:".

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| … | … |

## 9. Security, HIPAA and PHI
Which PHI fields this task touches, where they flow, how they are protected, what must never be logged, and the audit events involved. If none: "No PHI" and why.

## 10. Testing
Unit tests, integration tests, test data or fixtures, and the commands to run them. List the specific cases.

## 11. Acceptance criteria
- [ ] Testable statement
- [ ] …

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed (HIPAA review if labelled `phi`)
- [ ] No PHI in logs
- [ ] Docs / README updated

## 13. Hand-off
Which tasks consume this work and exactly what they can rely on afterwards.

## 14. Open questions
Unresolved items with an owner. When resolved, move the answer into DECISIONS.md and update the spec.

## 15. References
Plan sections, official docs, related tasks.
