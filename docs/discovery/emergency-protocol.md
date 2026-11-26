# Emergency protocol: Example Dental Clinic

- **Version:** 0.2 · **Status:** clinic reviewed (OK for development and testing) · **Reviewed by:** Dr. Casey Example, dentist (protocol owner) on 2026-11-26
- **Review record:** [emergency-protocol-feedback-2026-11-26.md](emergency-protocol-feedback-2026-11-26.md)
- **Decision-log input:** [Q4a and Q4a-r2](clinic-decision-log.md) (protocol owner, urgent slot within 24 hours)

> *Sample values: replace them with the clinic's reviewed protocol.*

This document is for the dentist. It describes, in plain words, how the AI receptionist recognises emergencies and exactly what it says. It never diagnoses and never gives treatment or medication advice.

## How it works
1. **Rules first.** Every message the patient types or says is checked against the word lists below **before** anything else, even in the middle of booking.
2. **The most serious match wins:** Tier 1 / crisis, then "uncertain", then Tier 2, then Tier 3.
3. **"No" never hides a life-threatening sign.** "No, I can't breathe" is still treated as an emergency. If a patient *denies* a Tier 1 sign ("I'm not short of breath"), the AI treats it as **uncertain**: it gives the 911 safety line and marks the request URGENT.
4. **An AI check runs second.** It can only make the result *more* urgent, never less. Anything unclear becomes an URGENT callback.
5. **What staff see:** URGENT callback cases are flagged in the email subject and sorted first in the admin console. There is no live transfer.

## Tier 1: life-threatening (call 911)
| What it covers | Example words the patient might use |
|---|---|
| Difficulty breathing or swallowing | "cannot breathe", "cannot really breathe", "hard to breathe", "trouble breathing", "difficulty breathing" …; or words together in one sentence: (throat) + (closing / tight / swelling / swollen…) |
| Swelling spreading to the eye or neck | or words together in one sentence: (swelling / swollen / puffy / swelled…) + (eye / eyes / neck / throat…) |
| Bleeding that won't stop | "bleeding will not stop", "will not stop bleeding", "cannot stop the bleeding", "bleeding does not stop", "a lot of blood" …; or words together in one sentence: (blood / bleeding) + (will not stop / keeps coming / soaking / gushing…) |
| Major trauma to the face or head | "broken jaw", "jaw is broken", "car accident", "passed out", "knocked out cold" … |
| Non-dental medical emergency | "chest pain", "face is drooping", "face drooping", "slurred", "allergic reaction" …; or words together in one sentence: (face) + (numb / drooping / droops) |

**What the AI says, immediately, before asking anything:**
> "This sounds like it could be a medical emergency. Please call 911 now or go to the nearest emergency room. Don't wait for us to call you back. I'm also letting our team at {clinic_name} know right away."

**If the patient keeps talking:**
> "Please call 911 or go to the nearest emergency room now. Our team has been told and will follow up with you."

**What happens next:** booking stops, an **URGENT** callback case is created right away with whatever the AI already knows, and the AI may then collect a name and phone number for the case.

## Crisis: suicide or self-harm (988)
| What it covers | Example words the patient might use |
|---|---|
| Suicide or self-harm statements | "want to die", "kill myself", "killing myself", "end my life", "hurting myself" … |

**What the AI says:**
> "I'm really sorry you're going through this. You can call or text 988 right now to talk to someone at the Suicide & Crisis Lifeline. If you are in immediate danger, call 911."

**What happens next:** booking stops and an **URGENT** callback case is created. If a crisis statement and a Tier 1 sign come together, the AI says both messages, the crisis message first.

## Uncertain
Used when a life-threatening sign is mentioned with a "no" or "not" in front of it, or when the AI check isn't sure.

> "I want to make sure you get the right help. If you have trouble breathing or swallowing, swelling spreading to your eye or neck, or bleeding that won't stop, please call 911 now. I'm marking your request as urgent so our team can contact you as soon as possible."

**What happens next:** an **URGENT** callback case is created and the AI collects the patient's details.

## Tier 2: urgent dental (urgent slot within 24 hours)
| What it covers | Example words the patient might use |
|---|---|
| Severe pain (8-10 out of 10) | "worst pain", "unbearable", "excruciating", "couldn't sleep", "could not sleep" … |
| Facial swelling (not spreading to eye or neck) | "face is swollen", "face is swelling", "facial swelling", "cheek is swollen", "swollen cheek" …; or words together in one sentence: (swollen / swelling / puffy) + (face / cheek / jaw) |
| Knocked-out or dislodged permanent tooth | "knocked out", "knocked loose", "tooth came out", "tooth got knocked", "lost a tooth" |
| Signs of infection | "abscess", "pus", "infected tooth", "tooth infection", "infected gum"; or words together in one sentence: (fever / temperature) + (tooth / teeth / gum / jaw) |
| Bleeding or severe pain after a tooth removal | "dry socket"; or words together in one sentence: (pulled / extraction / extracted / removed…) + (worse / bleeding / throbbing / unbearable…) |

