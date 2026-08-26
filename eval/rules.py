"""Rule-based (deterministic, free) checks for eval cases.

These are pure functions over already-produced TriageOutput/AccountBrief
objects — no LLM calls here. Each check returns (passed: bool, detail: str)
so run_eval.py can report exactly which rule fired and why.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas import AccountBrief, AccountRecord, TicketRecord, TriageOutput


@dataclass
class RuleResult:
    name: str
    passed: bool
    detail: str


def check_triage_rules(output: TriageOutput, rule_checks: dict) -> list[RuleResult]:
    results: list[RuleResult] = []

    if "issue_category_in" in rule_checks:
        allowed = rule_checks["issue_category_in"]
        ok = output.issue_category in allowed
        results.append(RuleResult(
            "issue_category_in", ok,
            f"got '{output.issue_category}', expected one of {allowed}",
        ))

    if "urgency_tier_in" in rule_checks:
        allowed = rule_checks["urgency_tier_in"]
        ok = output.urgency_tier in allowed
        results.append(RuleResult(
            "urgency_tier_in", ok,
            f"got '{output.urgency_tier}', expected one of {allowed}",
        ))

    if "product_area_contains_any" in rule_checks:
        needles = rule_checks["product_area_contains_any"]
        hay = output.product_area.lower()
        ok = any(n.lower() in hay for n in needles)
        results.append(RuleResult(
            "product_area_contains_any", ok,
            f"product_area='{output.product_area}' vs any of {needles}",
        ))

    if "reasoning_contains_any" in rule_checks:
        needles = rule_checks["reasoning_contains_any"]
        hay = output.reasoning.lower()
        ok = any(n.lower() in hay for n in needles)
        results.append(RuleResult(
            "reasoning_contains_any", ok,
            f"reasoning did{''if ok else ' not'} mention any of {needles}",
        ))

    if "needs_human_review" in rule_checks:
        expected = rule_checks["needs_human_review"]
        ok = output.needs_human_review == expected
        results.append(RuleResult(
            "needs_human_review", ok,
            f"got {output.needs_human_review}, expected {expected}",
        ))

    if "matched_kb_doc_is_null" in rule_checks:
        expected = rule_checks["matched_kb_doc_is_null"]
        ok = (output.matched_kb_doc is None) == expected
        results.append(RuleResult(
            "matched_kb_doc_is_null", ok,
            f"matched_kb_doc={output.matched_kb_doc!r}",
        ))

    if "max_confidence" in rule_checks:
        threshold = rule_checks["max_confidence"]
        ok = output.confidence <= threshold
        results.append(RuleResult(
            "max_confidence", ok,
            f"confidence={output.confidence} vs max {threshold}",
        ))

    return results


def check_account_rules(
    brief: AccountBrief,
    rule_checks: dict,
    *,
    account: AccountRecord | None,
    tickets_by_id: dict[str, TicketRecord],
) -> list[RuleResult]:
    results: list[RuleResult] = []

    if "account_exists" in rule_checks:
        expected = rule_checks["account_exists"]
        ok = (account is not None) == expected
        results.append(RuleResult("account_exists", ok, f"account found={account is not None}"))

    if "min_risk_flags" in rule_checks:
        minimum = rule_checks["min_risk_flags"]
        ok = len(brief.risks) >= minimum
        results.append(RuleResult(
            "min_risk_flags", ok, f"got {len(brief.risks)} risks, need >= {minimum}",
        ))

    if "max_risk_flags" in rule_checks:
        maximum = rule_checks["max_risk_flags"]
        ok = len(brief.risks) <= maximum
        results.append(RuleResult(
            "max_risk_flags", ok, f"got {len(brief.risks)} risks, need <= {maximum}",
        ))

    if rule_checks.get("quotes_must_be_verbatim"):
        all_grounded = True
        bad_quotes = []
        notes_blob = " ".join(account.escalation_notes) if account else ""
        for risk in brief.risks:
            if risk.ticket_id == "account_notes":
                grounded = risk.quote in notes_blob
            else:
                ticket = tickets_by_id.get(risk.ticket_id)
                grounded = ticket is not None and risk.quote in ticket.body
            if not grounded:
                all_grounded = False
                bad_quotes.append(risk.quote)
        results.append(RuleResult(
            "quotes_must_be_verbatim", all_grounded,
            "all quotes verbatim-grounded" if all_grounded else f"ungrounded quotes: {bad_quotes}",
        ))

    if "expected_quote_substrings_any" in rule_checks:
        needles = rule_checks["expected_quote_substrings_any"]
        all_quotes = " ".join(r.quote for r in brief.risks)
        ok = any(n in all_quotes for n in needles)
        results.append(RuleResult(
            "expected_quote_substrings_any", ok,
            f"risk quotes did{'' if ok else ' not'} include any of {needles}",
        ))

    if rule_checks.get("executive_summary_not_empty"):
        ok = len(brief.executive_summary.strip()) > 0
        results.append(RuleResult("executive_summary_not_empty", ok, ""))

    return results
