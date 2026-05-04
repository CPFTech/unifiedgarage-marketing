# UnifiedGarage - Platform Review

*Review date: April 16, 2026*
*Scope: `unifiedgarage-marketing` + `my-dms-frontend` + `my-dms`*

This is an opinionated technical review across security, code quality, performance, and product direction. Items marked **[FIXED]** were changed during this session. **[FLAG]** items need your decision before changing. **[SAFE-TO-DO]** items are batched for follow-up work you can tackle at your pace.

---

## TL;DR

You're in a better place than most stealth-stage B2B SaaS at this maturity level. The NestJS backend is genuinely production-grade: proper JWT+refresh, TOTP MFA with recovery codes, account lockout, rate limiting, structured logging with secret redaction, Sentry error tracking, raw-body Stripe webhooks. The biggest risk areas are (a) **tokens in localStorage** (XSS blast radius), (b) **`ignoreBuildErrors: true` in Next config** (TypeScript errors silently shipping to prod), and (c) **duplicated role logic between two frontend files that have drifted out of sync**.

The marketing site is now fully cleaned up (see commit history of `unifiedgarage-marketing`).

---

## Architecture recap (as-found)

```
unifiedgarage.com       ->  Vercel static     ->  unifiedgarage-marketing (just index.html + HTML)
app.unifiedgarage.com   ->  Vercel            ->  my-dms-frontend (Next.js 16 + React 19)
api.unifiedgarage.com   ->  Railway (Docker)  ->  my-dms (NestJS 10 + Prisma 5 + Postgres)
Cross-cutting: Sentry (errors), Resend (email), Stripe (billing), AWS S3 (storage), pg-boss (jobs)
```

Auth: JWT access token (15m) + opaque refresh token (30d), stored client-side in Zustand-persisted `localStorage`. TOTP MFA required for SUPER_ADMIN / DEALER_ADMIN / FINANCE_MANAGER. 9 roles total.

Data model: 66 Prisma models spanning inventory, deals, F&I, service, parts, accounting, CRM, portal, commissions, appraisals, workflows.

---

## Marketing site (`unifiedgarage-marketing`) - DONE

All done this session. Final commit `964bccd` on `main`:

**[FIXED]** Recovered `index.html` - it was truncated mid-sentence locally (still fine on GitHub).
**[FIXED]** Added Open Graph + Twitter Card + canonical + JSON-LD structured data for social/SEO.
**[FIXED]** Added inline SVG favicon (brand yellow with `U` glyph).
**[FIXED]** Added `<main>` landmark, skip link, `aria-hidden` on decorative mockup.
**[FIXED]** Added `privacy.html` + `terms.html` (beta placeholders - **will need legal review before GA**).
**[FIXED]** Added custom `404.html` (on-brand).
**[FIXED]** Added `robots.txt` + `sitemap.xml`.
**[FIXED]** Dropped broken `#pricing` footer link (no pricing section exists yet).
**[FIXED]** Vercel GitHub webhook reconnected - pushes now auto-deploy in ~30s.

**[FLAG]** OG/Twitter meta reference `/og-image.png` which doesn't exist. Social cards will work but have no preview image until we add one. Easy to auto-generate a 1200x630 PNG with the brand yellow + "UnifiedGarage" + tagline. Want me to generate one?

**[SAFE-TO-DO]** Privacy/Terms pages are placeholders and marked as such. They need a lawyer pass before you remove the "beta placeholder" notice banner.

---

## Frontend (`my-dms-frontend`)

### Security / auth

**[FLAG, HIGH]** Tokens (access + refresh) are persisted in `localStorage`. Standard convenience choice but it means *any* XSS leads to full session theft. For a DMS handling customer PII, deal/finance data, and payment info, **httpOnly + SameSite=Lax cookies set by the backend is the recommended pattern**. This is a real refactor (backend must switch to cookie-based auth, `lib/api.ts` drops the bearer header, CORS+origin tightens), but it's the single biggest security upgrade you can make. Worth scheduling.

**[FLAG, MEDIUM]** `lib/auth.ts` has `ROLE_NAV` and `lib/rolePolicy.ts` has `NAV_ACCESS` - **two copies of role-to-nav mapping that are not in sync** (e.g. `TECHNICIAN` is `['tech']` in one, `['service']` in the other). `DmsLayout.tsx` uses `rolePolicy.ts`, but `Sidebar.tsx` may use the other. Consolidate into `rolePolicy.ts` as the single source of truth; delete the `ROLE_NAV` and `ROLE_PERMISSIONS` constants in `auth.ts`.

