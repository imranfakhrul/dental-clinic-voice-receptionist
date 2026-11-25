---
id: P4-09
title: Admin console shell with staff login and RBAC, plus clinic profile, hours, holidays, settings history and staff screens
milestone: P4
epic: E4.2
size: M
labels: area:admin, area:frontend, type:feature
depends_on: P1-13, P1-19, P1-01, P1-15
status: approved
---

# P4-09: Admin console shell with staff login and RBAC, plus clinic profile, hours, holidays, settings history and staff screens

> Consolidated task (#54). It absorbs P4-10 "Clinic profile, hours and holidays screens" (see `tasks/_CONSOLIDATION.md`).

## 1. Summary
Build the clinic admin console inside the existing Next.js app at `frontend/app/admin/`. It has three parts.

**The shell:**
- a styled login page with TOTP MFA (wrapping the P1-13 flow);
- a session layer with an idle warning and automatic logout;
- a layout with a role-filtered side menu;
- a permission-aware `<Can>` component;
- a shared "Save and publish" dialog (diff + change note) for every settings screen.

**The first screens:**
- **Home**: three count tiles;
- **Clinic profile**: name, phone, website; the time zone is read-only;
- **AI booking hours**;
- **Holidays**: manual entry, US federal holiday suggestions, and import suggestions from Open Dental if verified;
- **Settings history**: versions, diff, restore;
- **Staff**: invite, change role, deactivate; ADMIN only.

**One small backend endpoint:** `GET /v1/admin/dashboard/summary`, which returns counts only.

The task is done when:
- the read-only role can't change anything, both in the UI and through the API;
- every settings change creates an audited config version;
- the other P4 screens (consents, failed messages, callbacks, mapping) can be added as pages without touching the shell.

## 2. Why this matters
Plan §7 gives clinic staff a console to configure the AI and work callback cases. Without it:
- the clinic can't correct its hours or holidays, and a wrong holiday lets the AI book a day the clinic is closed (P1-19 §2);
- staff can't be invited or removed, and P0-11 risk R32 is "a departed staff member keeps access";
- P4-02, P4-11 and P4-13 have nowhere to put their screens.

The console shows PHI on some pages (callbacks, consents). The shell's job is to make access control impossible to forget:
- every page and button checks a permission;
- the session ends after 15 minutes idle;
- the backend enforces the same permissions anyway (P1-13 default deny).

## 3. Background you need
- **Project in one paragraph:** We are building an MVP of a web-based AI receptionist for US dental clinics. Patients talk (voice) or type (chat) on the clinic's website. The AI identifies or registers them in **Open Dental** (the clinic's practice-management system and our source of truth), books, reschedules or cancels real appointments, sends WhatsApp confirmations and reminders, and escalates emergencies. When it can't resolve something, it creates a callback case and emails the clinic admin (there is no live transfer). It runs on Google Cloud: Gemini on Vertex AI, Google Speech-to-Text and Text-to-Speech, a Python FastAPI backend on Cloud Run, Cloud SQL Postgres and Redis, with a Next.js frontend. Key rules: the LLM only talks and extracts, while deterministic code decides and acts; we store only Open Dental IDs (PatNum, AptNum), never copies of patient records; no PHI goes to any vendor without a signed BAA; and the system must be HIPAA-ready from day one. Work runs in phases: P0 discovery & compliance → P1 core platform + Open Dental adapter → P2 text chat → P3 voice and P4 WhatsApp + admin console (in parallel) → P5 hardening → P6 pilot. This task belongs to **P4, WhatsApp, Reminders & Admin Console**.
- **Frontend layout (P1-01):** one Next.js app in `frontend/` (TypeScript, Tailwind, pnpm) with the areas `app/widget` and `app/admin`, deployed as the Cloud Run service `web` at `app.<domain>`. The console lives at `https://app.<domain>/admin`.
- **Staff auth (P1-13), already built:**
  1. The browser signs in with the Identity Platform JS SDK (email + password + TOTP; first login enrolls TOTP with a QR code).
  2. It sends the ID token to `POST /v1/auth/session`.
  3. It receives the cookie `__Host-dai_staff` (`HttpOnly`, `Secure`, `SameSite=Strict`) and a `csrf_token`.
  4. It calls the SDK's `signOut()` straight after, so no IdP session lingers.

  Further rules:
  - every API call goes through `apiFetch` with `credentials: "include"` and the `X-CSRF-Token` header;
  - sessions end after 15 min idle (`idle_timeout_s: 900`) or 12 h;
  - `GET /v1/auth/me` returns the staff member and role;
  - `DELETE /v1/auth/session` logs out.

  P1-13 built a minimal login page; this task restyles and wraps it.