**What the AI says:**
> "I'm sorry you're dealing with this. Let me find the earliest urgent appointment for you with our dentist."

It then offers the earliest **Limited Exam (emergency exam, 30 minutes, Dr. Casey Example)** starting within **24 hours** (see the [appointment-type mapping](appointment-type-mapping.md)).

**If there is no urgent opening (or it's after hours):**
> "I'm sorry, we don't have an urgent opening right now. I've marked your request as urgent, and our team will contact you as soon as possible at {callback_phone}. If it gets worse, for example swelling spreading to your eye or neck, trouble breathing or swallowing, or bleeding that won't stop, call 911 or go to the nearest emergency room."

and an **URGENT** callback case is created (the team calls back the same business day, decision-log B6).

## Tier 3: routine symptoms (normal booking)
| What it covers | Example words the patient might use |
|---|---|
| Mild or occasional tooth pain → booking reason `toothache` | "mild toothache", "toothache", "hurts a little", "slight ache", "a bit sore" … |
| Sensitivity to hot, cold or sweet → booking reason `sensitivity` | "sensitive to cold", "sensitive to hot", "sensitive teeth", "sensitive tooth", "hurts with cold" … |
| Small chip, no pain → booking reason `broken_tooth` | "chipped", "small chip", "tiny chip", "chip on my tooth" |
| Lost filling or crown, no severe pain → booking reason `lost_filling_or_crown` | "filling fell out", "lost a filling", "lost my filling", "filling came out", "crown came off" … |

The AI continues normal booking with the matching visit reason. If the patient asks for advice, it says:
> "I'm not able to give medical advice, but I can book a visit so the dentist can take a look."

## What the AI never does
- No diagnosis, no medication, home-remedy or first-aid advice (no first-aid line for a knocked-out tooth: dentist decision, see the review record).
- No clinic phone number in the 911 / 988 messages, so the patient is never encouraged to call the clinic instead of 911 or 988.

## Privacy note for developers (P2-20)
What a patient says about their symptoms **is PHI** at runtime. Never log the patient's words or the matched phrases. Log only the category ID and tier (for example `t2_facial_swelling`, `tier2`), with no patient identifiers.

## Testing
- **Test set:** `evals/emergency/emergency_cases.yaml`, 71 made-up patient messages, all labels confirmed by the dentist.
- **Dry run of version 0.2:** `evals/emergency/dry-run-results.csv`.
  - **100%** of Tier 1 and crisis cases are caught.
  - **70 of 71 (98.6%)** match exactly.
  - **0%** over-triage.
- **Known gap, for the AI check (P2-20):** E070 "I feel dizzy and lightheaded since my tooth was pulled" (expected: uncertain). The rules return no match, because single words like "dizzy" are too broad for a rule. The dentist agreed this case must be caught by the AI check.
- **Status:** production needs a final `approved` sign-off (P5-07, through the rules editor in P4-11). Development and staging may use this `clinic reviewed` version.

## Pending notifications
These GitHub issues don't exist yet. When each one is created, comment on it with the paths below, `rules_version` 0.2, and the known gap.

Paths: `backend/app/domain/clinic_config/schemas/emergency_rules.schema.json`, `backend/app/domain/clinic_config/seed/example-dental-clinic/emergency_rules.yaml`, `backend/tests/fixtures/clinic_config/emergency_rules.example.yaml`, `evals/emergency/emergency_cases.yaml`.

| Task | What it relies on | Posted on issue (date) |
|---|---|---|
| P2-20 Emergency detector (absorbs P2-21 scripts and Tier 2 path) | Matching rules (spec §6), test set and pass criteria, scripts and tier actions, the E070 gap, "log category and tier only" | - |
| P4-11 Admin screens (absorbs P4-12 rules editor) | The schema and the status lifecycle draft → clinic_reviewed → approved | - |
| P5-01 Eval harness (absorbs P5-02 scenarios) | The emergency test set, to import into the 100+ scenarios | - |
| P5-07 UAT (absorbs P5-15 clinic sign-off) | This clinic-reviewed rule set and the review record, to approve as `approved` | - |
