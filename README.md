# Tepuy Intelligence — v0

Latin America energy intelligence — starting with Venezuela.

This v0 contains two screens: a login page and a protected interactive map of
Venezuela. Auth is admin-provisioned (no signup flow in the app).

## Stack

- Next.js 14 (App Router) + TypeScript
- Supabase auth via `@supabase/ssr`
- MapLibre GL JS with MapTiler tiles (OpenFreeMap fallback)
- Tailwind CSS + custom design tokens
- Fraunces / Geist / Geist Mono via `next/font/google`

## Setup

### 1. Install

```bash
npm install
```

### 2. Configure environment

Copy the example file and fill in the three keys:

```bash
cp .env.local.example .env.local
```

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_MAPTILER_KEY=
```

### 3. Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and create a new project.
2. Once provisioned, open **Project Settings → API**.
3. Copy the **Project URL** into `NEXT_PUBLIC_SUPABASE_URL`.
4. Copy the **anon public** key into `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

### 4. Create a test user (no signup in the app)

The app does not expose a signup flow — users are admin-provisioned. To create
a user manually:

1. In your Supabase project, open **Authentication → Users**.
2. Click **Add user → Create new user**.
3. Enter an email and password and check **Auto Confirm User** so the account
   is immediately active.
4. Save — those credentials now work in the login screen.

### 5. Get a MapTiler key (optional but recommended)

1. Sign up at [maptiler.com](https://www.maptiler.com/) (free tier is generous).
2. In your account dashboard, copy your default **API key**.
3. Paste it into `NEXT_PUBLIC_MAPTILER_KEY`.

If `NEXT_PUBLIC_MAPTILER_KEY` is left blank the map automatically falls back to
[OpenFreeMap](https://openfreemap.org/) (`tiles.openfreemap.org/styles/dark`),
which requires no key and has no rate limit.

### 6. Run

```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000).

- Logged out → redirected to `/login`
- Logged in → redirected to `/map`

## Scripts

- `npm run dev` — start dev server
- `npm run build` — production build
- `npm run start` — run production build
- `npm run typecheck` — TypeScript only
- `npm run lint` — ESLint

## Project structure

```
app/
  layout.tsx              root layout, fonts, globals
  page.tsx                / → /map or /login
  globals.css             design tokens + component styles
  (auth)/login/page.tsx   login screen
  (protected)/map/page.tsx  map screen
components/
  LoginForm.tsx           email/password form, calls Supabase
  TopBar.tsx              brand, region context, sign-out
  VenezuelaMap.tsx        MapLibre map with anchor markers + coords
lib/supabase/
  client.ts               browser client
  server.ts               server client (cookies)
  middleware.ts           session refresh + route protection
middleware.ts             entry that calls updateSession
```