- **Roles and permissions (P1-13 `ROLE_PERMISSIONS`, with P4-01 and P4-02 additions):**

  | Permission | ADMIN | FRONT_DESK | DENTIST | READ_ONLY |
  |---|---|---|---|---|
  | `dashboard:read` | ✓ | ✓ | ✓ | ✓ |
  | `callback:read` | ✓ | ✓ | ✓ | ✓ |
  | `callback:read_contact` | ✓ | ✓ | ✓ | |
  | `callback:update` | ✓ | ✓ | ✓ | |
  | `activity:read` | ✓ | ✓ | | |
  | `config:read` | ✓ | ✓ | | |
  | `config:write` | ✓ | | | |
  | `staff:manage` | ✓ | | | |
  | `audit:read` | ✓ | | | |
  | `message:read`, `message:ack` | ✓ | ✓ | | |
  | `consent:read` | ✓ | ✓ | | ✓ |
  | `consent:write` | ✓ | ✓ | | |

  The backend is the authority. The UI only hides what the role can't use.
- **Clinic config (P1-19):** one versioned document per clinic, with sections `clinic`, `hours`, `holidays`, `scheduling`, `policies`, `callback`, `reminders`, `voice`, `clinic_info`, and so on.
  - `PATCH /v1/admin/config {base_version, changes, change_note}` creates a version (`201 {version}`). A stale `base_version` → 409.
  - `POST /v1/admin/config/activate {version, change_note}` makes it live.
  - `GET /v1/admin/config` returns `{version, config, od_check, warnings, locked_sections}`.
  - `GET /v1/admin/config/versions` and `GET /v1/admin/config/diff?from=&to=` give history and diffs.
  - Validation errors come back per field path. Some sections are **locked** (file-only, e.g. emergency rules).
  - Every version and activation is audited (`config.version_created`, `config.activated`).
- **Hours vs Open Dental schedules (P1-19):**
  - Open Dental's schedules say when each provider works;
  - our `hours` are an extra **AI booking window**: the AI never offers a time outside it;
  - our `holidays` close whole days, or set shorter hours, even if Open Dental has a schedule that day.
- **Open Dental schedules (P1-15):** `GET /schedules` with `SchedType` = Practice/Provider/Blockout/Employee/WebSchedASAP. **Verify:** whether a Practice schedule marks clinic holidays (e.g. a status or note value meaning "Holiday") and how to read it. If it can't be read reliably, there is no Open Dental import (§6.6).
- **Time zone:** `clinics.timezone` (IANA) is a column, not part of the versioned config. Every slot and reminder time depends on it.

New glossary terms: console shell, `<Can>`, Save and publish, settings history.

## 4. Scope
**In scope**
- `frontend/app/admin/` routes, layout, navigation, login and MFA screens (wrapping P1-13), session and idle handling, error pages (401, 403, 404, 409, offline).
- Shared UI: `<Can>`, `useStaff()`, `useConfig()`, the `SaveAndPublishDialog` with diff, the `FieldError` mapping from P1-19 errors, a table component, toasts.
- Screens: Home, Clinic profile, AI booking hours, Holidays, Settings history, Staff.
- `GET /v1/admin/dashboard/summary` (backend, counts only).
- `GET /v1/admin/opendental/holiday-suggestions` (backend, only if the Open Dental fact is verified).
- Static US federal holiday list (`frontend/app/admin/_lib/us-holidays.ts`, generated for the next two years).
- Playwright E2E for login, role menus, save-and-publish and restore.

