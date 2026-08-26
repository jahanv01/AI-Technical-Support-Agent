"""Pydantic data contracts shared across app/ and eval/.

Keeping these separate from the raw dataset schema (see DATA_SCHEMA.md) is
deliberate: TicketRecord/AccountRecord mirror the mock dataset as-is (including
ground-truth labels used only for eval), while TriageOutput/AccountBrief are
what the LLM pipeline actually produces and must validate against.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

# --- Raw dataset records (mirrors DATA_SCHEMA.md) --------------------------


class TicketRecord(BaseModel):
    ticket_id: str
    account_id: str
    company: str
    subject: str
    body: str
    product: str
    product_area: str
    category: str
    urgency: Literal["P1", "P2", "P3", "P4"]
    status: str
    plan_tier: str
    assigned_agent: str
    created_at: str
    updated_at: str
    tags: list[str] = Field(default_factory=list)
    channel: str
    satisfaction_score: Optional[int] = None


class PrimaryContact(BaseModel):
    name: str
    title: str


class AccountRecord(BaseModel):
    account_id: str
    company: str
    tam: str
    plan_tier: str
    arr_usd: int
    seats_licensed: int
    seats_active: int
    products: list[str]
    health_status: Literal["Healthy", "At Risk", "Churning", "New"]
    usage_trend: Literal["Increasing", "Stable", "Declining", "Inactive"]
    open_tickets: int
    p1_tickets_last_30d: int
    customer_since: str
    renewal_date: str
    last_qbr_date: str
    primary_contact: PrimaryContact
    escalation_notes: list[str] = Field(default_factory=list)
    nps_score: Optional[int] = None
    last_login_days_ago: int
    integrations_active: list[str] = Field(default_factory=list)
    region: str
    industry: str


# --- Task 1: triage input/output -------------------------------------------


class TicketIn(BaseModel):
    """What the triage endpoint/function accepts. Either pass subject+body
    directly, or a raw free-text blob (normalize into subject/body upstream)."""

    subject: str
    body: str
    account_id: Optional[str] = None


class TriageOutput(BaseModel):
    product_area: str
    issue_category: str
    urgency_tier: Literal["P1", "P2", "P3", "P4"]
    reasoning: str
    matched_kb_doc: Optional[str] = None
    recommended_team: str
    draft_response: str
    needs_human_review: bool = False
    confidence: float = Field(ge=0.0, le=1.0)


# --- Task 2: account brief output -------------------------------------------


class RiskFlag(BaseModel):
    issue: str
    quote: str  # must be a verbatim substring of the source ticket body
    ticket_id: str


class AccountBrief(BaseModel):
    account_id: str
    executive_summary: str
    risks: list[RiskFlag] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    generated_from_ticket_ids: list[str] = Field(default_factory=list)
    prompt_version: str
