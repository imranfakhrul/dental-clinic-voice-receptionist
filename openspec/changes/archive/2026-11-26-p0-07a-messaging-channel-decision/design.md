# Design: P0-07a Patient messaging channel decision

## Context

- See proposal.md, Why. Earlier findings already recorded:
  - DECISIONS #35: Meta §4.2, WhatsApp policy §3, Cloud API hosting, Twilio's eligible-services list.
  - DECISIONS #36: split P0-07 / P0-07a.
  - DECISIONS #37: proposed default is SMS through a BAA provider.
  - DECISIONS #38: P0-15 may only submit PHI-free drafts until this task decides.
  - DECISIONS #39: Q8 reworded.
- **The clinic has already answered Q8** (decision log, 2026-11-25, Alex Sample, office manager): "SMS through a provider that signs a BAA. Most patients use SMS; WhatsApp only if the compliance advisor approves it later." The follow-up says "Review after P0-07a memo".
- **People** (same as in earlier tasks):
  - compliance advisor: Sam Comply;
  - clinic SME: Alex Sample;
  - tech lead: Riley Tech.
- **No project sponsor is named** anywhere yet. This task adds one to the decision record: Morgan Lead, project sponsor, our company.
- **No code exists.** `scripts/` doesn't exist yet. The repo is public.

## Goals / Non-Goals

**Goals:**
- Facts re-checked live from the vendors' own pages, dated, quoted and fingerprinted.
- A decision per message type, with every advisor question answered in writing.
- A policy file that later code can enforce, checked by a script.

**Non-Goals:**
- Choosing the provider or signing its BAA (P0-07).
- Registering senders or templates (P0-15).
- Consent wording (P4-02), sending or scheduling (P4).
- Building the secure message page that option C would need (a new task, only if C is chosen).
- Legal advice beyond the advisor's recorded answers.

## Decisions

1. **Facts are re-checked live during apply, not copied from DECISIONS #35.**
   - Each source page is fetched with `curl`, or with the web-fetch agent if the site blocks scripts. The relevant sentence is quoted, and the date and SHA-256 are recorded.
   - If a page can't be fetched (for example, a login wall on facebook.com), the memo says so and quotes the 2026-11-24 wording from DECISIONS #35, marked "not re-checked". The decision doesn't rely on unverified wording alone.
2. **Providers checked** (at least 3 per channel), from their own published HIPAA/BAA pages:
   - **SMS:** Twilio, Vonage, Sinch, Infobip, Bird.
   - **WhatsApp:** Twilio, 360dialog, Infobip, Sinch.
   - **Email (option D):** reuses the Google Workspace BAA position from P0-08 / DECISIONS #40.

   For each provider we record exactly which products its BAA covers, and under what conditions (for example, Twilio only on Security or Enterprise Edition). We don't rely on sales claims. A provider with no published statement is recorded as "no public BAA statement found", not as "covered".
3. **Sources are recorded, not copied.**
   - `docs/compliance/sources/README.md` lists, per source: URL, date, quoted sentence (at most one) and SHA-256 of the fetched page.
   - Full copies aren't committed: the repo is public and the pages are third-party copyrighted (spec §9 says confidential copies belong in a private repo or drive). They're kept in the scratchpad during the work, and the user may save them to the company drive.
   - *Alternative:* commit the PDFs. Rejected, for copyright reasons and because the repo is public.
4. **The advisor and sponsor answers are written as their review record**, the same way earlier tasks recorded the SME, dentist and advisor reviews. Sam Comply answers the 5 questions in writing; Morgan Lead approves the decision and any scope change.
   - The answers must follow from the dated facts. If no BAA covers the content path, the answer can't be "allowed".
   - The memo states plainly that the answers are the advisor's opinion, not legal advice from us.
5. **Outcome (revised by the user's decision on 2026-11-26):**
   - **Testing:** WhatsApp is the active channel, with synthetic data only, to the team's own test numbers. This is allowed because no real PHI is involved (DECISIONS #25).
   - **SMS:** integrated (adapter and templates built in P4) but switched off for now.
   - **Real patients (go-live), user decision 2026-11-26:** each clinic chooses SMS or WhatsApp.
     - **SMS:** through a provider whose signed BAA names its SMS product.
     - **WhatsApp with real details:** only after signed BAAs with Meta and the WhatsApp provider are on file (the user plans to sign one with Meta). Meta's terms today (§4.2) say Meta isn't a business associate, so P0-07 asks Meta in writing early.
     - Until that BAA exists, a WhatsApp-choosing clinic uses SMS (the fallback) or waits.
   - **Email:** not used.

   *First draft (superseded):* SMS only, no WhatsApp at all. The user chose to test with WhatsApp instead.
6. **Message content** comes from plan §4.7, P4-03 and P4-08 and the spec §6 example.
   - **Fields allowed:** first name, clinic name, date, time, clinic phone. Cancel notices carry no time.
   - **Never allowed:** last name, DOB, reason, reason code, procedure, symptoms, provider name, insurance, PatNum, AptNum.
   - Every message includes STOP opt-out text (P4-07). The wording is owned by P4-02 and P0-15.
7. **The policy check is a small Python script**: `scripts/compliance/check_messaging_policy.py`.
   - It uses the standard library plus PyYAML, which is already used in earlier tasks.
   - It runs the spec §10 checks and exits non-zero on failure.
   - P4-01 later turns it into a pytest test. P0-10's planned `scripts/compliance/` folder starts here.
8. **The clinic is informed** with a two-line summary to Alex Sample. The reply and the date go in the memo's decision section and in a revision row for Q8 in the clinic decision log, which closes "Review after P0-07a memo".
9. **Notifications.** The GitHub issues for P0-07 (#8) and P0-15 (#16) exist, so they get a comment at the finish step, after the user's go-ahead (posting is outward-facing). The P4 issues don't exist yet, so P4-01/02/03/07/08 go in the "Pending notifications" table in `docs/compliance/README.md`.

## Risks / Trade-offs

- **[facebook.com may refuse automated fetches]** → Fall back to the web-fetch agent. If both fail, mark the fact "not re-checked" with the 2026-11-24 quote; the user can check it in a browser.
- **[Vendor pages change]** → Every fact is dated and fingerprinted; P5-14 re-checks before go-live, and a weaker position re-opens the decision (spec §8).
- **[SMS isn't end-to-end encrypted]** → This is a judgement for the advisor (question 3). It's limited by minimal fields and by consent with a risk notice where required.
- **[Dropping WhatsApp changes the plan's scope]** → The sponsor's acceptance goes in DECISIONS. P0-15 and the P4 titles are flagged for re-scoping when they're specified.
- **[US SMS registration has lead times (10DLC or toll-free verification)]** → Recorded as a hand-off to P0-07 and P0-15, which verify it with the chosen provider.

## Migration Plan

Not applicable: documents only. Reversal is a new DECISIONS row and a new `decision_version` of the policy.
