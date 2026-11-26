# PR vendor and PHI check (P0-10)

P1-01 copies the checklist below into `.github/pull_request_template.md`. Until then, reviewers apply it by hand to every change.

```markdown
### Vendor and PHI check
- [ ] This PR adds **no** new external service, SaaS, SDK that sends data out, or Google Cloud API.
      If it does: `docs/compliance/vendors.yaml` (and `infra/org/allowed_services.yaml` for Google APIs) is updated in this PR, and the compliance owner is a reviewer.
- [ ] This PR sends **no new kind of PHI** to an existing vendor and adds no new PHI hop. If it does: the PHI flow table `docs/architecture/phi-flows.md` (P0-14), the vendor's row and the clinic BAA Annex A (P0-09) are updated, and `python3 scripts/compliance/check_phi_flows.py` passes.
- [ ] No PHI in code, tests, fixtures, logs, screenshots or the PR description (synthetic data only).
- [ ] No Pre-GA (preview/experimental) model or feature receives PHI.
```

After changing `vendors.yaml`, run:
```bash
python3 scripts/compliance/check_vendors.py --render   # rewrites vendor-matrix.md; commit both files
python3 scripts/compliance/check_vendors.py --gate     # GATE OPEN / GATE CLOSED with reasons
```

## Proposed CODEOWNERS (not active)
**No `.github/CODEOWNERS` file exists yet.** User decision 2026-11-26: it is added when the app moves to production editing (DECISIONS #308). These are the entries to use then:

```
/docs/compliance/                     <compliance owner>
/infra/org/allowed_services.yaml      <compliance owner>
/backend/app/integrations/            <compliance owner> <backend lead>
/scripts/compliance/                  <compliance owner>
/docs/architecture/phi-flows.md       <compliance owner>
/docs/architecture/network.md         <compliance owner> <tech lead>
```

Before turning it on:
- The repo belongs to a personal GitHub account, so `@<org>/compliance-owners` teams can't exist. Use GitHub usernames, or move the repo to an organization and create the team.
- CODEOWNERS only **requests** a review. To **block** merges without it, branch protection needs "Require review from Code Owners" (P1-01 / P1-06; Verify the setting name then).
