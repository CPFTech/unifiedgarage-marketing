# UnifiedGarage - Next Steps Roadmap

*Drafted: April 16, 2026. Companion to `REVIEW.md`.*

Phased by **ship-velocity x leverage**: what gets you the most value for the smallest change, organized by what unblocks what. Each phase ends with a clear "Definition of Done" you can ship a status update on.

---

## Phase 0 - Hygiene sweep (this week, ~1 dev-day)

Prereqs for everything else. Small, safe, cumulatively high-impact.

- [ ] Push the branding fixes already applied to `my-dms` and `my-dms-frontend` (see `REVIEW.md` action checklist).
- [ ] Install `@sentry/nextjs` and wire it into the frontend (configs already written and waiting).
- [ ] Remove unused `@tanstack/react-query` dependency.
- [ ] Run `npx tsc --noEmit` and fix errors, then disable `ignoreBuildErrors` in `next.config.ts`.
- [ ] Consolidate frontend role logic into a single source of truth (`lib/rolePolicy.ts`). Delete the duplicated `ROLE_NAV`/`ROLE_PERMISSIONS` in `lib/auth.ts`.
- [ ] Audit `.env.local` files on both frontend repos - point local dev at a local backend, not prod.
- [ ] Delete debug artifacts (`__ping__`, `__size__*`, `tmp_*`, `create-tables*.js`).
- [ ] Add `typecheck`, `format`, `test` scripts to both `package.json` files.
- [ ] Set up `npm audit` as part of a weekly habit - or add Dependabot.

**DoD:** Clean `git status` in all three repos; Sentry dashboard showing events from both frontend and backend; `npm run typecheck` + `npm run lint` pass clean on both repos.

---

## Phase 1 - Pre-launch confidence (next 2-3 weeks)

The things you need before onboarding your first real non-beta dealership. Ordered by blast radius if you skip them.

### 1a. Auth hardening (highest priority)

**Migrate tokens from localStorage to httpOnly cookies.**

- Backend: `auth.service.ts` returns the refresh token via `Set-Cookie: refreshToken=...; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth/refresh`. Access token still goes in response body (short-lived, acceptable XSS risk).
- Frontend: `lib/api.ts` drops the `Bearer` header for the refresh call, uses `withCredentials: true` instead. Keep access token in memory (Zustand without persist) so a page reload triggers a refresh via cookie.
- CORS: already configured with `credentials: true` - no change needed.
- Rollout: dual-support localStorage + cookie for a release, then remove localStorage path.

**Add short-lived CSRF token** to mutation endpoints (POST/PATCH/DELETE). Double-submit cookie pattern works well with the above.

