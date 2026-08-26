"""Eval harness orchestrator.

Run with: python -m eval.run_eval
Produces eval_report.json and eval_report.md at the repo root.

This file is fully wired up already — it runs against whatever
app.triage.classify_ticket / app.account_brief.summarize_account currently
do. Until those are implemented it will report every case as a clean
"not implemented" failure rather than crashing, so you can run this from day
one and watch cases flip to passing as you build the real logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.account_brief import summarize_account
from app.config import ACCOUNTS_PATH, ROOT_DIR, TICKETS_PATH
from app.schemas import AccountRecord, TicketIn, TicketRecord, TriageOutput
from app.triage import classify_ticket
from eval.judge import judge_output
from eval.rules import check_account_rules, check_triage_rules

CASES_DIR = Path(__file__).parent
QUALITY_PASS_THRESHOLD = 0.6  # combined rule+judge score needed to "pass"


def _load_dataset() -> tuple[dict[str, TicketRecord], dict[str, AccountRecord]]:
    tickets_raw = json.loads(TICKETS_PATH.read_text(encoding="utf-8"))
    accounts_raw = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    tickets_by_id = {t["ticket_id"]: TicketRecord(**t) for t in tickets_raw}
    accounts_by_id = {a["account_id"]: AccountRecord(**a) for a in accounts_raw}
    return tickets_by_id, accounts_by_id


def _combine_score(rule_results: list, judge_score: float | None) -> float:
    rule_score = (sum(1 for r in rule_results if r.passed) / len(rule_results)) if rule_results else 1.0
    if judge_score is None:
        return rule_score
    return 0.5 * rule_score + 0.5 * judge_score


def run_triage_cases() -> list[dict[str, Any]]:
    cases = json.loads((CASES_DIR / "cases_triage.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        entry: dict[str, Any] = {"id": case["id"], "task": "triage", "adversarial": case["adversarial"]}
        try:
            output = classify_ticket(TicketIn(**case["input"]))
            rule_results = check_triage_rules(output, case["rule_checks"])
            judge = None
            try:
                judge = judge_output(rubric=case["judge_rubric"], produced_output=output.model_dump())
            except NotImplementedError:
                pass
            judge_score = judge["score"] if judge else None
            score = _combine_score(rule_results, judge_score)
            entry.update({
                "output": output.model_dump(),
                "rule_results": [r.__dict__ for r in rule_results],
                "judge": judge,
                "quality_score": round(score, 3),
                "passed": score >= QUALITY_PASS_THRESHOLD,
                "error": None,
            })
        except NotImplementedError:
            entry.update({"quality_score": 0.0, "passed": False, "error": "classify_ticket not implemented yet"})
        except Exception as exc:  # noqa: BLE001 - surfaced in report, not swallowed
            entry.update({"quality_score": 0.0, "passed": False, "error": f"{type(exc).__name__}: {exc}"})
        results.append(entry)
    return results


def run_account_cases(tickets_by_id: dict[str, TicketRecord], accounts_by_id: dict[str, AccountRecord]) -> list[dict[str, Any]]:
    cases = json.loads((CASES_DIR / "cases_account.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        entry: dict[str, Any] = {"id": case["id"], "task": "account_brief", "adversarial": case["adversarial"]}
        try:
            brief = summarize_account(case["account_id"])
            account = accounts_by_id.get(case["account_id"])
            rule_results = check_account_rules(
                brief, case["rule_checks"], account=account, tickets_by_id=tickets_by_id,
            )
            judge = None
            try:
                judge = judge_output(rubric=case["judge_rubric"], produced_output=brief.model_dump())
            except NotImplementedError:
                pass
            judge_score = judge["score"] if judge else None
            score = _combine_score(rule_results, judge_score)
            entry.update({
                "output": brief.model_dump(),
                "rule_results": [r.__dict__ for r in rule_results],
                "judge": judge,
                "quality_score": round(score, 3),
                "passed": score >= QUALITY_PASS_THRESHOLD,
                "error": None,
            })
        except NotImplementedError:
            entry.update({"quality_score": 0.0, "passed": False, "error": "summarize_account not implemented yet"})
        except Exception as exc:  # noqa: BLE001
            entry.update({"quality_score": 0.0, "passed": False, "error": f"{type(exc).__name__}: {exc}"})
        results.append(entry)
    return results


def render_markdown(all_results: list[dict[str, Any]]) -> str:
    lines = ["# Eval Report", "", "| id | task | adversarial | passed | score | error |", "|---|---|---|---|---|---|"]
    for r in all_results:
        lines.append(
            f"| {r['id']} | {r['task']} | {r['adversarial']} | "
            f"{'✅' if r['passed'] else '❌'} | {r['quality_score']} | {r['error'] or ''} |"
        )
    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    lines += ["", f"**{passed}/{total} cases passed** (threshold: {QUALITY_PASS_THRESHOLD})"]
    return "\n".join(lines)


def main() -> None:
    tickets_by_id, accounts_by_id = _load_dataset()
    triage_results = run_triage_cases()
    account_results = run_account_cases(tickets_by_id, accounts_by_id)
    all_results = triage_results + account_results

    report_json_path = ROOT_DIR / "eval_report.json"
    report_md_path = ROOT_DIR / "eval_report.md"
    report_json_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    report_md_path.write_text(render_markdown(all_results), encoding="utf-8")

    passed = sum(1 for r in all_results if r["passed"])
    print(f"{passed}/{len(all_results)} cases passed. Wrote {report_json_path.name} and {report_md_path.name}.")
    if passed < len(all_results):
        raise SystemExit(1)  # non-zero exit so CI can gate on this


if __name__ == "__main__":
    main()
