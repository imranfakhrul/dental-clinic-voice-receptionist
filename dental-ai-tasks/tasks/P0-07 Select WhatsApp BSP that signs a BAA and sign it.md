---
id: P0-07
title: Select patient-messaging provider that signs a BAA and sign it
milestone: P0
epic: E0.2
size: S
labels: area:compliance, area:messaging, type:chore
depends_on: P0-07a
status: approved
---

# P0-07: Select patient-messaging provider that signs a BAA and sign it

> Narrowed from the seed "Select WhatsApp BSP that signs a BAA and sign it". The channel decision moved to P0-07a, because Meta states the WhatsApp Business Platform is not HIPAA compliant (DECISIONS #35, #36). The ID is kept because P0-15 and P4-01 depend on it.

## 1. Summary
Using the channel(s) approved in P0-07a (`docs/compliance/messaging_policy.yaml`):
- compare at least three providers against fixed criteria;
- choose one;
- get its BAA signed, with the chosen channel explicitly covered;
- record the BAA the same way as the Google Cloud BAA (P0-05);
- open a **sandbox/test account with no PHI** so P0-15 and P4-01 can start.

Done means: the BAA is signed and recorded, the provider's coverage evidence is saved, the comparison is in the repo, and the test credentials are handed to the tech lead (not committed).

## 2. Why this matters
Confirmations and reminders (plan §2 #9–10, §4.7) go through an outside messaging provider. Under HIPAA and the plan's compliance gate (§3.3), no PHI may reach that provider until a BAA covering **that specific product** is signed. Providers often sign BAAs only for some products or editions: Twilio, for example, lists SMS but not WhatsApp, and requires its Security or Enterprise Edition. Picking the wrong product or edition would make every reminder a compliance problem.

The choice also fixes practical constraints for P0-15 (sender registration lead time), P4-01 (API and webhook format) and P4-06 (signature verification, retries). Patients and staff see the result through reliable delivery and working "STOP" handling.

Plan references: §2 #9–10 and #15, §3.3, §4.7, §12 (risk: provider won't sign a BAA).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P0, Discovery & Compliance Foundation**.
- **P0-07a decision:** which channel (SMS, WhatsApp in some form, email) may carry which message type, and which fields are allowed. It is recorded in `docs/compliance/messaging_policy.yaml`. This task only buys what P0-07a allowed.
- **BAA coverage list:** providers publish which products their BAA covers (e.g. Twilio's "HIPAA Eligible Services", https://www.twilio.com/en-us/hipaa). A BAA on the account doesn't cover products missing from that list.
- **US SMS sender registration:** business texting from US long-code numbers generally requires A2P 10DLC brand and campaign registration; toll-free numbers need verification. Both take time. **Verify** the current process and timing with each shortlisted provider.
- **Delivery webhooks and signatures:** providers call our endpoint with status updates (sent, delivered, failed, inbound "STOP"). Each request is signed so we can reject fakes (P4-06).
- **BAA record format:** the same as `docs/compliance/baa-google-cloud.md` (P0-05); P0-10 imports it into the vendor matrix.

## 4. Scope
**In scope**
- A comparison of at least 3 providers per approved channel, against the criteria in §6.
- The choice, signing the BAA (by someone with authority), and saving the BAA and the coverage evidence.
- `docs/compliance/baa-<vendor>.md`, `docs/integrations/messaging-provider.md`.
- A sandbox/test account with no PHI. Test credentials go to the tech lead through the password manager.
- Listing the sender-registration steps and lead times for P0-15.

**Out of scope** (and which task covers it)
- Which channel and content are allowed → P0-07a
- Registering the sender, numbers and templates → P0-15
- Storing production credentials in Secret Manager → P1-05
- The provider adapter, webhooks, retries, opt-out → P4-01, P4-06, P4-07
- Vendor matrix document → P0-10

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P0-07a Messaging decision | The approved channel(s) and conditions (`messaging_policy.yaml`) | Build the comparison for **SMS** (the Proposed default) and, separately, for WhatsApp BSPs. Don't sign anything until P0-07a is signed. |
| P0-05 Google Cloud BAA record (approved spec, soft) | The BAA record format | Use the format from the P0-05 spec. |

## 6. Interface contract

### Comparison criteria (`docs/integrations/messaging-provider.md`)
| # | Criterion | Must / Should |
|---|---|---|
| 1 | Signs a BAA, and the approved channel's product is **listed** as covered (document URL + date) | Must |
| 2 | Edition or plan needed for the BAA, and its price | Must (recorded) |
| 3 | US sender options (10DLC, toll-free, short code; WhatsApp sender if approved) and registration lead time | Must |
| 4 | Delivery and inbound webhooks with documented request signing | Must |
| 5 | STOP / opt-out handling (provider-level and passthrough to us) | Must |
| 6 | Message-body retention: can bodies be redacted or deleted from provider logs? | Should |
| 7 | REST API + maintained Python SDK; sandbox / test credentials | Should |
| 8 | Status page / SLA; US data processing | Should |
| 9 | Price per message (US) at pilot volume | Should |

Score each provider with yes / no / partial plus evidence links. A provider failing any **Must** is out.

### BAA record (`docs/compliance/baa-<vendor>.md`)
Same fields as P0-05, plus:
```markdown
- Covered products relied on: <e.g. Programmable SMS> (coverage list URL, version/date, saved copy)
- Edition/plan required for BAA: <…>
- Channels allowed by P0-07a: <…> (messaging_policy.yaml decision_version <…>)
```

### What P4-01 / P0-15 can rely on (`docs/integrations/messaging-provider.md`, section "Integration facts")
| Item | Example value |
|---|---|
| Provider and product | Twilio Programmable SMS |
| API base / SDK | REST + official Python SDK (Verify version) |
| Webhook signature method | Provider's documented scheme (Verify exact header and algorithm) |
| Sandbox / test credentials | Location in the password manager (never in the repo) |
| Sender type and registration steps | e.g. A2P 10DLC brand + campaign; lead time |
| Opt-out behaviour | Provider auto-handles STOP? Passes it to our webhook? |

**Verify:** every row against the chosen provider's docs, with links.

## 7. Implementation guide
1. Read `messaging_policy.yaml` and the P0-07a memo. List the approved channel(s) and conditions.
2. **Shortlist ≥ 3 providers per channel.** Start from the P0-07a provider check. For each, save its HIPAA/BAA page and coverage list (dated) under `docs/compliance/sources/`.
3. **Score them** against §6, with links. Ask sales in writing for anything not published (BAA template, edition price, coverage of the exact product).
4. **Choose** with the tech lead, and record the reasons in `messaging-provider.md`. Log the choice in DECISIONS.md.
5. **Sign the BAA** (signed by the person with authority, as in P0-05). Get the provider's countersigned copy. Check the BAA text names, or incorporates by reference, the coverage list that includes our product.
6. **Record** `docs/compliance/baa-<vendor>.md`.
7. **Open a sandbox/test account.** No PHI, ever; test messages go only to team members' phones with fake content. Put the credentials in the company password manager and give them to the tech lead. Never commit them.
8. **Write "Integration facts"** for P4-01 and the registration steps for P0-15.
9. **Notify** P0-10 (matrix), P0-15 (registration), P4-01 and P4-06 (API, webhooks), and P1-05 (production secrets later).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| A provider signs a BAA but the approved channel isn't on its coverage list | Fails Must #1. Exclude it, whatever sales say verbally. |
| The BAA needs an expensive edition | Record the cost; the sponsor decides. Don't use a non-BAA edition with PHI. |
| No provider meets all Musts | Stop. Go back to P0-07a for another option; record it in DECISIONS.md. |
| Sales can't share the BAA before purchase | Ask for a sample BAA. If unavailable, the advisor reviews it before signing anyway. |
| Sender registration lead time endangers the P4 schedule | Tell the sponsor; P0-15 starts registration with PHI-free content as soon as the provider is chosen. |
| The provider keeps message bodies in logs with no redaction option | Acceptable only under the BAA; record it in the vendor matrix and risk assessment (P0-11). Prefer providers that allow redaction. |
| Someone wants to test with a real patient's number | Not allowed. Test only with team phones and fake content. |

## 9. Security, HIPAA and PHI
- **No PHI is handled.** The sandbox only ever contains fake content sent to team phones.
- **The compliance gate:** no PHI may go to the provider until the BAA is signed **and** P0-09 (clinic BAA) and P0-10 (matrix) show it.
- **Credentials:** never in the repo or in tickets. The password manager now; Secret Manager in P1-05.
- **Audit:** not applicable here. Message sends are audited by P4-01 / P1-12.

## 10. Testing
No application code. Checks:
- The comparison table is complete: every cell has a value and an evidence link, and every excluded provider shows which Must it failed.
- Send one fake test message from the sandbox to a team phone and receive one delivery webhook (for example at a temporary request-inspection endpoint with no PHI). Record that it worked. This proves the "Integration facts" before P4-01 relies on them.
- A reviewer (tech lead + compliance advisor) checks that the BAA text covers the exact product used.

## 11. Acceptance criteria
- [ ] ≥ 3 providers per approved channel compared against all §6 criteria, with dated evidence
- [ ] The chosen provider meets every Must; the reasons are recorded and logged in DECISIONS.md
- [ ] The BAA is signed by both parties, and the chosen product is on the provider's coverage list (saved copy)
- [ ] `docs/compliance/baa-<vendor>.md` exists in the P0-05 format plus the extra fields
- [ ] Sandbox credentials are in the password manager (not the repo); one test message and one webhook were received
- [ ] "Integration facts" and the sender-registration steps are written for P4-01 and P0-15
- [ ] The P0-10, P0-15, P4-01, P4-06 and P1-05 issues are notified

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI: not applicable (no code); the §10 checks are recorded
- [ ] PR reviewed (HIPAA review if labelled `phi`): reviewed by the tech lead and the compliance advisor; no `phi` label because no PHI is handled
- [ ] No PHI in logs: none exists
- [ ] Docs / README updated: `messaging-provider.md` and the BAA record linked from `docs/`

## 13. Hand-off
| Task | Can rely on |
|---|---|
| P0-10 Vendor matrix | `baa-<vendor>.md` |
| P0-15 Sender registration / templates | Provider, sender type and registration steps; channel and fields from P0-07a |
| P4-01 Messaging adapter | "Integration facts", sandbox credentials (via the tech lead), `messaging_policy.yaml` |
| P4-06 Webhooks | Signature scheme and status values |
| P4-07 Opt-out | Provider STOP behaviour |
| P1-05 Secrets | The list of production secrets to create |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Budget ceiling for the BAA-eligible edition and per-message costs? | Project sponsor | Step 4 |
| Who signs the BAA (the same person as for Google Cloud)? | Company owner | Step 5 |
| If both SMS and WhatsApp are approved: one provider for both, or the best per channel? Proposed: one provider if it covers both under its BAA. | Tech lead | Step 4 |

## 15. References
- Plan §2 #9–10 and #15, §3.3, §4.7, §12
- P0-07a memo and `docs/compliance/messaging_policy.yaml`
- Twilio HIPAA: https://www.twilio.com/en-us/hipaa
- Meta Terms for WhatsApp Business Platform: https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform
- Related tasks: P0-05, P0-07a, P0-09, P0-10, P0-11, P0-15, P1-05, P4-01, P4-06, P4-07
