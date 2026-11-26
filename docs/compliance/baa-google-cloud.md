# Google Cloud HIPAA BAA record

> **Status: NOT ACCEPTED.** No Business Associate Addendum with Google is in place. **No PHI may be sent to, stored in or processed by any Google Cloud project** until this record shows it as accepted and the other gates below are cleared. All work runs on synthetic data only.

| Field | Value |
|---|---|
| Vendor | Google Cloud |
| Agreement name (as shown in console) | Google Cloud Platform HIPAA Business Associate Addendum |
| Status | **NOT ACCEPTED** (decision 2026-11-26, DECISIONS #293: the BAA stays on paper for now) |
| Document version / date printed on the agreement | - (not yet seen) |
| Accepted on | - |
| Accepted by | - (must be a person with authority to bind the company; still to be named, P0-05 spec §14) |
| Authority confirmed by | - |
| Project to opt in from | `dai-rcpt-ops` |
| Scope | Still to confirm in the accepted text. The HIPAA page says: "The HIPAA BAA for Google Cloud includes the entire Google Cloud infrastructure, not only a subset of Google Cloud." The opt-in page says it's enough to opt in from one project in the account. |
| Saved copy | - (to go in `docs/compliance/agreements/google-cloud-baa-YYYY-MM-DD.pdf` once accepted; the repo is public, so decide first whether the PDF belongs in the repo or in a private drive) |
| Legal review of terms | Pending (compliance advisor), tracked in P0-11 |
| Covered-products snapshot | 2026-11-26, below |

## How to accept (when the company decides to)
Source: https://support.google.com/cloud/answer/6329727. The page also says the opt-in appears only if the company's Google Cloud agreement doesn't already include the BAA by reference.

1. The person with authority opens `console.cloud.google.com/iam-admin/privacy` and selects `dai-rcpt-ops`.
2. Find "Google Cloud Platform HIPAA Business Associate Addendum", choose **Review and Accept**, read it, then choose **I Accept**.
3. Save the agreement text as a PDF, and note its version or date and the IAM role that was needed.
4. Fill in every field in the table above and change the status to **ACCEPTED**. Add a DECISIONS row and update P0-10's vendor matrix.

## Gates before any real PHI (DECISIONS #25)
Real PHI may enter `dai-rcpt-prod` only (never dev, staging or ops), and only when **all** of these are done:
- [ ] This BAA is accepted and recorded (above).
- [ ] The P0-06 covered-products restriction and US-only locations are in place.
- [ ] The clinic ↔ company BAA is signed (P0-09).
- [ ] The vendor matrix shows every vendor that touches PHI (P0-10).
- [ ] The organization-level controls listed in [README.md](README.md#pending-before-real-phi) are done.

## Covered-products snapshot
- **Source:** https://docs.cloud.google.com/docs/security/compliance/hipaa, section "Google Cloud supported services". The section was last updated by Google on **2026-11-11**; the snapshot was taken on **2026-11-26**.
- **Footnote text** is copied word for word from the page's best-practices table, which each footnote marker links to.

| Plan §3.2 service | Exact entry on the list | Listed? | Footnote / note (verbatim) |
|---|---|---|---|
| Gemini on Vertex AI | **"Generative AI on Agent Platform"** (the models) and **"Gemini Enterprise Agent Platform"** (the platform) | Yes, both, no footnote | No footnote. Vertex AI has been renamed: Google's Vertex AI docs now redirect to "Gemini Enterprise Agent Platform" ("Name changes from Vertex AI"), and the generative-AI overview redirects to "Overview of models on Agent Platform". The page doesn't list "Vertex AI" under that name. P0-13 confirms that each model we pick is GA and covered. The page says: "Don't use pre-GA offerings as defined in the Service Specific Terms with PHI, unless expressly noted otherwise." |
| Speech-to-Text | "Speech-to-Text" | Yes (footnote 29) | "If you have entered into a BAA with Google that covers any PHI obligations under HIPAA, don't opt in to data logging." P0-06 makes sure data logging is off. |
| Text-to-Speech | "Text-to-Speech" | Yes | - |
| Cloud Run | "Cloud Run" | Yes | - |
| Cloud SQL | "Cloud SQL" | Yes | - |
| Memorystore (Redis) | "Memorystore" | Yes | - (the page doesn't name "Memorystore for Redis" separately) |
| Cloud Tasks | "Cloud Tasks" | Yes | - |
| Cloud Scheduler | "Cloud Scheduler" | Yes | - |
| Secret Manager | "Secret Manager" | Yes (footnote 27) | "When storing secrets in Secret Manager, review and follow the Secret Manager best practices." |
| Cloud KMS | "Cloud Key Management Service" | Yes (footnote 7) | "Determine whether your organization has encryption requirements beyond what's required by the HIPAA Security Rule. Customer content is encrypted at rest on Google Cloud. If you have additional encryption requirements, use Cloud KMS." |
| Cloud Logging | "Cloud Logging" | Yes (footnote 8) | "Configure audit log export destinations. Export audit logs to Cloud Storage for long-term archival and to BigQuery for any analytical, monitoring, and forensic needs. Configure appropriate access controls for those destinations." |
| Cloud Monitoring | "Cloud Monitoring" | Yes (footnote 9) | "Don't store PHI in metadata such as metric labels, VM labels, GKE resource annotations, or dashboard titles or content. Anyone with the appropriate IAM permissions can view your monitoring console or use the Cloud Monitoring API to see this data." |
| Cloud Trace | "Cloud Trace" | Yes | - |
| Identity Platform (staff MFA) | "Identity Platform" | Yes (footnote 22) | "Only store the minimum data needed to provide authentication and authorization for your application or service. When creating a user in Identity Platform, the only required attribute is an email address or a phone number. If you must store PHI, use a general-purpose database solution in Google Cloud." |
| Cloud Storage (Terraform state, exports) | "Cloud Storage" | Yes (footnote 10) | "Enable Object Versioning to help preserve historical archives and recover objects after accidental deletion." |
| Artifact Registry (container images) | "Artifact Registry" | Yes (footnote 4) | "Artifact Registry encrypts data in repositories using Google default encryption or customer-managed encryption keys (CMEK). Metadata, such as artifact names, is encrypted with Google default encryption. This metadata can appear in logs and is visible to any user account with the Artifact Registry Reader role (roles/artifactregistry.reader) or Artifact Registry Viewer role (roles/artifactregistry.viewer). To help prevent unauthorized access to PHI, see Control access and protect artifacts." |

**Result:** every plan §3.2 service is listed, so nothing is marked "not covered".

**General statements on the page, verbatim:**
- "Disable unsupported Google Cloud services when working with PHI. If you can't disable a service, you must not use it for PHI." (P0-06)
- "Google Cloud and Google Workspace support HIPAA compliance within the scope of a Business Associate Agreement, but ultimately you are responsible for evaluating your own HIPAA compliance."
