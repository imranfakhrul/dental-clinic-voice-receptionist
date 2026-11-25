# AI Receptionist: pre-read for the discovery workshop

*Please read this before the workshop (about 10 minutes). Questions are welcome at any time.*

## What we are building
We are building an **AI receptionist on your clinic's website**. Patients can **talk to it by voice** or **type in a chat**, and switch between the two at any time.
It works directly with **Open Dental**: it books real appointments in your real schedule. It never keeps its own copy of patient records.

## What the AI receptionist does
- Answers common questions: services, opening hours, location, and the insurance plans you accept.
- Recognises returning patients once they confirm who they are (you decide what proof is required).
- Registers new patients by conversation, without creating duplicates.
- Listens to the patient's reason for the visit and picks the right appointment type, without giving a diagnosis.
- Offers 2–3 **real** free time slots and books one only after the patient confirms every detail.
- Reschedules and cancels appointments, following your cancellation policy.
- Sends a booking confirmation and a reminder about one hour before the appointment by text message, if the patient agrees. The channel is agreed in the workshop.
- Spots emergencies: tells the patient to call 911 for life-threatening symptoms, and offers an urgent slot or an urgent callback for urgent dental problems.

## What it does **not** do
- It does **not** diagnose or give treatment advice.
- It does **not** take phone calls, check insurance eligibility, collect intake forms or speak other languages. These are future options.
- It does **not** transfer the patient to a person live ("no live transfer").
- It does **not** invent availability or book anything without the patient's confirmation.

## What happens when the AI can't help: the callback flow
When the AI can't resolve something, or the patient asks for a person, it:
1. collects the patient's name, phone number and a short description;
2. reads them back to the patient to confirm;
3. creates a **callback case** and emails your clinic admin. Urgent cases are marked **URGENT**;
4. tells the patient when to expect a call back. You decide what we promise.

Your team then calls the patient back and marks the case as contacted or resolved in a simple admin console.

## Example (made up)
> **Patient:** Hi, I'd like a cleaning next week.
> **AI:** Happy to help. Are you an existing patient?
> **Patient:** Yes, Jane Test, born March 14, 1985.
> **AI:** Thanks, Jane. To confirm it's you, what's the mobile number on your file?
> … *(the AI offers three real slots, Jane picks Tuesday 10:00, and the AI reads back every detail)* …
> **AI:** You're booked for a cleaning on Tuesday at 10:00 with Dr. Example. You'll get a confirmation shortly.

## What we need from you in the workshop
About **90 minutes** with:
- your **office manager** (our main contact, who signs off decisions);
- your **Open Dental administrator**, ideally sitting at a clinic computer;
- the **dentist/owner**, for the emergency and clinical questions;
- the **person who can sign agreements** for the clinic (it may be one of the above).

We'll go through a short questionnaire (attached). For each question we suggest a default, so in most cases you only need to confirm or adjust it.

## One important rule: no real patient information yet
Until the data-protection agreement (BAA) between your clinic and our company is signed, **please don't show, tell or send us anything about real patients**. That includes names, birth dates, phone numbers, appointments and stories about real cases.
Please don't share your screen with live Open Dental patient data. We'll use made-up examples like "Jane Test" throughout.