**[FLAG, MEDIUM]** `lib/getToken.ts` appears to be a **dead/legacy auth path** that checks different localStorage keys (`token`, `accessToken`) than the current Zustand-persisted `dms-auth` key. If anything still imports `getToken()`, it will return `null` for logged-in users (since the primary path is `dms-auth`). Either audit callers and migrate to `getAccessToken()` from `auth.ts`, or delete `getToken.ts` outright. Run: `grep -rn "from.*getToken" --include='*.ts*'` to find callers.

**[FLAG, LOW]** `canAccess` policy is enforced **only** in `DmsLayout.tsx` (client-side redirect). No Next.js middleware, no per-page server check. For the dealer dashboard this is fine because the backend enforces role guards server-side - but document that clearly so no one adds a "trust the client" shortcut later.

### Code quality

**[FIXED]** README was unmodified `create-next-app` boilerplate - replaced with a real architecture overview.

**[FLAG, MEDIUM]** `next.config.ts` sets `typescript: { ignoreBuildErrors: true }`. This means TS errors do NOT fail `next build`, so broken types ship to prod silently. Run `npx tsc --noEmit` from the repo root to see how many errors this is masking. Recommendation: fix the errors (probably a handful), then flip this to `false`.

**[FLAG, MEDIUM]** Sentry config files (`sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`) reference `@sentry/nextjs`, but that **package is not in `package.json`**. Frontend error tracking is currently a no-op in prod. Two paths: install the package (`npm i @sentry/nextjs`, then wrap `next.config.ts` with `withSentryConfig`), or delete the config files. Given you already have Sentry set up on the backend, installing it on the frontend for parity is the right call.

**[FLAG, LOW]** `@tanstack/react-query` is listed in `package.json` but has **zero imports anywhere in the codebase**. Remove it (`npm uninstall @tanstack/react-query`) to shrink the bundle.

**[FLAG, LOW]** `package.json` scripts are minimal - no `typecheck`, no `format`, no `test`. Suggest adding:

```json
"typecheck": "tsc --noEmit",
"format": "prettier --write \"**/*.{ts,tsx,md}\"",
"test": "echo 'No tests yet - consider Vitest for components, Playwright for e2e' && exit 0"
```

**[SAFE-TO-DO]** `.env.local` and `.env.production` both point to the Railway **production** backend. Local dev writes to prod data. Split into a real dev env (local NestJS pointing at a local Postgres, or a dedicated Railway staging project).

**[SAFE-TO-DO]** Debug artifacts in repo root: `__ping__`, `__size__app/`, `__size__components/`, `__size__lib/`, `__size__types/`. They're gitignored so local-only, but they clutter `ls`. Clean with `rm -rf __ping__ __size__*`.

### Missing tooling

No test runner, no Storybook, no visual regression, no lint-staged / husky, no CI config visible. For an app of this scope (67+ routes, 9 roles, accounting/F&I logic) the lack of tests is a real risk - the kind of bug that breaks a deal posting won't be caught until a customer reports it. Recommendations in roadmap.

---

## Backend (`my-dms`)

### What's working well

This is a mature, thoughtful codebase. Highlights:

- **Proper JWT + refresh separation** with correct refresh-token rotation, session context (IP/UA), and `logoutEverywhere` support.
- **Account lockout** with escalating durations (15m to 30m to 60m cap) and user-enumeration-resistant error responses.
- **Rate limiting** via `@nestjs/throttler` on login/refresh/reset endpoints with appropriate limits.
- **TOTP MFA** (RFC 6238) with recovery codes, enforced for privileged roles.
- **Structured logging** via pino with `password` / `passwordHash` / `authorization` automatically redacted.
- **Sentry** integrated at the `main.ts` bootstrap level (before module imports) with 5xx-only forwarding - no caller-error noise.
- **Raw-body capture** for Stripe webhooks done correctly (before `setGlobalPrefix`).
- **OpenAPI/Swagger** generated and production-gated.
- **CORS** uses an explicit allowlist (no wildcards) with `credentials: true`.
- **Validation pipe** with `whitelist: true` globally.
- **pg-boss** job queue and `@nestjs/schedule` for recurring work.

### Fixes applied this session