**Require MFA enrollment for DEALER_ADMIN + FINANCE_MANAGER within 7 days of first login** (currently enforced on login if enrolled, but enrollment itself isn't forced).

**DoD:** XSS in any single component can't steal a session. MFA enforcement is automatic.

### 1b. Test baseline

You don't need 80% coverage - you need tests on the **load-bearing paths** so a refactor doesn't silently break deal math.

- Backend: unit tests for `lib/worksheetCalc.ts` (pricing math), `lib/dealCalc.ts`, `src/fi/*` commission logic, `src/accounting/*` posting logic. These are pure functions; one day of work gets you durable coverage.
- Backend: integration tests for the critical auth flows (login, MFA, refresh, lockout, reset) using a test Postgres. NestJS has great `@nestjs/testing` support - one test file per flow.
- Frontend: add **one** Playwright e2e test that logs in, creates a deal, desks it, and navigates to F&I. Acts as a smoke test in CI.
- CI: wire up GitHub Actions to run `lint`, `typecheck`, `test`, `build` on every PR. Block merges on failure.

**DoD:** A failing deal math test blocks merge. CI runs on every PR. Playwright smoke passes on main.

### 1c. Observability

- Enable frontend Sentry (Phase 0).
- Wire Sentry **release tracking** - tag each release so you can bisect which deploy introduced an error.
- Add **PostHog / Plausible / Amplitude** on the marketing site and app - you need usage metrics before you're making product decisions. The marketing site is static, so this is a single `<script>` tag.
- Add a status page (statuspage.io / Atlassian Statuspage / self-hosted Uptime Kuma) - you'll want one when your first big customer calls.
- Add uptime monitoring on `api.unifiedgarage.com/api/v1/health` and `app.unifiedgarage.com`.

**DoD:** Errors surface in Sentry with source maps. Usage analytics flowing. You get an alert if the API is down for >5min.

### 1d. Backups + DR

- Confirm Railway's Postgres automated backup schedule; if it's not daily with >= 7 day retention, switch or add your own nightly `pg_dump` to S3.
- Document a restore procedure and **do a test restore at least once**. "Backups" you haven't tested restoring from are decorations.

**DoD:** You can answer "what do we do if the database is gone in 30 minutes?" confidently.

---

## Phase 2 - Early customer experience (1-2 months)

Assuming a handful of pilot dealerships are onboarded. The goal is "they stay on the platform and refer friends".

### 2a. Onboarding flow

- Self-service signup -> dealership creation -> invite team -> import inventory. Today some of this exists (`/signup`, `/accept-invite`, `/settings/import`) but it's probably not a single guided flow.
- Build a checklist component on the `/dashboard` that shows the new dealership their progress: "Invite team (done)", "Import inventory (todo)", "Set up chart of accounts (todo)", "Configure tax profile (todo)".
- **Migration assistance:** the biggest blocker for dealers switching DMSes is data migration. Build a CSV importer that maps from the top 3-5 legacy DMSes (Reynolds, CDK, Dealertrack). Charge for white-glove migration if needed.

### 2b. Customer portal polish

You already have `/portal/*` - dashboard, documents, signup, vehicle detail. Invest more here because **the portal is your best free marketing**: every customer who logs in sees the brand, and it's how dealers differentiate.

- Mobile-first redesign (customers are on phones).
- Push notifications for service RO updates ("your tech found these items", "your car is ready").
- Self-service service appointments (read-write to `/service`).
- Document signing portal (tied into F&I `/fi/sign`).

### 2c. Reporting baseline

Dealers live in reports. Ship a minimum viable set, well-designed:

- Sales by salesperson, day/week/month.
- Inventory aging (>30/60/90 days).
- Service hours billed vs. available.
- F&I product penetration.
- Gross profit by deal.

Today you have the data and route pages - the gap is likely polish (filters, exports, saved views).

### 2d. Billing

Stripe is integrated. Make sure:
- The subscription banner in the app is actually **blocking** on expired trials (UI exists; verify enforcement is server-side too).
- Dunning emails (failed payment recovery) are wired via Stripe webhooks.
- Usage metering is in place if you charge per-user or per-rooftop.

---

## Phase 3 - Scale & differentiation (quarter+)

The things that turn a solid DMS into a platform.

### 3a. Multi-rooftop maturity

You already have `admin/dealer-groups` and `storeLocationId` on users. Harden:
- Cross-rooftop customer view (a customer who bought at one store shows up at the sister store).
- Cross-rooftop inventory transfer (wholesale between stores without manual re-entry).
- Group-level reporting.
- Per-rooftop theming/branding (logos, accent colors).

### 3b. Integrations

DMSes win or lose on ecosystem. Top integrations to prioritize:
- **DMS <-> lender integrations** (RouteOne, Dealertrack - but only after you have volume; they require contracts).
- **DMS <-> inventory syndication** (Autotrader, Cars.com, CarGurus, Facebook Marketplace). Build once, every dealer uses it.
- **DMS <-> OEM portals** (factory warranty, PDI). Nice-to-have but brand-specific.
- **Accounting exports** (QuickBooks, Sage). Huge retention driver.

### 3c. AI-augmented workflows

The real 2026 edge. Examples that would be natural given your architecture:
- Deal structuring assistant in F&I menu presentation - "this customer's LTV and credit score suggest offering Plan B".
- Inventory pricing recommendations using market data + aging.
- Service upsell suggestions from inspection notes.
- Auto-drafting customer follow-ups after a test drive.

You've done the hard work of having structured data in one place; that's what makes this tractable.

### 3d. Mobile apps

Technicians and service advisors shouldn't be tied to a desktop. You already have `/tech` and `/workshop` as mobile-optimized routes - next step is a native wrapper (React Native / Capacitor) for push notifications and offline-first inspection capture.

---

## What I'm intentionally not recommending

- **Big refactors for their own sake.** The code is clean enough. Don't rewrite modules unless they're actively blocking a feature.
- **Microservices.** You're a single-service monolith with a queue; that's the right shape until you have a team that's explicitly bottlenecked by deploy coupling.
- **GraphQL migration.** REST + Swagger is working. GraphQL pays off when the API has dozens of consumers with different shapes; today you have one.
- **Moving off Railway / Vercel.** They're expensive per-compute but free per-developer-hour. You'll know when it's time.
- **Rolling your own TOTP library.** Already done, and tastefully - keep it unless audit compliance forces otherwise.

---

## Open questions for you

These are decisions only you can make - worth thinking about before Phase 1 gets underway:

1. **Target customer size.** Solo used-car lot vs. 5-rooftop group vs. 50-rooftop franchise. This drastically changes the feature weights.
2. **Pricing model.** Per-user / per-rooftop / per-deal / hybrid. Affects architecture (metering) and sales motion.
3. **Go-to-market.** Founder-led sales (customer count grows linearly with your time) vs. self-serve (product has to carry it, likely lower ACV). Different feature bets.
4. **Compliance posture.** SOC 2 timeline, GLBA/Safeguards Rule compliance (automotive dealers have financial-institution-adjacent obligations), state-level dealer license requirements. Expensive to retrofit.
5. **Runway.** How much time do you have to hit "first real revenue"? That dictates whether we prioritize polish (retention) or velocity (new features).

Happy to dig into any of these as its own conversation.
