# Supabase setup

This is a one-time setup. After it's done you'll never touch the Supabase
dashboard for normal development — your editor + `make` is enough.

## 1. Create a project

1. Sign in at [supabase.com](https://supabase.com) (free tier is fine).
2. **New project** → pick an org, name it `tepuy-gas-intelligence`, choose a
   region close to you (the EU regions tend to be slightly faster from LATAM
   than US-East, but anything works), set a strong **database password** —
   **save this somewhere safe**, you cannot recover it later.
3. Wait ~1 minute for the project to provision.

## 2. Enable PostGIS

PostGIS is included in every Supabase project, but you have to flip it on.

1. In your project sidebar: **Database → Extensions**.
2. Search for **postgis**.
3. Toggle it **on**. (The default schema `extensions` is fine — our migration
   uses `CREATE EXTENSION IF NOT EXISTS postgis`, which finds it wherever it
   lives.)

That's it for PostGIS. You don't need to install or configure anything else.

## 3. Get the connection string

1. **Project Settings → Database → Connection string**.
2. You'll see several tabs. Pick **URI**.
3. There are two connection strings:
   - **Direct connection** (port `5432`, host `db.<ref>.supabase.co`) — use
     this for migrations.
   - **Transaction pooler** (port `6543`) — use this for app traffic at scale.

   For v1 you can use the **direct connection** for everything. We'll switch
   the app to the pooler later if/when traffic grows.

4. Copy the URI. It looks like:

   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.abcdefg.supabase.co:5432/postgres
   ```

5. Replace `[YOUR-PASSWORD]` with the password you set in step 1 (URL-encode
   any special characters — `@` becomes `%40`, etc.).

## 4. Wire it into the project

In the **repo root**:

```bash
cp .env.example .env
```

Open `.env` and set `DATABASE_URL` to your Supabase URI, **with two changes**:

1. Prefix the scheme: `postgresql://` → `postgresql+psycopg://`
2. Append `?sslmode=require` so the driver enforces TLS.

So a complete value looks like:

```
DATABASE_URL=postgresql+psycopg://postgres:MyP%40ssword@db.abcdefg.supabase.co:5432/postgres?sslmode=require
```

## 5. Install + migrate + seed

From the repo root:

```bash
make install   # creates backend/.venv, installs Python + npm deps
make migrate   # runs Alembic against your Supabase database
make seed      # loads the 6 manual_seed pipelines
```

You should see Alembic emit `Running upgrade  -> 0001, init: postgis +
pipelines` and `make seed` print `manual_seed: upserted 6 pipelines`.

## 6. Verify in the Supabase UI

1. **Table editor** → you should see a `pipelines` table with 6 rows.
2. Click any row. The `geometry` column shows `0106...` (WKB hex — that's the
   raw PostGIS storage). The `sources` column shows the JSON attribution.
3. **SQL editor** → try:

   ```sql
   select name, status, ST_AsGeoJSON(geometry)
   from pipelines order by name;
   ```

   You should see your six rows with GeoJSON geometries.

## 7. Run the app

Two terminals:

```bash
# terminal 1
make api

# terminal 2
cd frontend
cp .env.example .env   # one-time
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Troubleshooting

**`could not translate host name "db.<ref>.supabase.co"`** — check your
internet; the host is reachable from anywhere.

**`password authentication failed`** — the password in your URL has special
characters that need URL-encoding. `@` → `%40`, `#` → `%23`, etc. Easiest
trick: in Supabase, **Settings → Database → Reset database password** and
choose a password with only alphanumerics.

**`extension "postgis" is not available`** — go back to step 2; the extension
toggle is off.

**Migration fails on a permission error** — make sure you copied the
**direct** connection string (port 5432), not the pooled one. The pooler runs
in transaction mode and can refuse some DDL operations.

**`make migrate` succeeds but Supabase Table editor shows nothing** — refresh
the page. The Table editor caches the schema list.

## What this costs

The Supabase free tier gives you:
- 500 MB database (we'll use ~tens of KB)
- 2 GB egress per month
- Pauses after 1 week of inactivity (just hit any endpoint to wake it)

For a v1 you'll never get close to those limits.