**[FIXED]** `src/auth/mfa.service.ts` - TOTP issuer default was `'Smith Auto DMS'` (leaks into users' authenticator apps). Changed to `'UnifiedGarage'`.
**[FIXED]** `src/email/email.service.ts` - `APP_NAME` default was `'Smith Auto DMS'`, `APP_URL` default was `'http://localhost:3001'`. Updated both to UnifiedGarage values. (These are env-overridable - in prod you should set `APP_NAME` + `APP_URL` explicitly anyway, but the defaults now won't leak old branding if someone forgets.)
**[FIXED]** `src/main.ts` - Swagger contact was `'DMS Support'` / `support@dealermanagementsystem.com`. Updated to `UnifiedGarage Support` / `support@unifiedgarage.com`.

### Flagged items

**[FLAG, MEDIUM]** `credentials: true` in the CORS config but the frontend uses **Bearer tokens in localStorage, not cookies**. `credentials: true` has no effect today - it's only needed if/when you migrate to httpOnly cookie auth (see frontend section). Leave it as-is if that migration is on the roadmap, otherwise drop it.

**[FLAG, LOW]** Swagger is exposed at `/api/v1/docs` for any non-production `NODE_ENV`. Fine - but make sure `NODE_ENV=production` is set on Railway. Verify with: `curl -sI https://api.unifiedgarage.com/api/v1/docs` and confirm 404.

**[SAFE-TO-DO]** Root-level debug/tmp files: `__list_migrations__.js`, `__ping__`, `tmp_frontend_api.txt`, `tmp_read.js`, `tmp_runner_output.txt`, `create-tables.js`, `create-po-tables.js`. Some are scratch work, some were one-off migration helpers. The `create-tables*` scripts are now superseded by Prisma migrations - delete them. The `tmp_*` and `__*` files are safe to delete.

**[SAFE-TO-DO]** Setup docs: `WEEK1-SETUP.md`, `WEEK2-SETUP.md`, `WEEK3-SETUP.md`, `WEEK4A/B/C-SETUP.md` - these are ephemeral planning docs from your build process. Once the platform is stable, consider moving them to a `docs/history/` folder or deleting; they'll get stale and confuse future contributors.

**[SAFE-TO-DO]** `PLATFORM-REVIEW.md` (17KB) - you already did an internal review. Worth cross-referencing its findings against this one; reconcile and consolidate into a single living `docs/REVIEW.md`.

**[SAFE-TO-DO]** `create-admin.ts` and `create-test-users.ts` - dev-only seed scripts. Keep them, but make sure `NODE_ENV=production` in the script guards `if (NODE_ENV === 'production') process.exit(1)` so they can't accidentally run against Railway.

### Data / schema

Not reviewed in detail (66 models, 2312-line `schema.prisma`). A focused schema review would be a separate session - but spot-check recommendations:

**[SAFE-TO-DO]** Confirm every tenant-scoped model has a `dealershipId` foreign key and a database-level index on it. A `grep "@@index" prisma/schema.prisma | wc -l` should be comparable to your number of multi-tenant models.

**[SAFE-TO-DO]** Confirm cascade/restrict behavior is consistent on foreign keys - mixed `onDelete: Cascade` vs. `onDelete: Restrict` is a classic source of "why did deleting this customer wipe their deals" bugs.

**[SAFE-TO-DO]** Prisma migration hygiene: `prisma migrate deploy` should be run on Railway startup (check `startup.js`). `prisma db push` is a dev-only convenience and should never run in prod.

---

## Cross-cutting observations

**Branding consistency:** Marketing uses Inter font; app uses Geist. Not necessarily wrong, but worth deciding if that's intentional (marketing = friendly, app = workstation) or accidental.

**Observability:** Sentry is in good shape server-side. Frontend error tracking is unwired (see above). Structured request logs via pino are great - make sure Railway's log aggregation is set up to query them by `reqId` or user id.

**Rate limiting:** throttler is applied to auth endpoints. Consider a more aggressive default for mutation endpoints (POST/PATCH/DELETE) - especially anything that triggers emails, writes to S3, or calls Stripe.

**Secret hygiene:** `.env` files gitignored on both app repos. No secrets found in tracked files. Backend `.env` has only dev placeholder values. Good.

**Dependency freshness:** NestJS 10 is current. Prisma 5 is current (6 is out but breaking). Next 16 is literally the bleeding edge. React 19 is current. No critically outdated majors. `npm audit` on both would be a quick win.

---

## Immediate action checklist (pick what to do now)

1. `[FIXED]` Marketing site SEO/a11y/legal stubs/404 - shipped.
2. `[FIXED]` Backend branding cleanup - shipped.
3. `[FIXED]` Frontend README rewrite - shipped.
4. `[15 min]` Decide on Sentry frontend: `npm i @sentry/nextjs` OR delete the three `sentry.*.config.ts` files. (I recommend installing it.)
5. `[5 min]` `npm uninstall @tanstack/react-query` in `my-dms-frontend`.
6. `[30 min]` Run `npx tsc --noEmit` in `my-dms-frontend`, fix the errors it surfaces, then set `ignoreBuildErrors: false` in `next.config.ts`.
7. `[15 min]` Consolidate role logic: delete `ROLE_NAV` + `ROLE_PERMISSIONS` from `lib/auth.ts`, migrate callers to `rolePolicy.ts`. Keep `ROLE_PERMISSIONS` logic but rehome it next to `NAV_ACCESS`.

See `ROADMAP.md` for the bigger picture.
