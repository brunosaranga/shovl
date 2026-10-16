# shovl: progress and deployment notes

Last updated: 16 Oct 2026 (**live**: site https://shovl-3upi.onrender.com, API https://shovl-api.onrender.com, database on Neon; security checks on the live site passed 16 Oct; pre-post fixes deployed 16 Oct, Mozilla Observatory **A+ (110/100, 12/12 tests)**; see "Before posting publicly")

## Deadline

The original target was **Sunday 11 October 2026**; set a new date. Rough order of work:

1. Engine safety pass (backend): **done**
2. Backend hardening: settings, check heuristics, password rules: **done** (see "Changes since 4 Oct")
3. Frontend: beta flow, guest session, dashboard on real data, the new scan outcomes: **done** (13 Oct, rebuilt in the Fenix-style structure)
4. Deployment setup: hosting, Postgres, HTTPS, environment variables, daily cleanup job. **Postgres: done (15 Oct), live on Neon.** **API live on Render (15 Oct): https://shovl-api.onrender.com. Frontend live on Render (15 Oct): https://shovl-3upi.onrender.com.** **Done (16 Oct):** proxy count set, live security checks passed. Left: first run of the guest cleanup workflow
5. A full test with a real browser against the deployed backend, then go live

If the date is at risk, the safe things to cut are PDF reports and the optional backend decisions below. Do not cut the safety pass or the deployment checklist.

## Goal of this stretch

Beta flow: Landing > DomainVerification > ScanRunning > Report, with first-time visitors getting a guest session so they can see their scans on the dashboard.

## Decisions made

- Guests are a real account created on the first "dig deeper", each one independent.
- Registering upgrades the same account, so scans stay attached.
- Signing in from a guest session moves the guest's scans onto the real account.
- Guests are strict: practice targets only. Real domains need a registered account.
- Allowance: guests 3 scans in total, registered users 5 per rolling 24 hours. Checked when a scan starts.
- Failed and interrupted scans do not count. Hard ceiling on attempts: 6 total (guests), 10 per day (registered).
- Staff accounts are exempt from the allowance.
- Guest creation limited to 30 per hour per network address.
- **Check severities (8 Oct):** "open, intent unknown" (endpoint answers without a token, or objects readable by ID without login) is MEDIUM. "Can't verify ownership" (BOLA with a token) is LOW. HIGH is kept for strong signals only.
- **Practice targets show honest results** (8 Oct): no special-casing, no faked results.
- **Practice targets** (14 Oct): postman-echo.com, httpbingo.org, jsonplaceholder.typicode.com and dummyjson.com. All free, no API key, and their writes are echoed or simulated, never stored. Left out on purpose: reqres.in (needs an API key), api.escuelajs.co (writes are stored for everyone), httpbin.org (no uptime guarantee), fakestoreapi.com (failed an automated check). Use a path, not the bare domain: postman-echo.com's root redirects off-site, which the scanner refuses.
- **Dark mode** (14 Oct): follows the system setting until the visitor picks one with the navbar toggle, then remembers it (`shovl.theme` in localStorage).
- **Database** (14 Oct): managed Postgres on **Neon, Free plan, region AWS Europe Central 1 (Frankfurt)**, using the direct connection string (not the `-pooler` one). The region cannot be changed later, so the app host should run in Frankfurt too. Production starts with an empty database: nothing is copied from the local SQLite file. Local development stays on SQLite unless DATABASE_URL is set.
- **Hosting** (15 Oct): **free options only for now.** **Render, region Frankfurt.** API = web service `shovl-api` on the **Free** instance (512 MB, 0.1 CPU, 750 free hours a month; it sleeps after 15 minutes without traffic and the next visitor waits about a minute while it wakes), with `WEB_CONCURRENCY=1`. Daily guest cleanup = **GitHub Actions** workflow `.github/workflows/purge-guests.yml` (Render cron jobs are never free; GitHub Free gives private repositories 2,000 Actions minutes a month, and without a card on file jobs just stop at the limit; the cleanup uses about a minute a day). Frontend = Render static site (free, next step). Workspace on the free Hobby plan: 5 GB of outbound bandwidth a month shared by all services. When money allows: Starter instance ($7/month) removes the sleep.
- **Mass assignment writes data, so it runs on practice targets only** (8 Oct). On a user's own domain it is skipped as `not_run`. An explicit opt-in comes after the beta.
- **Sessions** (8 Oct): access tokens last 16 hours (was 60 minutes). Change with `JWT_ACCESS_TOKEN_MINUTES`. The frontend still does not store the refresh token, so users sign in again after that. Guest tokens stay at 30 days.
- **Revocable sessions** (8 Oct): every token carries the account's `token_version` in a `tv` claim, and a token whose version no longer matches is refused with a 401 (code `token_revoked`). Upgrading a guest raises the version, so the old 30-day guest token stops working the moment the account is registered. Tokens issued before this change have no claim and count as version 0, so nobody is signed out by the rollout.
- **Passwords** (8 Oct): minimum 10 characters, maximum 128, plus Django's common / all-numeric / too-similar-to-email checks. Applied when a password is chosen (register, upgrade), never at sign-in.
- **Email verification** (16 Oct): not for the beta. Password help and account deletion go through the support address in the FAQ instead (see "Frontend: 16 Oct update").
- **Emails are lowercased** (16 Oct): one address is one account however it is typed. Stored lowercased, found in any case at sign-in, and backed by a case-insensitive unique rule in the database (see "Lowercase emails").
- **Content-Security-Policy** (16 Oct): enforced on the static site. Scripts only from the site itself, no inline scripts; inline styles allowed on purpose (blocking runtime styles could break the layout). Any new outside source (analytics, a CDN, another API) must be added to the policy or the browser blocks it (see "Static site headers").

## Changes since 4 Oct

- `core/settings.py`: secret key, `DEBUG`, `ALLOWED_HOSTS` and CORS now come from environment variables. The app refuses to start in production if one is missing. It also refuses to start if `SHOVL_ALLOW_PRIVATE_TARGETS=1` is set while `DEBUG` is off. Development needs `DJANGO_DEBUG=1`. `.env.example` lists the variables.
- `frontend/src/api/targets.js`: `localhost` and `127.0.0.1` are practice targets in development builds only (`import.meta.env.DEV`).
- `scanner/evidence.py` (new): shared helpers that judge a response by status, body type and content, not status alone.
- `scanner/checks/auth.py`: HIGH only when an invalid token gets through, or when your own token and no token return the same content. MEDIUM for "open to anyone". LOW for a web page returned instead of API data, and LOW ("could not be assessed") when the endpoint answers 404 or another non-answer without a token, instead of PASS.
- `scanner/checks/bola.py`: probes an ID that cannot exist as a baseline. A catch-all, echo or web-page server passes. MEDIUM without a token, LOW with a token (ownership cannot be verified with one account). Never HIGH.
- `scanner/checks/mass_assignment.py`: matches key and value in parsed JSON on 2xx responses only. A made-up control field detects servers that return whatever they are sent (LOW). A rejection that names a field (4xx) is no longer HIGH.
- `scanner/engine.py` and `scans/views.py`: `WRITE_CHECKS` and `allow_writes`. Mass assignment runs on practice targets only. On a real domain it comes back as an ERROR finding with reason `not_run`, so the report reads "based on 5 of 6 checks".
- `accounts/serializers.py`: password validators applied on register and upgrade (400 with `{"password": [...]}`).
- `scanner/checks/rate_limit.py`: no longer HIGH when no 429 is seen in 15 quick requests. It is MEDIUM with honest wording (the limit may be higher than the test reaches), and PASS when the server advertises a limit in its headers (RateLimit-*, X-RateLimit-*, X-Rate-Limit-*). The burst stops at the first 429.
- `scanner/tests.py`: the test certificates now carry the standard CA extensions, because Python 3.13 checks certificates strictly by default (one TLS test failed without this).
- `core/settings.py`: access token lifetime raised from 60 minutes to 16 hours, set by `JWT_ACCESS_TOKEN_MINUTES` (default 960).
- `accounts/models.py`, `tokens.py` (new), `authentication.py` (new), `serializers.py`, `views.py`, `core/settings.py`, `migrations/0003_user_token_version.py` (new): revocable tokens (see "Revocable sessions" above). `settings.py` now uses `accounts.authentication.VersionedJWTAuthentication` as the default authentication class.
- New tests: `scanner/test_checks.py` (66), `accounts/test_passwords.py` (15), `accounts/test_tokens.py` (4), `accounts/test_revocation.py` (20). Total with the existing safety tests: 160.

## Backend: done

Drop-in files and what they hold.

**accounts/**

- [x] models.py: is_guest flag, create_guest()
- [x] serializers.py: UpgradeSerializer, LoginSerializer (guest-scan transfer at sign-in), password strength on register and upgrade
- [x] transfer.py: moves a guest's scans to a real account, deletes the guest
- [x] permissions.py: IsRegisteredUser
- [x] throttles.py: GuestCreationThrottle (limit value at the top)
- [x] views.py: guest session, upgrade, /me/ with allowance
- [x] urls.py: /guest/ and /upgrade/ routes
- [x] management/commands/purge_guests.py (plus two empty `__init__.py` files): deletes guests 30 days after creation, with their scans and PDFs. `--dry-run` previews, `--days` changes the age
- [x] test_passwords.py: 15 tests
- [x] test_tokens.py: 4 tests (sign-in, upgrade and guest token lifetimes)
- [x] tokens.py, authentication.py, migrations/0003: revocable tokens. test_revocation.py: 20 tests

**domains/**

- [x] views.py: guests cannot add or verify domains
- [x] bug fixes: duplicate domain returns 400, practice-target list synced with the frontend (httpbin removed)
- [x] verification.py (14 Oct): practice targets are now the four public hosts above. Subdomains of a listed host count too; the parent of one does not (typicode.com is not a practice target). `scanner/tests.py` checks all of them plus lookalikes; still 160 tests
- [x] serializers.py (13 Oct): `serializers.VAlidationError` typo fixed. Adding a domain you had already added crashed with a 500 instead of the 400 above, so going back to /verify for the same domain always failed

**scans/**

- [x] limits.py: the numbers, counting, locked check-and-start
- [x] views.py: guest practice-only rule, allowance on both endpoints, scan saved at start, interrupted and failed handling, `allow_writes` for practice targets
- [x] models.py: interrupted status

**scanner/** (robustness pass)

- [x] http.py (new): shared request helper, time budget, plain-language errors. Don't run scripts from inside the scanner/ folder, its name shadows Python's http
- [x] config.py: scan budget, redirect cap, 1 MB response cap, per-response time cap, and the development-only allow_private_targets() flag
- [x] engine.py: reachability test, run_check (never raises), ensure_usable, build_raw, WRITE_CHECKS / allow_writes
- [x] Safety pass in http.py: every resolved address must be public, the connection goes to the address that was checked (no second lookup), HTTPS still verifies the real hostname, redirects followed one hop at a time and only within the same site, bodies read in chunks up to 1 MB under the time limits, environment proxies ignored
- [x] domains/verification.py: the file-ownership check goes through the same helper, and now requires the file to be exactly the token. localhost and 127.0.0.1 are practice targets only with the development flag
- [x] tests.py: 55 tests for the safety layer (certificate fixture updated for Python 3.13)
- [x] test_checks.py: 66 tests for the checks and the write-check skip. Run `python manage.py test scanner accounts scans` before every deploy (170 tests; one is skipped on SQLite)
- [x] report.py: meta gets checks_run, checks_failed, partial
- [x] checks/*.py (all six): use the helper and accept the budget. Misconfiguration keeps the worst severity, data exposure reads field names only
- [x] evidence.py (new): response-judging helpers shared by the checks
- [x] Check heuristics: auth, bola, mass_assignment and rate_limit rewritten (see "Changes since 4 Oct")
- [x] scans/views.py uses all of the above. A failed scan stores its reason in results.error

**Other fixes** (shovl-bugfixes.zip)

- [x] rate_limit typo, verbose passed to checks, token no longer read from the URL

Migrations to run: `accounts/migrations/0003_user_token_version.py`, `accounts/migrations/0004_lowercase_emails.py`, `accounts/migrations/0005_user_email_ci_unique.py` and `scans/migrations/0003_target_url_length_storable_results.py` ship with the code (do not regenerate them), then `migrate`.

**Postgres** (14 Oct, shovl-postgres-14oct.zip)

- [x] `core/settings.py`: the database comes from `DATABASE_URL` (dj-database-url). Production refuses to start without it, and refuses anything but Postgres. `sslmode=require` is added for any non-local host unless the URL sets it. Connections are reused for 60 seconds (`DB_CONN_MAX_AGE`) with a health check, so a connection Neon closed after scaling to zero is replaced. `DB_DISABLE_SERVER_SIDE_CURSORS=1` only for a pooler address
- [x] `requirements.txt` (new, next to manage.py): exact versions, Django 6.0.9 (same series as before, with the security patches), psycopg 3, dj-database-url. No WeasyPrint
- [x] `.env.example`: every variable the backend reads (the file in the repo was empty)
- [x] Found by running on Postgres: a target URL over 200 characters crashed with a 500 (SQLite had stored it). `Scan.target_url` is now 2048 long (migration 0003), and `scans/validators.py` refuses longer URLs, control characters, broken Unicode and non-http(s) schemes with a 400 on both scan endpoints, before anything is written
- [x] Found by running on Postgres: scan results containing the NUL character, broken Unicode or NaN (all can come from the scanned API's own responses) could not be saved, so a hostile target could make its own scan fail. `scans/encoders.py` cleans them on every save of `Scan.results`
- [x] `scans/test_database.py`: 10 tests, including a race test where 6 scans start at the same moment with one scan left. With the row lock exactly 1 starts; with the lock removed all 6 started (checked), which is why production must be Postgres. The race test is skipped on SQLite
- [x] Checked: 170 tests pass on Postgres 16 and on SQLite, migrations run from scratch on Postgres, the 42 browser checks pass with the backend on Postgres, no server errors

**Production on Render** (15 Oct, shovl-render-15oct.zip)

- [x] `build.sh` (Render build command `bash build.sh`): install, `check --deploy --fail-level WARNING`, `collectstatic`, `migrate`, `createcachetable`
- [x] `gunicorn.conf.py` (Render start command `gunicorn core.wsgi:application`): port from $PORT, gthread 2 x 8, timeout 120, graceful 100, workers recycled every ~1000 requests
- [x] `core/health.py`: `/healthz` answers "ok" before the host-name and HTTPS checks and without the database (Render health check path)
- [x] `core/settings.py`: Render's own hostname added to ALLOWED_HOSTS automatically; JSON-only API in production (no browsable API); WhiteNoise; HTTPS behind the proxy (`SECURE_PROXY_SSL_HEADER`, redirect, secure cookies, HSTS 30 days; the HSTS subdomain and preload warnings are silenced on purpose); errors logged to the host's log stream; shared database cache; GUEST_THROTTLE_PROXIES, SHOVL_LOG_CLIENT_IP and SHOVL_PDF_REPORTS from the environment
- [x] `accounts/throttles.py`: proxy count from the environment, optional log line for measuring it
- [x] `scans/views.py`: keep-alive comments while a check works, no-buffering headers, PDFs only when switched on. `scans/test_stream.py`: 5 tests
- [x] `backend/shovl/.gitignore` (new): keeps the `staticfiles/` folder out of git
- [x] Checked: 175 tests pass on SQLite, Postgres, and Postgres with production settings; production gunicorn run checked request by request (health on an internal address over plain HTTP, redirect to HTTPS, unknown host refused, JSON-only, security headers, admin CSS, CORS for the frontend only, guest limit across processes); 42 browser checks pass under gunicorn; a slow scan streams event by event with at most 15 s of silence; three scans at once run side by side

**Lowercase emails** (16 Oct, shovl-prepost-16oct.zip; deployed 16 Oct)

- [x] `accounts/models.py`: `UserManager.normalize_email` trims and lowercases the whole address (Django's own only lowercases the domain). `get_by_natural_key` lowercases too, so sign-in works in any case, in the API and the admin. `User.save()` and `User.clean()` lowercase, so every write path is covered. `Meta.constraints`: `UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique")`. `create_user` checks for a blank address after trimming
- [x] `accounts/serializers.py`: register declares its own `email` field with a case-insensitive check (DRF's automatic check was exact-match only) and returns `EMAIL_TAKEN_MESSAGE`; a race on the same address now gives a 400 instead of a 500. Upgrade's check comment corrected (it was always case-insensitive)
- [x] `accounts/migrations/0004_lowercase_emails.py`: lowercases existing addresses. If two accounts differ only in case it stops and names them (ids and addresses) instead of choosing one; on Render that fails the build and the running version stays up. `0005_user_email_ci_unique.py`: adds the constraint
- [x] `accounts/test_email_case.py`: 11 tests (register, upgrade, manager, admin-style save, database rule, full_clean, guests, sign-in in any case, wrong password)
- [x] Checked: `makemigrations --check` shows no drift; old mixed-case data lowercased and a clash stopped with the named accounts, on SQLite and Postgres 16; 11 tests pass on both; 186 tests pass locally (one skipped on SQLite)

## Backend: still to do

Small decisions, none of them blocking the beta:

- [ ] A guest's scans from today count toward the real account's daily total after sign-in transfer. Decide whether that is the behaviour you want
- [ ] After the beta: refresh-token flow in the frontend, so sessions renew without a sign-in
- [ ] After the beta: opt-in for the mass assignment POST on real domains (checkbox, parameter on both scan endpoints, a proper SKIPPED status)
- [ ] After the beta: email verification by 6-digit code, then password reset on the same code table. Needs an email API over HTTPS (Render's free plan blocks SMTP ports 25, 465 and 587; Brevo via django-anymail suggested, 300 free emails a day) and a sending domain with SPF/DKIM records. Lowercase emails: done 16 Oct

## Frontend: done (13 Oct)

Rebuilt with the Fenix Primavera structure: `routes.jsx` as the single source of truth, all copy in
`content/en/`, design tokens in `styles/tokens.css`, one folder per component with a colocated
`.module.css`, plain-JS `lib/`, and ui → sections → pages. Same look; the frontend README explains
the layout and `MIGRATION.md` maps every old file to its new place.

- [x] Landing: consent tick next to "dig deeper" creates the guest session (only shown when nobody is signed in)
- [x] Stored session reused on every visit (`lib/session.js`, key `shovl.session`; the old `access_token` key is adopted once)
- [x] Routes open for the beta flow, with access levels in `routes.jsx` (public / guest-or-registered / registered)
- [x] Practice target → scanning; own domain → /verify (registered) or the register tab (guest or nobody)
- [x] Stream refusals read from the JSON body and acted on by code (register, verify, wait until retry_after)
- [x] Scans remaining from /me/ on the landing page, the dashboard and settings
- [x] Any 401 (expired or `token_revoked`): session cleared once; registered → sign-in with a notice, guest → start page
- [x] Dashboard on real scan data, client-side pagination
- [x] Report handles running (refreshes every 3s), failed (results.error) and interrupted scans
- [x] Stream handles the failed event and ERROR results ("could not run")
- [x] "based on N of M checks" + the checks that could not run (mass assignment on own domains)
- [x] Interrupted / failed scans say "this scan did not count"; "stop this scan?" when leaving mid-scan (in-app and tab close)
- [x] Register and upgrade show the server's `password` messages under the field; the 10-character rule is shown up front
- [x] Register as a guest uses /upgrade/ and replaces the stored token with the new one
- [x] Sign-in as a guest sends `guest_token` in the body (scans move to the account)
- [x] Guests are told their scans are kept 30 days, and that today's scans still count after registering
- [x] GitHub/Google buttons and "Forgot password?" removed
- [x] ground.png replaced by ground.webp (2880px, ~220 KB)
- [x] Settings shows only what exists: email, domains (verified / pending), plan and scans left
- [x] 42 browser checks passed against the real backend (guest, upgrade, revocation, sign-in transfer, refusals, failures, leave guard, expiry, mobile)

## Frontend: 14 Oct update (shovl-update-14oct.zip)

- [x] The shovel spins again on the scan page. Cause: CSS Modules rename keyframe names inside a module, so `Spinner.module.css` was asking for a renamed `spin-steps` that only existed globally. Keyframes now live in the module that uses them. Same fix for the empty-URL shake in `UrlInput`
- [x] Four practice targets, shown as one-click "try:" chips under "dig deeper" for visitors who aren't registered (`lib/targets.js`, `LaunchPanel`, `content/en/landing.js`)
- [x] Informational text uses ink-950 like body text (`--text-muted` in `tokens.css`)
- [x] Dark mode: `[data-theme="dark"]` on `<html>` remaps the semantic tokens; sun/moon toggle in the navbar (`ui/ThemeToggle`, `context/ThemeContext.jsx`); a small script sets the theme before the first paint, so there is no flash (moved to `public/theme-init.js` on 16 Oct)
- [x] New token rule: text on a coloured fill (severity badges, the matrix, verified marks) uses `--on-fill` / `--on-dark-fill`, which stay the same in both themes. Code-like panels (terminal, DNS values, copy fields, finding evidence) use the `--terminal` tokens
- [x] Checked: lint clean, build OK, 12 theme checks, the 42 browser checks again, 160 backend tests

## Frontend: 16 Oct update (shovl-faq-16oct.zip)

- [x] FAQ modal: 18 questions in three groups (about shovl, results, your account), each a collapsible row. Native `<dialog>`, so it sits above the navbar, closes on Escape, the close button or a backdrop click, and keeps keyboard focus inside. Questions start collapsed each time it opens (`layout/Faq/FaqModal`, `context/FaqContext.jsx`)
- [x] Desktop: a "?" button fixed in the bottom-right corner (`layout/Faq/FaqButton`). Mobile: no button; "faq" sits in the account menu instead. Visitors who aren't signed in get the account menu on mobile too ("faq", "sign in"); on desktop their avatar still goes straight to sign-in
- [x] Copy in `content/en/faq.js`; support address `brunoeasaranga@gmail.com` in `common.contactEmail` (password help and account deletion go there). The answers repeat several numbers: 3 guest scans, 5 per 24 hours, 16-hour sessions, 30-day guest data, the 15-request rate test. Update `faq.js` when any of them changes
- [x] `ui/Modal`: `z-index: overlay` (invalid, so browsers dropped it) replaced by `var(--z-overlay)`. The "stop this scan?" backdrop now covers the navbar and the ground instead of sitting under them
- [x] Checked: lint clean, build OK, 27 browser checks (desktop and mobile, light and dark, anonymous / guest / registered, Escape, backdrop, focus)

## Frontend: 16 Oct pre-post update (shovl-prepost-16oct.zip; deployed 16 Oct)

- [x] `index.html`: one description (the duplicate removed), `og:*` preview tags (`og:site_name`, `og:image:alt` added) and `twitter:card`; JetBrains Mono added to the Google Fonts link (weights 400, 700, 800), so `--font-mono` no longer falls back to Courier; the theme script moved out to `public/theme-init.js`, loaded as a plain blocking script in `<head>` (still runs before the first paint). This is what lets the CSP refuse every inline script
- [x] `public/theme-init.js` (new): the theme script, unchanged
- [x] `public/.well-known/security.txt` (new): Contact (support address), Expires 2027-10-01, Preferred-Languages en, pt, Canonical. Renew before it expires. A Vite build copies `.well-known/` into `dist`
- [x] `layout/Navbar/Navbar.module.css`: debug `background-color: red` removed from `.menu`
- [x] Sign-in illustration: `sections/auth/AuthIntro/AuthIntro.jsx` imports `assets/images/incident-report-asset.jpg` and renders an `<img>` (a path string in `content/en/auth.js` was never bundled and showed as text). `auth.js` keeps only `intro.graphicAlt`. The frame keeps its border and shadow; the image keeps its natural shape

## Frontend: still to do

- [x] ~~Fonts: JetBrains Mono is named in tokens.css but never loaded~~ Fixed 16 Oct: loaded in index.html
- [x] ~~Incident-report illustration on the sign-in page~~ Fixed 16 Oct: AuthIntro imports the image
- [ ] After the beta: refresh-token flow, so sessions renew without a sign-in
- [ ] After the beta: Settings editing, API keys, account deletion (need backend endpoints first)
- [x] ~~`layout/Navbar/Navbar.module.css`: `.menu` debug `background-color: red`~~ Removed 16 Oct

## API reference for the frontend

`POST /api/accounts/guest/` body `{tos_agreed: true}`: 201 `{access, refresh, is_guest}`. 400 without consent. 429 `too_many_sessions` with `retry_after` (seconds).

`POST /api/accounts/register/` body `{email, password, tos_agreed}`: 201. The email is stored lowercased. 400 with `{"password": [messages]}` if the password is refused (too short, too common, entirely numeric, too similar to the email, longer than 128 characters). 400 with `{"email": ["An account with this email already exists. Sign in instead."]}` if the address exists in any case.

`POST /api/accounts/upgrade/` guest token in the header, body `{email, password, tos_agreed}`: 200 with new tokens. **The guest token stops working as soon as this succeeds; use only the returned tokens from then on.** A refused upgrade (400) leaves the guest token working. 400 if the email exists in any case ("sign in instead"). 400 with `{"password": [messages]}` if the password is refused (same rules). 403 if not a guest.

`POST /api/accounts/login/` body `{email, password, guest_token?}`. The email can be typed in any case. The guest token goes in the body, not the header. Passwords are not re-checked at sign-in.

Any endpoint: a token that has been revoked (for example a guest token after the upgrade) gets 401 with `{"detail": "This session is no longer valid. Please sign in again.", "code": "token_revoked"}`. Treat it like any other 401: clear the stored token and send the user to sign-in.

`GET /api/accounts/me/`: `{id, email, is_guest, allowance}`. allowance is `{limit, used, remaining, period}` or null for staff. period is `total` or `day`.

Scan refusals (both scan endpoints), body `{detail, code}`:

- 403 `registration_required`: guest tried a real domain
- 403 `guest_limit_reached`: guest used their scans or attempts
- 429 `daily_limit_reached`: includes `retry_after` (ISO time)
- 429 `too_many_attempts`: includes `retry_after`
- 403 "Domain not verified.": registered user, unverified domain

On the stream endpoint a refusal body is JSON inside a text/event-stream response. Read it as text, then parse.

Scan statuses: pending, running, complete, failed, interrupted.

Stream events, in order: running (check reachability, progress 0), then running and result per check, then complete. result can carry severity ERROR with a plain-language detail. **On a real domain the mass assignment result is ERROR with reason `not_run`.** If the scan cannot produce a result: an error event (check scan) followed by failed `{scan_id, reason, message}`. Failed scans do not count against the allowance.

One-shot endpoint failures: 502 `{detail, code, reason}` where code is `target_unreachable` (reasons: dns, refused, connection, timeout, tls, redirects, redirect_offsite, private, bad_response, invalid_url) or `scan_failed`. Messages for every reason are plain language and safe to show as they are.

Report meta includes checks_run, checks_failed, partial. risk_score can be INCOMPLETE. A skipped check counts in checks_failed, so `partial` is true on every real-domain scan.

Severities you will now see more of: auth and BOLA return MEDIUM for "open to anyone" and LOW for "ownership cannot be verified". Rate limiting returns MEDIUM when no limit is seen. Any public API reads at least MEDIUM overall.

## Deployment checklist

### Must do before any public URL

- [x] The app refuses to start if SHOVL_ALLOW_PRIVATE_TARGETS=1 while DEBUG is off (settings.py)
- [x] Do NOT set SHOVL_ALLOW_PRIVATE_TARGETS or DJANGO_DEBUG on the host. Leave them unset. If the private-targets flag is on in production, anyone can point the scanner at your own server. Checked 16 Oct: both unset on `shovl-api`
- [x] localhost and 127.0.0.1 are dev-only practice targets, on both the backend (verification.py) and the frontend (targets.js)
- [x] Block private and internal IP ranges, check every redirect hop (SSRF): built into scanner/http.py
- [x] After deploying, confirm it works for real: start a scan of a private address from the live app. It must fail with "That address points to a private network". If it scans, the development flag is on. Passed 16 Oct: signed out, `http://localhost` asks to register; `localtest.me` (resolves to 127.0.0.1) is refused with the private-network message
- [ ] Run `DJANGO_DEBUG=1 python manage.py test scanner accounts scans` on your Mac before every push (186 tests, one skipped on SQLite). Activate the project's virtual environment first (`source shovl-venv/bin/activate`; `which python` should point inside it): the Mac's system Python has no `whitenoise`, and every request-based test then errors (seen 16 Oct, 47 errors). Two warnings are expected: WhiteNoise's "No directory at …/staticfiles/" (collectstatic only runs on Render) and urllib3's "Certificate did not match expected hostname: other.test" (a TLS safety test refusing a wrong certificate on purpose). The host itself runs `check --deploy` on every build and refuses to deploy if a production safety setting is off (DEBUG left on, for example)
- [x] Secret key, DEBUG, ALLOWED_HOSTS and CORS read from environment variables in settings.py
- [x] On the host: generate a NEW secret key (the old one was in the uploaded zips) and set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS (bare hostnames) and CORS_ALLOWED_ORIGINS (full origin, no trailing slash). Checked 16 Oct
- [ ] WristHugger: regenerate its keys and database if that zip went anywhere shared

### Guest throttle

- [x] GUEST_THROTTLE_PROXIES measured on Render (15 Oct): **3**. The log line showed `REMOTE_ADDR=127.0.0.1 X-Forwarded-For=<visitor>, 162.158.x.x (Cloudflare edge), 10.196.x.x (Render internal)`, so the visitor is 3rd from the right. Set it on `shovl-api`, then remove SHOVL_LOG_CLIENT_IP. If Render changes its network, measure again the same way (SHOVL_LOG_CLIENT_IP=1, create a guest, read the `guest creation:` line). Checked 16 Oct: set to 3, SHOVL_LOG_CLIENT_IP removed
- [x] Shared cache: a database table (`shovl_cache`, made by `createcachetable` in build.sh) whenever DATABASE_URL is set, so every gunicorn process counts the same (15 Oct). Tested: exactly 30 guests per address, a fake address written in front by the client is ignored

### Server setup

- [x] Postgres support in the code: DATABASE_URL in settings.py, production refuses SQLite (14 Oct)
- [x] Neon project `shovl` created (15 Oct): AWS Europe Central 1 (Frankfurt), Postgres 18.6, Free plan, branch `production`, database `neondb`, role `neondb_owner`. `migrate` applied everything up to scans.0003. `python manage.py test scans` passed against Neon (10 tests, lock test included). Staff account created with a new password and terms accepted. Code pushed to main
- [x] On the host: set DATABASE_URL to the Neon direct connection string (the API runs in production mode, which refuses to start without a Postgres DATABASE_URL; 16 Oct)
- [x] requirements.txt; WeasyPrint dropped (the PDF code uses ReportLab). gunicorn and WhiteNoise added (15 Oct)
- [x] Static files: WhiteNoise serves the admin's CSS and JS, `collectstatic` runs in build.sh; rest_framework added to INSTALLED_APPS (15 Oct)
- [x] gunicorn: `gunicorn.conf.py`, 2 processes x 8 threads (gthread), timeout 120 s, control socket off. The scan stream sends `Cache-Control: no-cache` and `X-Accel-Buffering: no`, plus a keep-alive comment every 15 s while a check works, so no proxy sees a silent connection (15 Oct)
- [x] PDF reports off in production by default (`SHOVL_PDF_REPORTS`); the frontend has no download button yet (15 Oct)
- [ ] Schedule `python manage.py purge_guests` daily: GitHub Actions workflow `.github/workflows/purge-guests.yml` (03:00 UTC, plus a Run workflow button). Needs the repository secret DATABASE_URL. Check the first run in the Actions tab
- [x] Frontend: Render static site `shovl` (free): root directory `frontend`, build `npm ci && npm run build`, publish `dist`, `VITE_API_BASE_URL` = the API address with `/api` (baked in at build time), `NODE_VERSION` = `22.22.0`. Live since 15 Oct
- [x] Frontend hosting must send `index.html` for every route: Render rewrite rule Source `/*`, Destination `/index.html`, Action Rewrite. Checked 16 Oct: `/dashboard` opens the app
- [x] CORS_ALLOWED_ORIGINS in the `shovl-backend` group = `https://shovl-3upi.onrender.com` (15 Oct). A trailing slash makes the build fail with corsheaders.E014 (seen once; the running version stayed up)
- [x] Frontend wakes the sleeping free API on every page load (`wakeApi()` in `lib/api.js`, a no-cors request to `/healthz`). Tested: 42 browser checks pass against the built bundle served as static files (15 Oct)
- [ ] Optional on the host: JWT_ACCESS_TOKEN_MINUTES (default 960, which is 16 hours)
- [x] Keep `.env`, shovl-venv/, `__pycache__/` and `db.sqlite3` out of git and out of the deploy. Repo checked 16 Oct

### Static site headers (16 Oct)

Set on the Render static site `shovl`, Headers page, path `/*`. Mozilla Observatory on 16 Oct: **A+, 110/100, 12/12 tests**.

- [x] `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, `Strict-Transport-Security` (Observatory reads at least six months)
- [x] `Content-Security-Policy`, enforced after a Report-Only pass:

```
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; media-src 'self' data:; connect-src 'self' https://shovl-api.onrender.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests
```

- Observatory notes `'unsafe-inline'` in `style-src` without taking points: deliberate, since blocking runtime styles could break the layout
- Observatory suggests HSTS preload: not possible on an `onrender.com` address (the domain belongs to Render). Revisit with a custom domain
- When adding an outside source (analytics, a CDN, another API, a new font host), add it to the matching directive first, ideally by switching the header to `Content-Security-Policy-Report-Only` for a click-through. To undo quickly, rename the header back or delete it; no code change needed
- If the API address changes (custom domain, new service), update `connect-src` along with `VITE_API_BASE_URL`

## Before posting publicly (16 Oct)

Passed on the live site, 16 Oct: the private-address test, the environment variables on `shovl-api`, production mode (JSON-only errors, no debug page), and the GitHub repo (no `.env`, database or old keys). Then the pre-post fixes (shovl-prepost-16oct.zip) were deployed and checked:

- [x] Link preview tags in `frontend/index.html` (description, `og:*`, `twitter:card`)
- [ ] `frontend/public/og-image.png` (1200×627, a screenshot of the landing page works), then check it at its own URL and with LinkedIn's Post Inspector. Without it the link shows as a card with no image
- [x] Lowercase emails at register, upgrade and sign-in (see "Lowercase emails"). Migrations 0004 and 0005 applied on Render; sign-in with the staff email in a different case works
- [x] Security headers and CSP on the static site; Mozilla Observatory A+ (see "Static site headers")
- [x] `frontend/public/.well-known/security.txt` served as plain text
- [ ] Run the guest cleanup workflow once by hand and confirm it passes (see "Server setup")
- [ ] Cold start: keep the "first visit takes a minute" line in the post, or pay for Render Starter for the launch weeks
- [x] Polish: navbar debug red removed, JetBrains Mono loaded, sign-in illustration showing
- [ ] Post assets: a 20–40 s screen recording of a practice-target scan, and one report screenshot

## Known gaps to revisit

- [ ] The DNS lookup itself uses the system resolver's timeout (usually a few seconds); a slow trickle can overshoot the response time limit by at most one read timeout
- [ ] The scanner connects to the first resolved address (IPv4 first). If that one is down while another is up, the scan reports unreachable
- [ ] Redirects to another subdomain (for example api. to app.) are refused on purpose. Loosen only if a real user needs it
- [ ] The scanner ignores HTTP_PROXY / HTTPS_PROXY on purpose. If your host forces outbound traffic through a proxy, scans will fail and this needs a deliberate fix
- [x] ~~Password strength is never checked~~ Fixed 8 Oct: applied on register and upgrade
- [ ] A password reset flow does not exist yet. When it does, apply the same password checks there
- [ ] Access tokens last 16 hours and the frontend does not store the refresh token, so registered users are signed in again about once a day. The frontend sends them to sign-in on a 401. Access tokens cannot be revoked, so a longer life means a leaked token stays usable longer
- [x] ~~After an upgrade the old guest token keeps working for about 30 days~~ Fixed 8 Oct: upgrading raises the account's token version and the old token is refused
- [ ] "Sign out everywhere" is possible now (raise `token_version`) but has no button or endpoint. Also worth calling when a password-reset or change-password flow exists
- [ ] A guest's scans from today count toward the real account's daily total after sign-in transfer
- [ ] A scan that keeps running after the tab closes would need a background job system
- [ ] Practice-target lists live in two places (domains/verification.py and frontend/src/lib/targets.js). Keep them in sync
- [ ] Practice targets are third-party services. If one goes down or starts redirecting, scans of it fail with a plain-language reason; swap it out in both lists
- [ ] Postgres stores JSON keys in its own order (shortest first), so the evidence shown in a saved report can list keys in a different order than the live scan did. Nothing reads them by position
- [ ] Neon Free: 1 GB storage (shown on the project setup screen, 15 Oct), up to 2 CU, 10 branches per project; the database sleeps after 5 minutes without queries and wakes in a few hundred milliseconds. Watch usage in the Neon dashboard once real traffic comes in; the paid Launch plan is billed by usage
- [x] ~~Emails are case-sensitive at sign-up and sign-in~~ Fixed 16 Oct: lowercased on every save, found in any case at sign-in, case-insensitive unique rule in the database (see "Lowercase emails")
- [ ] An API that answers 200 with an error body for missing IDs (instead of 404) passes the BOLA check, because the nonexistent-ID probe sees a 200
- [ ] A schemaless store that returns any field it is sent reads as LOW ("could not be assessed") in the mass assignment check
- [ ] The rate limit burst is only 15 requests, so an API with a higher limit reads MEDIUM unless it advertises the limit in its headers

## Numbers you may want to change later

- `scans/limits.py`: guest 3, daily 5, attempt ceilings 6 and 10, stale-scan cutoff 10 minutes
- `scanner/config.py`: connect timeout 5s, read timeout 15s, rate-limit read timeout 6s, scan budget 90s, redirects 5, response cap 1 MB, per-response time cap 30s. Each can also be set through an environment variable (SHOVL_...)
- `accounts/throttles.py`: 30 guests per hour per address
- `accounts/views.py`: guest token lifetime 30 days
- `accounts/tokens.py`: the claim name (`tv`). Renaming it signs out every token issued with the old name
- `core/settings.py`: access token lifetime 16 hours (`JWT_ACCESS_TOKEN_MINUTES`, default 960); refresh token 7 days (`SIMPLE_JWT`, not used by the frontend yet)
- `core/settings.py`: minimum password length 10 (the `AUTH_PASSWORD_VALIDATORS` entry)
- `accounts/serializers.py`: maximum password length 128 (`PASSWORD_MAX_LENGTH`)
- `scanner/checks/bola.py`: probe IDs 1, 2, 3, 99, 100 and baseline ID 987654321
- `scanner/checks/rate_limit.py`: 15 requests, 0.1s apart, stops at the first 429 (`BURST_COUNT`, `BURST_INTERVAL`)
- `scans/validators.py`: longest accepted target URL 2048 characters (`MAX_URL_LENGTH`; the column in `scans/models.py` must match)
- `core/settings.py`: database connection reuse 60 seconds (`DB_CONN_MAX_AGE`)
- `frontend/src/content/en/faq.js`: repeats the guest, daily, session, guest-data and rate-test numbers above in plain words. Change it alongside them
- `frontend/public/.well-known/security.txt`: `Expires: 2027-10-01`. Renew before then (a date under a year ahead)
