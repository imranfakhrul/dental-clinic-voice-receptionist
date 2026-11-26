# Source record: patient messaging decision (P0-07a)

Every fact in [patient-messaging-decision.md](../patient-messaging-decision.md) is recorded here with its URL, the date it was checked, one quoted sentence and a SHA-256 fingerprint of the page as fetched. **Full copies aren't committed:** the repo is public and the pages are third-party copyrighted. A reviewer can re-fetch the URL and compare it. Copies taken on 2026-11-26 are kept outside the repo, in the company drive.

**How the pages were fetched:**
- **facebook.com and whatsappbusiness.com** refuse scripted downloads (HTTP 400), so those pages were read through a web-fetch tool. No byte fingerprint is available for them (**n/a**).
- **All other pages** were downloaded with `curl` and fingerprinted with `sha256sum`. A dynamic page's fingerprint can change between visits even when the text doesn't; it identifies the copy we read.
- **All checked on 2026-11-26.**

## Meta / WhatsApp
| ID | Source | Page date | Quote (at most one sentence) | SHA-256 |
|---|---|---|---|---|
| S1 | [Meta Terms for WhatsApp Business Platform](https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform), §4.2 "Prohibited Data" | Last Modified: September 23, 2026 | "…you acknowledge that Meta is not a Business Associate or Subcontractor…" and, in the same sentence, "…the WhatsApp Business Platform is not HIPAA compliant." (the omitted words refer to HIPAA's definitions) | n/a |
| S2 | Same page, §4.2 | same | "We make no representations or warranties that the WhatsApp Business Platform meets the needs of businesses regulated by laws and regulations with heightened confidentiality requirements for data, such as healthcare…" | n/a |
| S3 | [WhatsApp Business Messaging Policy](https://business.whatsapp.com/policy) (now redirects to whatsappbusiness.com/policy/), §3 "Protect Data and Comply with Law" | Last updated: September 23, 2026 | "Don't use WhatsApp for telemedicine or to send or request any health related information if applicable regulations prohibit distribution of such information to systems that do not meet heightened requirements to handle health related information." | n/a |
| S4 | [Meta Hosting Terms for Cloud API](https://www.facebook.com/legal/Meta-Hosting-Terms-Cloud-API) (page title "WhatsApp Business Platform Cloud API Terms"), §1.1 | Last Updated: September 23, 2026 | "Cloud API is provided by Meta and allows its users to send and receive messages over the WhatsApp network…" | n/a |
| S5 | Same page, §2.2 | same | Company Personal Data processed by Meta includes "…phone numbers, message content, personal identifiers, and message details (type, time, etc.)" | n/a |
| S6 | [WhatsApp template overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview) | - | The page's navigation lists "Booking appointment templates" under "Utility messages", so appointment messages appear to fall in the utility category. P0-15 confirms this when it submits templates. | `a0e274e482727217a7eb1ff302f798e68b62f78aca1377a58b82ca8e33e376ff` |

## SMS and WhatsApp providers
| ID | Source | Page date | Quote (at most one sentence) | SHA-256 |
|---|---|---|---|---|
| P1 | [Twilio HIPAA](https://www.twilio.com/en-us/hipaa) | - | "Customers wishing to sign a BAA with Twilio must have our Security Edition or Enterprise Edition." | `0df460231542869b2a8f43a1f7aebea5b06c622cdb216c63e5710360948e4aca` |
| P2 | [Twilio HIPAA Eligible Services (PDF)](https://twil.io/HIPAA-eligible-products-and-services) | Last Updated: June 30, 2026 | Lists "Programmable SMS" (Programmable SMS Basics, Programmable MMS, Long Codes, Toll-free, Short Codes, Advanced Opt-out); **WhatsApp isn't on the list.** | `c287de06267e45c0f8031d0d6c236a006b17445fc3583c84b0c8cf90138f1b38` |
| P3 | [Vonage HIPAA Compliance](https://www.vonage.com/communications-apis/healthcare/hipaa-compliance/) | - | "Messages API SMS and MMS messaging between providers and patients — available under the Vonage BAA for U.S. traffic." Also: "HIPAA support and BAA coverage apply to U.S. traffic only." The same page says dedicated numbers must be used only for HIPAA messaging. **WhatsApp isn't named under the BAA.** | `d25c7ed5421fc757a11894c16f7806e6b4ec96b099becbda8ca79506a69504c2` |
| P4 | [Sinch HIPAA](https://sinch.com/legal/policies-statements/other-sinch-policies-statements/hipaa/) | - | "Sinch has product level business associate agreements (BAA), which is an addendum to our standard Terms of Service." **It doesn't say which products.** | `07c60f241499d91a4ac33d7f9847f332baacce6748336e2e4aeb81c18d652744` |
| P5 | [Infobip HIPAA attestation (news, 2021-11-17)](https://www.infobip.com/news/infobip-successfully-completes-hipaa-attestation-reinforcing-commitment-to-data-privacy-and-security) | 2021-11-17 | "For customers that are subject to HIPAA, Infobip will sign a business associate agreement (BAA) for eligible services." The attestation "covered Infobip's SMS services". **No published list of eligible services; WhatsApp isn't named.** | `e5fccc0fccf2cf042e404344193c3e280e67c65dcdbdd29d83568fe60a970d32` |
| P6 | [Bird Acceptable Use Policy](https://bird.com/en-nl/legal/acceptable-use-policy-previous2024) | Previous (2024) version; Bird announced a June 2025 update that we couldn't retrieve | "HIPAA laws apply to 'covered entities'; Bird is not a covered entity, nor does it qualify as a 'business associate'." | `9274651ffaaeacca6ca88f0c589c7a22c439bf0e48da77c774052fb538d78ab7` |
| P7 | [360dialog Architecture and Security](https://docs.360dialog.com/docs/waba-basics/architecture-and-security) | - | **No mention of HIPAA or a BAA** (0 matches). A web search of 360dialog's site found no HIPAA/BAA statement. | `072dde37473be5c0cfb6a3541f261a291054960494a348bd27d66615a8e1a75e` |

## Not re-checked here (for the advisor and later tasks)
| Topic | Where it's settled |
|---|---|
| US A2P SMS registration (10DLC) and toll-free verification: rules and lead times | P0-07 / P0-15, with the chosen provider (Twilio lists Long Codes, Toll-free and Short Codes as eligible, P2) |
| TCPA consent rules for appointment texts | The advisor's answer to question 4; wording in P4-02 |
| HHS guidance on communicating at the patient's request over less secure channels | The advisor's answers to questions 1 and 3 ([HHS](https://www.hhs.gov/hipaa/for-professionals/index.html)) |
