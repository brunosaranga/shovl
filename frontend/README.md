# shovl · frontend

React (Vite) frontend for shovl, the neo-brutalist API security scanner.
Talks to the Django API in `backend/` (JWT auth, guest sessions, SSE scan stream).

## Run

```bash
npm install
cp .env.example .env      # VITE_API_BASE_URL → your Django API, including /api
npm run dev               # http://localhost:5173
npm run lint              # must stay clean
npm run build             # production build in dist/
npm run preview           # serve the build locally
```

Run the backend with `DJANGO_DEBUG=1` in development. To scan `localhost` / `127.0.0.1`
locally, also set `SHOVL_ALLOW_PRIVATE_TARGETS=1` on the backend (dev only, never in production).

Hosting: this is a single-page app, so the server must send `index.html` for every route
(Netlify `_redirects`, Vercel rewrites, or Nginx `try_files $uri /index.html`).

## How it's organised

```
src/
├── main.jsx, App.jsx        # entry: global styles + SessionProvider + router
├── routes.jsx               # single source of truth: every page, who may open it, the account menu
├── styles/                  # tokens.css (design system), reset, base, utilities
├── content/en/              # ALL copy, no JSX ({placeholders} filled by lib/text.js)
├── context/                 # SessionContext (anonymous | guest | registered), ThemeContext, SoundContext,
│                            # NavSlotContext
├── hooks/                   # useScanStream, useScanLauncher, useScans, useDomainSetup,
│                            # useLeaveGuard, useMediaQuery, useContent, useSounds
├── lib/                     # api (axios + endpoints + stream), session (token storage),
│                            # sse, targets, severity, apiErrors, text, sound — no React in here
├── assets/                  # logos/, knobs/, images/, sounds/
├── components/
│   ├── layout/              # Layout (shell), Navbar (+ AccountMenu), NavCenter, Ground, Footer,
│   │                        # PageBody, PageMeta, AccessGate
│   ├── ui/                  # Button, Card, Badge, Alert, Modal, ProgressBar, Terminal, Knob,
│   │                        # Logo, Spinner, TextField, Checkbox, CopyField, PageTitle, Pagination,
│   │                        # ThemeToggle, SoundToggle
│   ├── forms/               # UrlInput, AuthForm
│   └── sections/            # grouped by page area: landing/, auth/, verify/, scan/,
│                            # report/, dashboard/, settings/
└── pages/                   # Landing, Auth, Verify, ScanRunning, Report, Dashboard,
                             # Settings, NotFound
```

Every component lives in its own folder with a colocated `Name.module.css`.

Rules of thumb:

- **Copy lives in `content/en/`.** Never hard-code text in a component.
- **Components only use semantic tokens** (`--surface`, `--text`, `--accent`, `--sev-high`…).
  Raw colours (`--ink-950`, `--neon-500`…) stay inside `tokens.css`. Dark mode is the inverse:
  `[data-theme="dark"]` at the bottom of `tokens.css` remaps layer 2, nothing else.
- **Text on a bright or red fill uses `--on-fill` / `--on-dark-fill`**, never `--text`: those two
  never invert, so a yellow badge keeps dark text in dark mode.
- **Keyframes live in the `.module.css` that uses them.** CSS Modules rename animation names
  inside a module, so a module can't use keyframes from a global stylesheet.
- **Pages compose sections; sections use `ui/` pieces.** Pages hold page-level wiring only.
- **`lib/` is plain JavaScript.** Anything that talks to the API or localStorage goes there, so
  components never build URLs or read tokens.
- **Severity colours come from one place:** `lib/severity.js` maps backend values to a tone,
  `ui/Badge` and the matrix colour by tone. The same severity is never two colours.
