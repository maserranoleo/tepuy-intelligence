"""OFAC fuzzy matcher.

Scope of v1: a deliberately simple word-boundary token matcher against the
`sanctions_entries` table. False-positive-tolerant; the UI labels matches as
"potential" and links to the OFAC entry for analyst verification.

Algorithm:
  1. Normalize the operator string (uppercase, strip punctuation, collapse
     whitespace), tokenize.
  2. Drop tokens shorter than 4 chars (avoids "GAS" / "ENI" noise) and a
     short stoplist of generic energy words ("GAS", "OIL", "ENERGY", "S",
     "A", "DE", "Y") that match on too many SDN entries.
  3. For each surviving token, find sanctions entries whose
     `sdn_name_normalized` contains the token as a whole word.
  4. Rank: Venezuela-program matches first; ties broken by number of
     tokens matched.
  5. Cap to N matches per operator.

The matcher loads its haystack once from the DB at construction time. In
the API we instantiate it per-request via FastAPI Depends — load cost is
~10ms for the full SDN list and reused across all rows in that response.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sanctions_entry import SanctionsEntry

logger = logging.getLogger("sanctions.matcher")

MIN_TOKEN_LENGTH = 4
MAX_MATCHES = 5

# Tokens that, even at length 4+, match too broadly to be useful signal.
STOPLIST = {
    "GAS", "OIL", "PETROLEO", "PETROLEOS", "ENERGY", "ENERGIA", "ENERGIES",
    "COMPANY", "CORP", "CORPORATION", "INC", "LIMITED", "LTD", "GROUP",
    "HOLDING", "HOLDINGS", "INTERNATIONAL", "GLOBAL", "REFINERIA", "REFINERY",
}

VENEZUELA_PROGRAM_RE = re.compile(r"VENEZUELA", re.I)


@dataclass(frozen=True)
class SanctionsMatch:
    ent_num: int
    matched_name: str
    sdn_type: str | None
    programs: list[str]
    matched_tokens: list[str]
    venezuela_program: bool
    ofac_url: str

    def to_jsonable(self) -> dict:
        return {
            "ent_num": self.ent_num,
            "matched_name": self.matched_name,
            "sdn_type": self.sdn_type,
            "programs": self.programs,
            "matched_tokens": self.matched_tokens,
            "venezuela_program": self.venezuela_program,
            "ofac_url": self.ofac_url,
        }


def _normalize(s: str) -> str:
    s = s.upper()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize(operator: str) -> list[str]:
    norm = _normalize(operator)
    tokens = [t for t in norm.split() if len(t) >= MIN_TOKEN_LENGTH]
    return [t for t in tokens if t not in STOPLIST]


@dataclass
class _Entry:
    ent_num: int
    sdn_name: str
    sdn_name_normalized: str
    sdn_type: str | None
    programs: list[str]
    venezuela: bool


class SanctionsMatcher:
    """In-memory matcher built from the `sanctions_entries` table.

    Construct once per request (cheap — a few hundred rows or low thousands
    of rows). Reuse across every entity in that response.
    """

    def __init__(self, entries: list[_Entry]) -> None:
        self._entries = entries

    @classmethod
    def from_db(cls, db: Session) -> "SanctionsMatcher":
        rows = db.execute(select(SanctionsEntry)).scalars().all()
        entries = [
            _Entry(
                ent_num=r.ent_num,
                sdn_name=r.sdn_name,
                sdn_name_normalized=r.sdn_name_normalized,
                sdn_type=r.sdn_type,
                programs=list(r.programs or []),
                venezuela=any(VENEZUELA_PROGRAM_RE.search(p) for p in (r.programs or [])),
            )
            for r in rows
        ]
        return cls(entries)

    def match(self, operator: str | None) -> list[SanctionsMatch]:
        if not operator:
            return []
        tokens = _tokenize(operator)
        if not tokens:
            return []
        # Pre-compile word-boundary regexes once per call.
        token_res = [(t, re.compile(rf"\b{re.escape(t)}\b")) for t in tokens]

        scored: list[tuple[int, int, SanctionsMatch]] = []
        for e in self._entries:
            matched = [t for t, rx in token_res if rx.search(e.sdn_name_normalized)]
            if not matched:
                continue
            score_ven = 1 if e.venezuela else 0
            score_tokens = len(matched)
            scored.append(
                (
                    -score_ven,        # Venezuela first (negate for ascending sort)
                    -score_tokens,     # more tokens better
                    SanctionsMatch(
                        ent_num=e.ent_num,
                        matched_name=e.sdn_name,
                        sdn_type=e.sdn_type,
                        programs=e.programs,
                        matched_tokens=matched,
                        venezuela_program=e.venezuela,
                        ofac_url=(
                            "https://sanctionssearch.ofac.treas.gov/Details.aspx?id="
                            f"{e.ent_num}"
                        ),
                    ),
                )
            )

        scored.sort(key=lambda x: (x[0], x[1]))
        return [m for _, _, m in scored[:MAX_MATCHES]]
