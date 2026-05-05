from pydantic import BaseModel, Field


class SanctionsMatch(BaseModel):
    """Potential OFAC SDN match for an asset's operator string.

    Match = candidate, NOT a legal determination. The frontend labels
    these as "Potential SDN match" and links to OFAC for verification.
    """

    ent_num: int
    matched_name: str
    sdn_type: str | None = None
    programs: list[str] = Field(default_factory=list)
    matched_tokens: list[str] = Field(default_factory=list)
    venezuela_program: bool = False
    ofac_url: str