- **Breakpoint is 768px** (CSS variables can't be used in media queries).

## Key behaviours

| Feature | Where |
| --- | --- |
| Guest session: the consent tick next to "dig deeper" creates it, the token is reused on every later visit | `sections/landing/LaunchPanel`, `hooks/useScanLauncher`, `context/SessionContext` |
| Where "dig deeper" goes: practice target → scan, own domain → verify (registered) or register (guest) | `hooks/useScanLauncher` |
| Who can open which page, and where they're sent instead | `routes.jsx` (`access`), `layout/AccessGate` |
| Register as a guest = upgrade in place; the new token replaces the guest one (the old one is revoked) | `context/SessionContext` (`register`) |
| Sign in as a guest = the guest's scans move to the account (`guest_token` in the body) | `context/SessionContext` (`signIn`) |
| Any 401 (expired, `token_revoked`): session cleared once; registered → sign-in, guest → start page | `lib/api.js` (`onSessionExpired`), `layout/AccessGate` |
| Live scan over SSE with fetch (EventSource can't send the token) | `hooks/useScanStream`, `lib/sse.js`, `lib/api.js` (`openScanStream`) |
| Refusals (allowance, guest on own domain, unverified domain) with the right next step | `sections/scan/ScanProblem`, `lib/apiErrors.js` |
| Failed / interrupted scans: "this scan did not count" | `sections/scan/ScanProblem`, `sections/report/ScanState`, dashboard rows |
| "Stop this scan?" when leaving mid-scan (in-app and tab close) | `hooks/useLeaveGuard`, `pages/ScanRunning` |
| "based on 5 of 6 checks" + which checks could not run (mass assignment on own domains) | `sections/report/CoverageNote` |
| Reports of scans still running refresh themselves every 3s | `hooks/useScans` (`useScanDetail`) |
| Page title in the navbar's middle slot, URL input there on the desktop landing page | `layout/NavCenter`, `context/NavSlotContext` |
| Per-page `<title>` (React 19 hoists it, no helmet) | `layout/PageMeta` |
| Dark mode without a flash: saved choice, else the system setting; toggle in the navbar | `index.html`, `context/ThemeContext`, `ui/ThemeToggle` |
| Practice targets + one-click suggestions on the landing page | `lib/targets.js` (`PRACTICE_TARGETS`), `sections/landing/LaunchPanel` |
| Sound: ambiance loop on every page except verify and scan running (`ambiance: false` in routes); scan track once per scan; success / failed / error / knob cues; mute button left of the theme toggle, remembered (`shovl.sound`) | `lib/sound.js`, `context/SoundContext`, `hooks/useSounds`, `ui/SoundToggle`, `routes.jsx` |

## Sound

Files live in `src/assets/sounds/` under their export names. To replace one, overwrite the file with
the same name. Playback levels (0 to 1) and fade lengths are at the top of `lib/sound.js`.

- Browsers keep a page silent until the first click, tap or key press, so the ambiance starts then.
- Muted visitors download nothing. Otherwise the four short cues load with the page (~200 KB), the
  ambiance streams and the scan track (1.6 MB) downloads on the first gesture, so the track is ready
  when the scan page opens.
- Opening /verify or /scan/running cuts the ambiance at once, no fade. On the scan page every other sound
  (a cue still ringing included) stops and the scan track starts from the top.
- The ambiance pauses while the tab is hidden; cues still play (a scan finishing in the background).
- Which cue plays where: scan outcomes in `hooks/useSounds` (`useScanSounds`, `useScanOutcomeSound`);
  errors where they're shown (`useSoundCue`) or where they happen (`play("error")` in `useScanLauncher`,
  `AuthForm`, `VerifyAction`); the knob sound in `ui/Knob`.

## Before production

- [ ] `.env`: `VITE_API_BASE_URL` = the real API, e.g. `https://api.shovl.example/api`
- [ ] Backend `CORS_ALLOWED_ORIGINS` = this frontend's exact origin
- [ ] Fonts: `index.html` loads Arbutus + Inter. `--font-mono` asks for JetBrains Mono, which
      is not loaded, so most visitors see Courier. Add it to the Google Fonts URL if you want it.
- [ ] Practice-target lists live in two places: `src/lib/targets.js` and backend
      `domains/verification.py`. Keep them in sync.
- [ ] Settings only shows what the backend supports (email, domains, allowance). Editing, API keys
      and account deletion come back when their endpoints exist.
- [ ] The incident-report illustration on the sign-in page is still a placeholder (`sections/auth/AuthIntro`).

See `MIGRATION.md` for where every file of the previous layout went.
