# OFAC SDN list

[U.S. Treasury OFAC](https://ofac.treasury.gov/) publishes the Specially
Designated Nationals (SDN) list as a no-headers CSV. Free, no auth.

This source ingests the full SDN list into the `sanctions_entries`
reference table. The matcher in `app/sanctions/matcher.py` reads from
this table at API request time to flag operator strings that overlap
with sanctioned entities.

## Run

```bash
make ingest-ofac                           # default: official URL
make ingest-ofac URL=<override>            # override the source URL
make ingest-ofac FILE=path/to/SDN.CSV      # parse a local file
```

`--dry-run` (parse and report Venezuela-program entries):

```bash
PYTHONPATH=backend:. backend/.venv/bin/python \
  -m data_pipeline.sources.ofac.load --dry-run
```

## Why all entries, not just Venezuela?

Operators of Venezuelan assets sometimes appear under non-Venezuela
programs (vessel designations, secondary sanctions, etc.). Storing the
full list lets the matcher catch these without a second ingest. With
~12K entries it's still trivial in storage terms.

The matcher *does* preferentially highlight Venezuela-program matches
in the UI; the full list is the haystack.

## Idempotency

Upserts by `ent_num` (OFAC's stable entity number). Re-running on the
same data is a no-op aside from `updated_at`.

## Update cadence

OFAC publishes corrections frequently — sometimes daily during active
sanctions cycles. For Tepuy v1: weekly is sufficient. Run after major
news events touching Venezuelan energy (license modifications,
designation announcements).

## Caveats

- **Match quality is not certainty.** The matcher uses normalized
  word-boundary token matching; it produces *candidates*, not legal
  determinations. The UI reflects this with "Potential SDN match"
  language and a link to the OFAC entry for analyst verification.
- **Aliases not yet ingested.** OFAC's `alt.csv` contains alternative
  names (a.k.a.s) that frequently appear in operator strings but not
  the primary SDN_Name. Adding alt.csv is a follow-up — for v1, the
  primary name catches the most common cases (PDVSA, CITGO, etc.).
- **Vessels and individuals are in the same table** as entities. We
  filter by `sdn_type = "Entity"` in the matcher when scoring candidates.
