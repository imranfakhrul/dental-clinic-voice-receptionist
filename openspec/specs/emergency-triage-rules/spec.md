# emergency-triage-rules Specification

## Purpose

Defines, per clinic, how patient messages are checked for emergencies before anything else. It covers the tiers, the deterministic phrase rules, the exact words the AI says, what happens next, and the labelled test set that proves no emergency is missed.

## Requirements

### Requirement: Rules files validate against the emergency-rules JSON Schema
Every clinic emergency-rules file and the shared test fixture SHALL validate against `emergency_rules.schema.json` (JSON Schema 2020-12). Unknown fields SHALL be rejected.

#### Scenario: Valid clinic rules
- **WHEN** the clinic rules file is validated against the schema
- **THEN** validation passes

#### Scenario: Category with no way to match
- **WHEN** a category has no phrases and fewer than two co-occurrence groups
- **THEN** validation fails

### Requirement: Draft categories cover every tier
The rules SHALL contain at least the Tier 1 categories (airway, spreading swelling, bleeding, trauma, non-dental medical), the crisis category, the Tier 2 categories (severe pain, facial swelling, knocked-out tooth, infection, post-extraction) and the Tier 3 categories (mild pain, sensitivity, minor chip, lost filling).

#### Scenario: Category list check
- **WHEN** the category IDs of the clinic rules are listed
- **THEN** every draft category is present, or its removal is recorded in the dentist feedback file

### Requirement: Category tiers and reason codes are consistent
Each category's tier SHALL match its ID prefix (`t1_` → 1, `t2_` → 2, `t3_` → 3, `crisis` → crisis). Tier 3 categories SHALL carry a reason code from the appointment-type mapping. Tier 1, Tier 2 and crisis categories SHALL carry none.

#### Scenario: Tier 3 maps to a booking reason
- **WHEN** the category `t3_sensitivity` matches
- **THEN** booking continues with reason code `sensitivity`

### Requirement: Messages are normalized before matching
Before matching, each patient turn SHALL be lowercased, with apostrophes straightened and whitespace collapsed. Contractions and their transcript forms SHALL map to one form (`can't`/`cant`/`can not` → `cannot`, `won't`/`wont` → `will not`, `don't`/`dont` → `do not`). Punctuation SHALL be removed except `.`, `?` and `!`, which split sentences.

#### Scenario: Voice transcript form
- **WHEN** the transcript is "i cant breathe"
- **THEN** it matches the same as "I can't breathe."

### Requirement: Phrases and co-occurrence groups match within one sentence
A phrase SHALL match when its words appear consecutively on word boundaries within one sentence. A co-occurrence category SHALL match when every group has at least one term in the same sentence, in any order.

#### Scenario: Spreading swelling by co-occurrence
- **WHEN** a sentence contains "swollen" and "eye"
- **THEN** `t1_spreading_swelling` matches

#### Scenario: Terms in different sentences
- **WHEN** "swollen" and "eye" appear in different sentences
- **THEN** the co-occurrence category does not match

### Requirement: Negation never silences Tier 1 or crisis
A negation word within the configured window before a match SHALL cancel a Tier 2 or Tier 3 match. For a Tier 1 or crisis match, it SHALL turn the result into `uncertain`, never into no match. Phrases that themselves contain a negation SHALL not be checked for negation.

#### Scenario: Negated Tier 1 phrase
- **WHEN** the patient says "no I am not short of breath"
- **THEN** the result is `uncertain`, not `none`

#### Scenario: Negated Tier 2 phrase
- **WHEN** the patient says "no swelling, just a bit sensitive"
- **THEN** the Tier 2 match is ignored and Tier 3 `sensitivity` matches

### Requirement: Highest-severity result wins
Precedence SHALL be tier 1 / crisis > uncertain > tier 2 > tier 3 > none. When both tier 1 and crisis match, both scripts SHALL be said, crisis first. A later model check MAY raise the result but SHALL never lower it.

#### Scenario: Tier 1 and Tier 2 together
- **WHEN** one message matches a Tier 1 and a Tier 2 category
- **THEN** the result is `tier1`

### Requirement: Tier 1 and crisis stop everything and escalate
`tier1` SHALL say the 911 script immediately, create an URGENT callback case without asking questions first, and stop all booking. `crisis` SHALL say the 988 script, create an URGENT case and stop booking.

#### Scenario: Emergency mid-booking
- **WHEN** a Tier 1 phrase appears while a booking is in progress
- **THEN** booking stops, the 911 script is said and an URGENT case is created

### Requirement: Uncertain results escalate with a safety line
`uncertain` SHALL say the uncertain script, which contains the 911 safety line, and create an URGENT callback.

#### Scenario: Negated airway phrase
- **WHEN** the result is `uncertain`
- **THEN** the patient hears when to call 911 and an URGENT callback is created

### Requirement: Tier 2 offers an urgent slot or an URGENT callback
`tier2` SHALL search `emergency_exam` slots starting within `urgent_slot_max_hours`. If there is none, it SHALL say the no-slot script and create an URGENT callback.

#### Scenario: No urgent slot
- **WHEN** a Tier 2 result has no `emergency_exam` slot within the window
- **THEN** the no-slot script is said and an URGENT callback is created

### Requirement: Tier 3 continues normal booking
`tier3` SHALL continue normal booking with the category's reason code, saying the routine script only if the patient asked for advice.

#### Scenario: Mild sensitivity
- **WHEN** the result is `tier3` from `t3_sensitivity`
- **THEN** booking continues with reason code `sensitivity`

### Requirement: Scripts are fixed, reviewed and contain no advice
The AI SHALL say only the scripts in the rules file, in English. The only placeholders SHALL be `{first_name}`, `{clinic_name}` and `{callback_phone}`. Scripts marked `contains_first_aid: false` SHALL contain no medication, home-remedy or treatment advice.

#### Scenario: Advice-words check
- **WHEN** the script texts are scanned for the spec's advice-word list
- **THEN** no script with `contains_first_aid: false` matches

#### Scenario: Unknown placeholder
- **WHEN** a script contains `{address}`
- **THEN** the file is rejected

### Requirement: Rules move through a review lifecycle
Rules SHALL have status `draft`, `clinic_reviewed` or `approved`. `clinic_reviewed` and `approved` SHALL require `reviewed_by` and `reviewed_on`. Production SHALL load only `approved`. Dev and staging MAY load `clinic_reviewed`. `draft` is for local tests only.

#### Scenario: End state of this task
- **WHEN** the dentist has reviewed the rules and the feedback is applied
- **THEN** the clinic rules have `status: clinic_reviewed` with reviewer and date

### Requirement: Labelled test set proves no under-triage
A labelled set of at least 60 synthetic utterances SHALL exist in the required mix: ≥20 tier1, ≥3 crisis, ≥15 tier2, ≥10 tier3, ≥10 none and ≥5 uncertain. Applying the rules SHALL return the expected result for 100% of tier1 and crisis cases, and SHALL never return `tier3` or `none` for a case expected as tier1, crisis, uncertain or tier2. At least 95% of all cases SHALL match exactly. Cases the rules can't meet SHALL be listed for the model check.

#### Scenario: Dry run
- **WHEN** the matching rules are applied to every test case
- **THEN** the pass criteria hold, or each failing case is listed for P2-20's model check

### Requirement: Symptoms are never logged in plain text
Phrases, test utterances and examples SHALL be synthetic. At runtime, only the category ID and tier MAY be logged, never the patient's words or matched phrases.

#### Scenario: Logging a match
- **WHEN** a message matches `t2_facial_swelling`
- **THEN** the log contains the category ID and tier only
