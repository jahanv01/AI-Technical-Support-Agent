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
from concurrent.futures import ThreadPoolExecutor
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
MAX_WORKERS = 4  # modest concurrency for independent, I/O-bound eval cases -
                  # keeps runtime reasonable without hammering free-tier rate limits


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


def _run_triage_case(case: dict) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": case["id"], "task": "triage", "adversarial": case["adversarial"]}
    try:
        output = classify_ticket(TicketIn(**case["input"]))
        rule_results = check_triage_rules(output, case["rule_checks"])
        judge = judge_output(rubric=case["judge_rubric"], produced_output=output.model_dump())
        score = _combine_score(rule_results, judge["score"])
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
    return entry


def _run_account_case(case: dict, tickets_by_id: dict[str, TicketRecord], accounts_by_id: dict[str, AccountRecord]) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": case["id"], "task": "account_brief", "adversarial": case["adversarial"]}
    try:
        brief = summarize_account(case["account_id"])
        account = accounts_by_id.get(case["account_id"])
        rule_results = check_account_rules(
            brief, case["rule_checks"], account=account, tickets_by_id=tickets_by_id,
        )
        judge = judge_output(rubric=case["judge_rubric"], produced_output=brief.model_dump())
        score = _combine_score(rule_results, judge["score"])
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
    return entry


def run_all_cases(tickets_by_id: dict[str, TicketRecord], accounts_by_id: dict[str, AccountRecord]) -> list[dict[str, Any]]:
    triage_cases = json.loads((CASES_DIR / "cases_triage.json").read_text(encoding="utf-8"))
    account_cases = json.loads((CASES_DIR / "cases_account.json").read_text(encoding="utf-8"))

    jobs: list = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        jobs += [pool.submit(_run_triage_case, c) for c in triage_cases]
        jobs += [pool.submit(_run_account_case, c, tickets_by_id, accounts_by_id) for c in account_cases]
        return [job.result() for job in jobs]


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
    all_results = run_all_cases(tickets_by_id, accounts_by_id)

    report_json_path = ROOT_DIR / "eval_report.json"
    report_md_path = ROOT_DIR / "eval_report.md"
    report_json_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    report_md_path.write_text(render_markdown(all_results), encoding="utf-8")

    passed = sum(1 for r in all_results if r["passed"])
    failed = [r for r in all_results if not r["passed"]]
    quota_failures = [r for r in failed if r.get("error") and "PerDay" in r["error"]]

    print(f"{passed}/{len(all_results)} cases passed. Wrote {report_json_path.name} and {report_md_path.name}.")

    if quota_failures:
        print()
        print("QUOTA_EXHAUSTED: Daily free-tier limit (500 req/day) reached.")
        print(f"  {len(quota_failures)} case(s) failed due to quota, not logic errors.")
        print("  Options: wait until quota resets (midnight UTC), or rotate to a")
        print("  new API key in repo Settings → Secrets → GEMINI_API_KEY.")

    if failed:
        # Exit 2 = quota only (operational, not a code regression).
        # Exit 1 = at least one genuine test failure.
        raise SystemExit(2 if failed == quota_failures else 1)


if __name__ == "__main__":
    main()
