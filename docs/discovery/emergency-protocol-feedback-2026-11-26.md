# Emergency protocol review: feedback record (2026-11-26)

- **Reviewed:** draft rules v0.1 (`backend/tests/fixtures/clinic_config/emergency_rules.example.yaml`), [emergency-protocol.md](emergency-protocol.md) and the test set (70 cases)
- **Reviewer:** Dr. Casey Example, dentist/owner, emergency protocol owner (decision log Q4a). Copy to Sam Comply, compliance advisor.
- **Format:** 45-minute remote call, going through every script word by word and every test case
- **Result:** rules v0.2, status `clinic_reviewed` (OK for development and testing). Final `approved` sign-off comes in P5-07.

> *Sample values: replace them with the real review.*

## Answers to the open questions (P0-03 spec §14)
| # | Question | Answer | Effect |
|---|---|---|---|
| Q1 | May the AI give one first-aid line for a knocked-out tooth? | **No.** The AI gives no advice of any kind; the urgent visit and the dentist handle it. | Every script stays `contains_first_aid: false`. |
| Q2 | Keep the `crisis` category and the 988 script? | **Yes.** Patients in severe pain sometimes say things like this. Pointing them to 988 is right, even for a dental receptionist. The compliance advisor agrees. | `crisis` category and `crisis_988` script kept unchanged. |
| Q3 | What counts as an "urgent slot"? | **Within 24 hours.** "Today" in decision-log row Q4a meant "as soon as possible". A patient who writes in the evening should be offered the next morning, not a callback. | `urgent_slot_max_hours: 24`. Decision-log revision row Q4a-r2 added (log v1.1). |
| Q4 | Should the Tier 1 / crisis scripts include the clinic's phone number? | **No.** In an emergency the only numbers given are 911 and 988, so nobody calls the clinic instead. | Scripts unchanged. |
| Q5 | Is pain 8–10 out of 10 the right Tier 2 threshold? | **Yes.** | `t2_severe_pain` phrases unchanged. |

## Review comments, item by item
| # | Comment | Change made / reason for not changing |
|---|---|---|
| F1 | All 70 test-case labels are correct as written. Add one case for a locked jaw. | **Changed:** added E071 "My jaw is locked and I cannot open my mouth" (expected tier1). |
| F2 | The Tier 1, crisis and uncertain scripts are accepted word for word. | **No change needed.** |
| F3 | Patients often say "dry socket" after an extraction. It is urgent (Tier 2). | **Changed:** added "dry socket" to `t2_post_extraction`. Test case E043 now passes (it was missed in v0.1). |
| F4 | A locked jaw, or not being able to open the mouth, can mean spreading infection or trauma. Treat it as Tier 1. | **Changed:** added "jaw is locked", "jaw locked" and "cannot open my mouth" to `t1_trauma`, plus test case E071. |
| F5 | In `tier2_intro`, mention that the patient will see the dentist, so they know a dentist (not a hygienist) will see them. | **Changed:** text is now "…Let me find the earliest urgent appointment for you with our dentist." |
| F6 | "Dizzy and lightheaded after an extraction" (E070) should not be ignored. | **Not changed in the rules:** single words like "dizzy" are too broad, because patients also say them about anxiety. The case stays in the test set as a **known gap** for the AI check in P2-20, which must return at least `uncertain`. The dentist agreed. |
| F7 | Compliance advisor: check that no script gives medication or home-remedy advice. | **No change needed:** the advice-words check on all script texts is clean. Painkiller words appear only in the phrase lists (e.g. "painkillers aren't working"). |

## Decision-log update
Answer Q3 changes the wording of decision-log row Q4a, so revision row **Q4a-r2** was added and the log bumped to **v1.1**. Alex Sample (office manager, SME) approved v1.1 by email on 2026-11-26.

## Results after applying the feedback (rules v0.2, 71 cases)
- Schema validation passes; the rules the schema can't express have 0 violations; the advice-words check is clean.
- **Dry run:** 100% of Tier 1 and crisis cases caught, 70 of 71 (98.6%) exact, 0% over-triage. One known gap, E070, for the AI check. Full results in `evals/emergency/dry-run-results.csv`.
