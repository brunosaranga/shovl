# Where everything went

The previous frontend kept every style in one 2,600-line `styles/global.css` and some logic inside
components. This maps each old file to its new home. Delete this file once you're used to the layout.

## Logic

| Old | New |
| --- | --- |
| `App.jsx` (routes + ProtectedRoute) | `routes.jsx` (pages + access levels) and `components/layout/AccessGate` |
| `context/AuthContext.jsx`, `hooks/useAuth.js` | `context/SessionContext.jsx` (`useSession`) — now knows guests, upgrade, expiry |
| `components/auth/ProtectedRoute.jsx` | `components/layout/AccessGate` (driven by `access` in `routes.jsx`) |
| `api/client.js` | `lib/api.js` (axios, endpoints, stream) + `lib/session.js` (token storage) |
| `api/targets.js` | `lib/targets.js` (unchanged logic) |
| `hooks/useScanStream.js` | `hooks/useScanStream.js` (refusals, failed, interrupted, retry) + `lib/sse.js` |
| `components/scan/HandleScan.jsx` (`useScan`) | `hooks/useScanLauncher.js` |
| `hooks/useWindowSize.js` | `hooks/useMediaQuery.js` (`useMediaQuery(MOBILE_QUERY)`) |
| `context/ThemeContext.jsx` | removed (unused, no dark styles yet; tokens.css is ready for one) |
| `components/common/RiskColors.jsx`, `common/riskHeadline.js`, colour maps in FindingItem and SeverityMatrix | `lib/severity.js` + `ui/Badge` tones (one mapping) |
| `components/common/MockScans.jsx` | removed: the dashboard reads `/api/scans/` |
| DomainVerification's create-then-list effect | `hooks/useDomainSetup.js` (lists first, adds only when missing) |

## Components

| Old | New |
| --- | --- |
| `layout/PageShell.jsx` | `layout/Layout` (route shell with `<Outlet />`) — pages no longer wrap themselves |
| PageShell's `centerElement` prop | `<NavCenter>…</NavCenter>` inside the page |
| `layout/Navbar.jsx` | `layout/Navbar/Navbar.jsx` + `AccountMenu.jsx` |
| `layout/GroundCanvas.jsx` | `layout/Ground` |
| `layout/Footer.jsx` | `layout/Footer` |
| `layout/Buttons.jsx` (`PrimaryButton`) | `ui/Button` (`variant="primary"`, plus `stop`, `small`, `danger`, `dark`, `quiet`) |
| `layout/Pagination.jsx` (static) | `ui/Pagination` (works) |
| `common/PageTitle.jsx` | `ui/PageTitle` |
| `scan/KnobToggle.jsx` | `ui/Knob` (now a real button with `aria-pressed`) |
| `scan/URLInput.jsx` | `forms/UrlInput` |
| `landing/ToggleRow.jsx` | `sections/landing/ScanOptions` |
| `landing/BrandHero.jsx`, `landing/BrandHeader.jsx` | `sections/landing/BrandHero`, `sections/landing/BrandHeader` |
| "dig deeper" button in Landing | `sections/landing/LaunchPanel` (button + consent + scans left + errors) |
| `pages/Auth.jsx` form | `forms/AuthForm` + `sections/auth/AuthTabs` + `sections/auth/AuthIntro` |
| `domain-verification/DomainVerificationCard.jsx` | `sections/verify/VerifyIntro` + `sections/verify/DnsInstructions` |
| `domain-verification/TriggerVerification.jsx` | `sections/verify/VerifyAction` |
| `domain-verification/CopyToClipboard.jsx` | `ui/CopyField` |
| `scan-running/ScanHeader.jsx` | `sections/scan/ScanHeader` |
| `scan-running/ScanProgressBar.jsx` | `ui/ProgressBar` |
| `scan-running/ScanTerminal.jsx` | `ui/Terminal` |
| `report/ReportMetaCard.jsx` | `sections/report/ReportMeta` (+ `sections/report/CoverageNote`) |
| `report/SeverityMatrix.jsx` | `sections/report/SeverityMatrix` |
| `report/FindingsList.jsx`, `report/FindingItem.jsx` | `sections/report/Findings/` (open state moved inside) |
| `dashboard/ScansStats.jsx` | `sections/dashboard/ScanStats` |
| `dashboard/ScanList.jsx` | `sections/dashboard/ScanList/` (`ScanList.jsx` + `ScanRow.jsx`) |
| Settings page markup | `sections/settings/SettingsSection` (`SettingsSection` + `SettingsRow`) |
| Empty placeholder files (`NewScan.jsx`, `AuthTabs.jsx`, `ScanCard.jsx`, `ProgressBar.jsx`…) | removed |

## Styles

| Old | New |
| --- | --- |
| `styles/global.css` `:root` + `styles/variables.css` | `styles/tokens.css` (two layers: raw palette → semantic) |
| `styles/global.css` `* {}` / `body {}` + `index.css` | `styles/reset.css` + `styles/base.css` |
| Every other rule in `global.css` | the `.module.css` next to the component that uses it |
| `App.css`, `styles/components.css`, `styles/old ideas*.css` | not carried over (unused) |
| Google Fonts `@import` in CSS | `<link>` in `index.html` (loads in parallel) |

## Assets

| Old | New |
| --- | --- |
| `assets/shovl-logo.svg`, `ShovelGraphic.svg`, `UserAvatar.svg` | `assets/logos/` |
| `assets/*Knob*.svg` | `assets/knobs/` |
| `assets/ground.png` (4.8 MB) | `assets/images/ground.webp` (2880px wide, ~220 KB) |
| `assets/delimit.svg` | `assets/images/delimit.svg` (unused, kept) |
| `assets/hero.png`, `react.svg`, `vite.svg`, `public/icons.svg` | removed (Vite template leftovers) |

## Visible differences (on purpose)

- One severity scale everywhere: HIGH orange, MEDIUM yellow, LOW green, PASS grey, "could not run" slate.
  Before, the matrix showed HIGH in red and LOW in yellow while the badges used other colours.
- The red debug border around the navbar page title is gone.
- The "expand all / collapse all" buttons are styled (they were unstyled browser buttons).
- Mobile: page titles are readable in the dark bottom bar, content starts near the top instead of
  150px down, and dashboard rows wrap instead of running off the screen.
- New: the consent tick and scans-left line next to "dig deeper", the guest notice on the dashboard,
  the coverage note on reports, the leave-scan dialog, and the problem panels.