**Out of scope** (and which task covers it)
- Login backend, sessions, MFA enforcement, staff API, permission matrix → P1-13 (done)
- Config storage, validation and versioning → P1-19 (done)
- Appointment type mapping, policies, clinic info, emergency rules screens → P4-11
- Messaging, voice and callback settings, callback cases, AI activity log → P4-13
- Consent screen → P4-02 (mounted in this shell)
- Failed-messages list UI → P4-13 (API in P4-01)
- Changing the time zone → support procedure, not the console (DECISIONS #262)
- SSO, password policy settings → later (P1-13 out of scope)

## 5. Dependencies and how to start without them
| Depends on | What you need from it | How to work before it is done |
|---|---|---|
| P1-13 Staff auth (approved spec) | Login flow, `/v1/auth/*`, `/v1/admin/staff*`, `apiFetch`, CSRF, roles | Use the dev Identity Platform tenant and the seeded dev Admin. For UI work, `NEXT_PUBLIC_ADMIN_MOCK=1` serves fixtures from MSW (Mock Service Worker) handlers in `frontend/app/admin/_mocks/`. |
| P1-19 Config (approved spec) | `/v1/admin/config*` endpoints, error format, locked sections | MSW handlers with the `seed/example-dental` config. |
| P1-01 Repo (approved spec) | Next.js app, Tailwind, CI | — |
| P1-15 Open Dental client (approved spec) | `GET /schedules` for holiday suggestions | Manual holidays and federal suggestions don't need it; the import button stays hidden until verified. |
| P2-22, P4-01 (approved specs) | Tables for the summary counts | Counts query `callback_requests` and `outbound_messages`; return 0 where a table is empty. |

## 6. Interface contract

### 6.1 Routes (`frontend/app/admin/`)
| Route | Page | Permission to view | Edit permission |
|---|---|---|---|
| `/admin/login` | Login + TOTP (+ enrollment on first login) | public | — |
| `/admin` | Home | `dashboard:read` | — |
| `/admin/settings/profile` | Clinic profile | `config:read` | `config:write` |
| `/admin/settings/hours` | AI booking hours | `config:read` | `config:write` |
| `/admin/settings/holidays` | Holidays | `config:read` | `config:write` |
| `/admin/settings/history` | Settings history | `config:read` | `config:write` (restore) |
| `/admin/staff` | Staff | `staff:manage` | `staff:manage` |
| `/admin/consents` | P4-02 page | `consent:read` | `consent:write` |
| `/admin/messages` | P4-13 page | `message:read` | `message:ack` |
| `/admin/callbacks` | P4-13 page | `callback:read` | `callback:update` |
| `/admin/settings/*` (more) | P4-11 / P4-13 pages | as declared there | as declared there |

Rules:
- A page a role can't view returns the 403 page (not a redirect loop) and doesn't appear in the menu.
- An unknown route returns 404.
- An unauthenticated user goes to `/admin/login?next=<path>`. `next` must be a relative `/admin/...` path (no open redirect).

### 6.2 Navigation registry (`frontend/app/admin/_lib/nav.ts`)
```ts
export type Permission =
  | "dashboard:read" | "callback:read" | "callback:read_contact" | "callback:update" | "activity:read"
  | "config:read" | "config:write" | "staff:manage" | "audit:read"
  | "message:read" | "message:ack" | "consent:read" | "consent:write";

export interface NavItem {
  href: string;              // "/admin/settings/hours"
  label: string;             // "AI booking hours"
  group: "Main" | "Patients" | "Clinic settings" | "Admin";
  view: Permission;          // hidden if the staff member lacks it
  ownerTask: string;         // "P4-09" — for traceability
}

export const NAV: NavItem[] = [
  { href: "/admin",                   label: "Home",             group: "Main",            view: "dashboard:read", ownerTask: "P4-09" },
  { href: "/admin/callbacks",         label: "Callbacks",        group: "Patients",        view: "callback:read",  ownerTask: "P4-13a" },
  { href: "/admin/messages",          label: "Failed messages",  group: "Patients",        view: "message:read",   ownerTask: "P4-13a" },
  { href: "/admin/consents",          label: "WhatsApp consent", group: "Patients",        view: "consent:read",   ownerTask: "P4-02" },
  { href: "/admin/settings/profile",  label: "Clinic profile",   group: "Clinic settings", view: "config:read",    ownerTask: "P4-09" },
  { href: "/admin/settings/hours",    label: "AI booking hours", group: "Clinic settings", view: "config:read",    ownerTask: "P4-09" },
  { href: "/admin/settings/holidays", label: "Holidays",         group: "Clinic settings", view: "config:read",    ownerTask: "P4-09" },
  { href: "/admin/settings/history",  label: "Settings history", group: "Clinic settings", view: "config:read",    ownerTask: "P4-09" },
  { href: "/admin/staff",             label: "Staff",            group: "Admin",           view: "staff:manage",   ownerTask: "P4-09" },
];
// Addition (DECISIONS #280–#282): P6-01 adds /admin/settings/pilot ("Pilot switches", config:read, ownerTask P6-01);
// P6-02 adds /admin/insights ("Insights", kpi:read, ownerTask P6-02); P6-04 adds /admin/review/sessions/[id] (no NAV item, transcript:read).
// P4-11 / P4-13 append their items here; a unit test checks every NAV href has a page and vice versa.
```
- The client copy of the permission matrix is generated from the backend: `GET /v1/auth/me` returns `permissions: Permission[]` (additive to P1-13). The UI never hard-codes role → permission.

### 6.3 Session and permission helpers
```ts
// frontend/app/admin/_lib/session.tsx
export interface Staff { id: string; display_name: string; role: "ADMIN"|"FRONT_DESK"|"DENTIST"|"READ_ONLY";
                         clinic_id: string; permissions: Permission[]; }
export function useStaff(): { staff: Staff | null; loading: boolean; logout(): Promise<void> };
export function Can(props: { perm: Permission; children: React.ReactNode; fallback?: React.ReactNode }): JSX.Element;
//   <Can perm="config:write"><Button>Save and publish</Button></Can>
//   Without the permission, forms render read-only (inputs disabled, no submit button, banner "View only").
```
**Idle handling:**
- The client tracks activity (keydown, pointer, visible page).
- At 13 minutes idle a modal shows "You'll be signed out in 2 minutes" with a **Stay signed in** button. The button calls `GET /v1/auth/me`, which refreshes the server idle timer (P1-13).
- At 15 minutes, the page calls `logout()` and routes to `/admin/login?reason=idle`.
- Any API 401 → clear in-memory state → login page.
- A 403 → toast "You don't have permission for that" (this shouldn't happen if `<Can>` is used).
- The `csrf_token` is kept in memory only (never `localStorage`). On reload, `GET /v1/auth/me` returns a fresh `csrf_token` (additive to P1-13).

### 6.4 Save and publish (`SaveAndPublishDialog`)
```ts
interface SaveAndPublishProps {
  section: keyof ClinicConfig;              // "hours"
  baseVersion: number;                      // version the form was loaded from
  changes: Partial<ClinicConfig>;           // merge-patch of the edited section only
  onDone(newVersion: number): void;
}
```
Flow:
1. **Preview:** the dialog shows a human-readable diff of `changes` against the loaded config, e.g. "Monday: 8:00 AM–12:00 PM, 1:00–5:00 PM → 9:00 AM–5:00 PM" or "Added holiday: Fri, Dec 25, 2026 (closed)".
2. The staff member types a **change note** (required, 5–200 chars, e.g. "New Monday hours from January").
3. **Publish** sends `PATCH /v1/admin/config {base_version, changes, change_note}` and then `POST /v1/admin/config/activate {version, change_note}`.
4. **Results:**
   - `409` (someone else saved first) → "Settings changed since you opened this page. Reload to see the latest." with a Reload button. Nothing is lost silently.
   - `422` validation → errors are mapped to fields by path (e.g. `hours.mon[1].end`) and the dialog closes.
   - Activation failure after a successful PATCH (rare; e.g. a prod-only rule) → the version exists but isn't active. The error is shown, and Settings history lists the version as "Not active".
   - Success → toast "Published. The AI uses the new settings now." `useConfig()` refetches.

There is no separate draft step in the UI (DECISIONS #262).

### 6.5 Screens
**Home** (`/admin`): three tiles from the summary endpoint. Each tile links to its page if the staff member can view it. There are no names, no reasons and no times.
```
GET /v1/admin/dashboard/summary          Permission dashboard:read
200 {"callbacks_open": 4, "callbacks_open_urgent": 1, "messages_failed_unack": 2,
     "ai_bookings_today": 7, "as_of": "2026-12-08T17:02:00Z"}
```
- `callbacks_open`: `callback_requests` with status `OPEN`. `callbacks_open_urgent`: the same with urgency `URGENT`.
- `messages_failed_unack`: `outbound_messages` with status `FAILED` and `acknowledged_at` null; it returns `null` when the staff member lacks `message:read`.
- `ai_bookings_today`: `appointment_refs` created today in clinic local time by a session.
- All counts are scoped to the staff member's clinic. Cache 30 s per clinic in Redis.

**Clinic profile** (`/admin/settings/profile`), the `clinic` section:

| Field | Input | Validation (client mirrors P1-19; the server is the authority) |
|---|---|---|
| `display_name` | text | 2–80 chars |
| `public_phone_e164` | US phone input → E.164 | Valid US number |
| `website_url` | URL | `https://` |
| Time zone | **read-only** text, e.g. "America/New_York (Eastern Time)" | Note: "Contact support to change the time zone." (DECISIONS #262) |

**AI booking hours** (`/admin/settings/hours`), the `hours` section:
- one row per weekday with 0–3 time ranges and a "Closed" toggle;
- 15-minute steps; times in clinic local time;
- the helper text explains that Open Dental schedules still decide which dentist is free, and these hours only limit when the AI may book;
- client checks: start < end, no overlaps, at most 3 ranges per day.

**Holidays** (`/admin/settings/holidays`), the `holidays` section:
- **Table:** date, name, Closed (all day) or Short hours (ranges). Add, edit, delete. Past dates are greyed; entries older than 60 days can be removed in bulk.
- **"Suggest US federal holidays":** opens a checklist for the next 12 months from `us-holidays.ts`, using the observed dates (e.g. when July 4 falls on a Saturday, the observed day is Friday). Nothing is pre-checked; the staff member picks, then Save and publish.
- **"Import from Open Dental":** shown only when the backend reports `od_holidays_supported: true` (§6.6). It lists the closed practice days Open Dental knows for the next 12 months as a checklist. Same picking flow; never automatic.
- **P1-19 warning:** "No holidays in the next 365 days" appears as a banner.

**Settings history** (`/admin/settings/history`):
- a list of versions from `GET /v1/admin/config/versions?limit=50`: version, date, who, source (`console` / `import` / `system`), change note, an Active badge, and "Not active" where it applies;
- **View changes** → `GET /v1/admin/config/diff?from=v-1&to=v`, rendered as a readable list;
- **Restore this version** (`config:write`) → the dialog explains "This makes version 12 live again. Your later changes stay in history." and requires a change note, then `POST /v1/admin/config/activate`;
- locked sections (P1-19 `locked_sections`) show a lock icon: "Changed by the project team".

**Staff** (`/admin/staff`, `staff:manage`):
- table from `GET /v1/admin/staff`: name, email, role, MFA enrolled, last login, Active;
- **Invite** → `POST /v1/admin/staff {email, display_name, role}`;
- **Change role** → `PATCH {role}` (the dialog warns "Their current sessions end now");
- **Deactivate** → `PATCH {active:false}` (confirm dialog; immediate effect per P1-13);
- **Resend invite** → `POST /v1/admin/staff/{id}/resend-invite`;
- a staff member can't change their own role or deactivate themselves (button hidden; P1-13 also rejects it with 409, **Verify** the P1-13 rule exists, else add it).

### 6.6 Open Dental holiday suggestions (backend, conditional)
```
GET /v1/admin/opendental/holiday-suggestions?months=12     Permission config:write
200 {"supported": true,  "items": [{"date": "2026-12-25", "name": "Christmas"}]}
200 {"supported": false, "items": []}       # when the clinic's Open Dental data can't express holidays
```
- **Verify** first: does `GET /schedules?SchedType=Practice&dateStart=&dateEnd=` return a field that marks a holiday or closed day? Record the field and example in `docs/integrations/open-dental-api-facts.md`.
- If not verifiable, ship with `supported: false` (the button stays hidden) and log the result in DECISIONS.
- The call uses `Priority.INTERACTIVE` and the P1-15 cache rules.
- `GET /v1/admin/config` gains `od_holidays_supported: bool` (additive to P1-19), so the page knows whether to show the button.

### 6.7 Additive backend changes
- **P1-13** `GET /v1/auth/me` returns `permissions: Permission[]` and a fresh `csrf_token`; it also refreshes the idle timer.
- **P1-19** `GET /v1/admin/config` returns `od_holidays_supported` and `timezone` (read-only, from `clinics.timezone`).
- **New** `GET /v1/admin/dashboard/summary` (`backend/app/api/admin/dashboard.py`).

## 7. Implementation guide
1. **Read** P1-13 (login flow, `apiFetch`, CSRF, roles, staff API), P1-19 (config API, errors, locked sections, rules), P1-01 (frontend layout, CI) and P4-02 §6.10 (the consents page that mounts here).
2. **Layout:** `frontend/app/admin/layout.tsx` (session provider, side menu from `NAV` filtered by `permissions`, header with clinic name, staff name and Sign out), plus `loading.tsx`, `error.tsx`, `not-found.tsx` and the 403 page.
3. **Login:** restyle the P1-13 page under `/admin/login`: email/password, TOTP step, first-login enrollment (QR + secret + verify), errors (wrong code, account disabled, rate limited) and the `?reason=idle` message.
4. **Session helpers:** `useStaff`, `<Can>`, the idle timer and modal, 401/403 handling in `apiFetch`.
5. **Config helpers:** `useConfig()` (SWR or React Query with `version`), `SaveAndPublishDialog`, diff renderer (`_lib/diff.ts`), error path → field mapping.
6. **Screens:** Home, Profile, Hours, Holidays (federal list generator, plus the OD import if verified), History, Staff.
7. **Backend:** the summary endpoint (permission, clinic scope, 30 s cache) and the two additive response fields.
8. **Mocks:** MSW handlers for every endpoint used, so `pnpm dev` works with `NEXT_PUBLIC_ADMIN_MOCK=1`.
9. **Path fix (already applied in the specs, DECISIONS #262):** P4-02 §6.10 now says `frontend/app/admin/consents/page.tsx`; P4-01 has no frontend path. Use `frontend/app/admin/...` everywhere.
10. **Accessibility:** keyboard navigation, labelled inputs, focus trapped in dialogs, WCAG AA contrast (Tailwind tokens).
11. **Tests** (§10).

## 8. Edge cases and error handling
| Situation | Expected behaviour |
|---|---|
| READ_ONLY opens Hours | Form disabled, "View only" banner, no Save button. A crafted PATCH → 403 from the backend. |
| FRONT_DESK opens Staff via URL | 403 page; not in the menu. |
| Two admins edit Hours at once | The second Publish gets 409 → reload prompt; no overwrite. |
| Validation error from the server (e.g. overlapping ranges) | Field-level message; nothing published. |
| PATCH succeeds, activate fails | Error shown; the version is listed "Not active" in history; the admin can retry Restore. |
| Session expires while typing | Idle modal at 13 min. At 15 min logout; unsaved form data is lost. **Proposed:** keep the unsaved form in memory only and warn "Unsaved changes" on navigation, never in `localStorage` (no PHI here, but keep the pattern). |
| Network offline | Banner "You're offline"; Save disabled. |
| Staff deactivated while signed in | Next API call → 401 → login page with "Your account is not active". |
| Admin tries to deactivate themselves | Button hidden; backend rejects. |
| Holiday on a date that's already in the list | Client blocks the duplicate; the server rule also rejects. |
| Federal holiday falls on a weekend | The suggestion shows the observed weekday, with a note. |
| Open Dental holidays not supported or unreachable | Import button hidden, or shows "Couldn't reach Open Dental. Try again later." No partial import. |
| `next` param points outside `/admin` | Ignored → `/admin`. |
| Clinic in another environment or another clinic's data | Impossible: every request is scoped by the staff session's clinic (P1-13). |

## 9. Security, HIPAA and PHI
- **PHI in this task's screens:** none on Home (counts only), Profile, Hours, Holidays or History (clinic data). The Staff page shows staff names and emails (workforce data, not PHI). PHI pages (callbacks, consents) are built by other tasks, inside this shell's access control.
- **Controls:**
  - MFA login (P1-13);
  - `HttpOnly` cookie session, CSRF token in memory only;
  - 15-minute idle logout with warning (HIPAA automatic logoff, §164.312(a)(2)(iii));
  - role-filtered menu and `<Can>`;
  - backend default deny (P1-13 T10).
- **Never store** session data, CSRF tokens or API responses in `localStorage`/`sessionStorage`. No analytics or third-party scripts in `/admin`. The CSP for `/admin` is the same as P2-25, minus the widget allowances.
- **Audit (backend):** `auth.login` / `.logout`, `config.version_created`, `config.activated` (including restores, `reason_code=restore`), `staff.create` / `.role_change` / `.deactivate`. Summary reads aren't audited (no PHI).
- **No open redirect** (`next` validation). The admin pages send `X-Frame-Options: DENY` / `frame-ancestors 'none'`.

## 10. Testing
**Unit** (Vitest + Testing Library, `frontend/app/admin/**/*.test.tsx`):

| # | Case | Expected |
|---|---|---|
| U1 | `NAV` filtering per role (4 roles) | Menu matches §6.1 |
| U2 | `<Can>` without the permission | Children hidden; fallback shown |
| U3 | Diff renderer for hours, holidays, profile | Readable lines as in §6.4 |
| U4 | Error path mapping `hours.mon[1].end` | The right input shows the message |
| U5 | Federal holiday generator for 2027 | Observed dates correct (e.g. July 4, 2027 is a Sunday → observed Mon, July 5) |
| U6 | Idle timer | Modal at 13 min, logout at 15 min, reset on activity |
| U7 | `next` validation | Only `/admin/...` accepted |
| U8 | Every `NAV` href has a page | Test passes |

**Backend** (pytest):
- **B1:** summary counts per clinic.
- **B2:** another clinic's data is never counted.
- **B3:** `messages_failed_unack` is `null` without `message:read`.
- **B4:** `GET /v1/auth/me` returns `permissions`.

**E2E** (Playwright against dev with seeded users, one per role):
- **E1:** login with TOTP (test TOTP secret from the dev password manager, generated with `otplib`).
- **E2:** READ_ONLY can't see Save on any settings page, and a direct API PATCH returns 403.
- **E3:** ADMIN changes Monday hours → Save and publish → the history shows the new version with the note → Restore the previous version → active again.
- **E4:** two browser contexts edit at once → the second gets the 409 prompt.
- **E5:** ADMIN invites a FRONT_DESK user; changing the role ends that user's session.
- **E6:** idle logout (clock mocked).

```bash
cd frontend && pnpm test && pnpm test:e2e -- admin
cd backend && pytest tests/unit/admin/test_dashboard.py -q
```

## 11. Acceptance criteria
- [ ] The read-only role can't edit anything: no edit controls in the UI, and the API returns 403 (E2)
- [ ] Every settings change creates a new config version with a change note, audited and visible in Settings history (E3)
- [ ] A previous version can be restored from Settings history (E3)
- [ ] Concurrent edits never overwrite each other silently (E4)
- [ ] The menu shows only pages the role may view, and a direct URL to a forbidden page shows 403 (U1, E2)
- [ ] Login requires TOTP; idle logout happens at 15 minutes with a warning at 13 (E1, E6)
- [ ] The time zone is shown read-only
- [ ] Holidays can be added manually and from federal suggestions; Open Dental import appears only if verified
- [ ] Home shows counts only, no patient data (B1–B3)
- [ ] P4-02 and P4-13 pages can be added by appending to `NAV` without changing the shell (U8)

## 12. Definition of done
- [ ] All acceptance criteria met
- [ ] Tests added and passing in CI
- [ ] PR reviewed
- [ ] No PHI in logs
- [ ] Docs / README updated (`docs/admin/console.md`: routes, permissions, how to add a page, save-and-publish flow)
- [ ] Open Dental holiday fact verified or recorded as unsupported
- [ ] Additive edits merged: P1-13 `/v1/auth/me` fields, P1-19 response fields

## 13. Hand-off
| Consumer | What it can rely on |
|---|---|
| P4-02 Consents page | Mounted at `/admin/consents` with `useStaff`, `<Can>`, `apiFetch` |
| P4-11 Mapping, policies, clinic info, emergency rules | `SaveAndPublishDialog`, `useConfig`, diff renderer, field error mapping, `NAV` entries |
| P4-13 Settings; P4-13a callbacks, activity, failed messages (split, DECISIONS #266) | Shell, `NAV`, `<Can>`, table component, Home tiles link to its pages |
| P4-17 E2E | Seeded role users and login helpers for Playwright |
| P5 security review | Route list, CSP, idle logout, default deny |

## 14. Open questions
| Question | Owner | Needed by |
|---|---|---|
| Does Open Dental's API expose clinic holidays (Practice schedule status or note)? | Developer (Verify) | Step 6 |
| Should the console have its own sub-domain (`admin.<domain>`) instead of `app.<domain>/admin`? Proposed: keep `/admin` (P1-01, P1-13 cookie set for `app.<domain>`) | Tech lead | Before P5 review |

## 15. References
- Plan §7 (clinic admin console), §6 (security), §2 (staff capabilities)
- HIPAA automatic logoff: 45 CFR §164.312(a)(2)(iii)
- U.S. OPM federal holidays: https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/
- DECISIONS #86, #152, #252–#262
- Related tasks: P1-01, P1-13, P1-15, P1-19, P2-22, P2-25, P4-01, P4-02, P4-11, P4-13, P4-17, P5-08
