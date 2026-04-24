"""Eval harness — runs all 12 test cases and generates a report."""

import asyncio
import io
import json
import sys
from datetime import date
from pathlib import Path

# Force UTF-8 stdout on Windows so ₹ and other unicode in notes don't crash prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.agents.orchestrator import OrchestratorAgent
from app.models.schemas import (
    ClaimCategory,
    ClaimHistoryItem,
    ClaimSubmission,
    DocumentInput,
)
from app.services.policy_loader import PolicyLoader


def build_submission(tc: dict) -> ClaimSubmission:
    inp = tc["input"]
    documents = [DocumentInput(**doc) for doc in inp.get("documents", [])]
    claims_history = [ClaimHistoryItem(**ch) for ch in inp.get("claims_history", [])]

    return ClaimSubmission(
        member_id=inp["member_id"],
        policy_id=inp.get("policy_id", "PLUM_GHI_2024"),
        claim_category=ClaimCategory(inp["claim_category"]),
        treatment_date=inp["treatment_date"],
        claimed_amount=inp["claimed_amount"],
        hospital_name=inp.get("hospital_name"),
        ytd_claims_amount=inp.get("ytd_claims_amount", 0),
        claims_history=claims_history,
        documents=documents,
        simulate_component_failure=inp.get("simulate_component_failure", False),
    )


async def run_all():
    test_cases_path = Path(__file__).parent.parent / "test_cases.json"
    with open(test_cases_path) as f:
        data = json.load(f)

    policy = PolicyLoader()
    results = []

    for tc in data["test_cases"]:
        case_id = tc["case_id"]
        case_name = tc["case_name"]
        expected = tc["expected"]

        try:
            submission = build_submission(tc)
            orchestrator = OrchestratorAgent(policy)
            decision = await orchestrator.process(submission)

            # Evaluate
            checks = []
            exp_decision = expected.get("decision")

            if exp_decision is not None:
                actual = decision.decision.value if decision.decision else None
                checks.append(("decision", exp_decision, actual, actual == exp_decision))
            else:
                stopped = decision.decision is None and len(decision.document_errors) > 0
                checks.append(("stopped_early", True, stopped, stopped))

            if "approved_amount" in expected:
                match = (
                    decision.approved_amount is not None
                    and abs(decision.approved_amount - expected["approved_amount"]) < 1
                )
                checks.append(("approved_amount", expected["approved_amount"], decision.approved_amount, match))

            if "rejection_reasons" in expected:
                for reason in expected["rejection_reasons"]:
                    match = reason in decision.rejection_reasons
                    checks.append((f"reason:{reason}", True, match, match))

            all_passed = all(c[3] for c in checks)

            trace_steps_data = []
            if decision.trace:
                for step in decision.trace.steps:
                    trace_steps_data.append({
                        "agent": step.agent,
                        "check_name": step.check_name,
                        "status": step.status,
                        "details": step.details,
                        "confidence_impact": step.confidence_impact,
                    })

            amount_breakdown_data = None
            if decision.amount_breakdown:
                ab = decision.amount_breakdown
                amount_breakdown_data = {
                    "original_amount": ab.original_amount,
                    "after_exclusions": ab.after_exclusions,
                    "network_discount_applied": ab.network_discount_applied,
                    "after_network_discount": ab.after_network_discount,
                    "copay_percent": ab.copay_percent,
                    "copay_amount": ab.copay_amount,
                    "after_copay": ab.after_copay,
                    "sub_limit_cap": ab.sub_limit_cap,
                    "per_claim_limit_cap": ab.per_claim_limit_cap,
                    "annual_limit_cap": ab.annual_limit_cap,
                    "final_approved": ab.final_approved,
                }

            results.append({
                "case_id": case_id,
                "case_name": case_name,
                "passed": all_passed,
                "checks": checks,
                "decision_value": decision.decision.value if decision.decision else None,
                "approved_amount": decision.approved_amount,
                "confidence": decision.confidence_score,
                "rejection_reasons": decision.rejection_reasons,
                "doc_errors": [
                    {"document_id": e.document_id, "error_type": e.error_type, "message": e.message}
                    for e in decision.document_errors
                ],
                "fraud_signals": [
                    {"flag": s.flag, "details": s.details} for s in decision.fraud_signals
                ],
                "notes": decision.notes,
                "trace_steps": trace_steps_data,
                "line_item_decisions": [
                    {"description": li.description, "amount": li.amount,
                     "status": li.status, "reason": li.reason}
                    for li in decision.line_item_decisions
                ],
                "amount_breakdown": amount_breakdown_data,
            })

        except Exception as e:
            results.append({
                "case_id": case_id,
                "case_name": case_name,
                "passed": False,
                "error": str(e),
            })

    # Print report
    passed_count = sum(1 for r in results if r.get("passed"))
    total = len(results)

    print(f"\n{'='*70}")
    print(f"  EVAL REPORT: {passed_count}/{total} test cases passed")
    print(f"{'='*70}\n")

    for r in results:
        status = "PASS" if r.get("passed") else "FAIL"
        icon = "[+]" if r.get("passed") else "[-]"
        print(f"{icon} {r['case_id']} — {r['case_name']} — {status}")

        if "error" in r:
            print(f"    ERROR: {r['error']}")
        else:
            print(f"    Decision: {r.get('decision_value')}, "
                  f"Approved: {r.get('approved_amount')}, "
                  f"Confidence: {r.get('confidence', 0):.2f}")
            if r.get("rejection_reasons"):
                print(f"    Rejection Reasons: {r['rejection_reasons']}")
            if r.get("doc_errors"):
                for de in r["doc_errors"]:
                    print(f"    Doc Error [{de['error_type']}]: {de['message']}")
            if r.get("fraud_signals"):
                for fs in r["fraud_signals"]:
                    print(f"    Fraud Signal [{fs['flag']}]: {fs['details']}")
            if r.get("notes"):
                for note in r["notes"][:3]:
                    print(f"    Note: {note[:100]}")
            trace_steps = r.get("trace_steps", [])
            print(f"    Trace Steps: {len(trace_steps)}")
            for check in r.get("checks", []):
                status_mark = "[+]" if check[3] else "[-]"
                print(f"      {status_mark} {check[0]}: expected={check[1]}, actual={check[2]}")
        print()

    # Generate markdown report
    report_path = Path(__file__).parent / "EVAL_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Eval Report\n\n")
        f.write(f"**Result: {passed_count}/{total} test cases passed**\n\n")
        f.write(f"| Case | Name | Status | Decision | Approved | Confidence |\n")
        f.write(f"|------|------|--------|----------|----------|------------|\n")
        for r in results:
            status = "PASS" if r.get("passed") else "FAIL"
            conf = r.get("confidence")
            conf_str = f"{conf:.2f}" if isinstance(conf, float) else "N/A"
            f.write(
                f"| {r['case_id']} | {r['case_name']} | {status} | "
                f"{r.get('decision_value', 'N/A')} | "
                f"{r.get('approved_amount', 'N/A')} | "
                f"{conf_str} |\n"
            )

        f.write(f"\n## Detailed Results\n\n")
        for r in results:
            status = "PASS" if r.get("passed") else "FAIL"
            f.write(f"### {r['case_id']}: {r['case_name']} — {status}\n\n")
            if "error" in r:
                f.write(f"**Error:** {r['error']}\n\n")
            else:
                f.write(f"- **Decision:** {r.get('decision_value')}\n")
                f.write(f"- **Approved Amount:** {r.get('approved_amount')}\n")
                f.write(f"- **Confidence:** {r.get('confidence', 0):.2f}\n")
                if r.get("rejection_reasons"):
                    f.write(f"- **Rejection Reasons:** {', '.join(r['rejection_reasons'])}\n")
                if r.get("notes"):
                    f.write(f"- **Notes:**\n")
                    for note in r["notes"]:
                        f.write(f"  - {note}\n")

                # Amount breakdown
                ab = r.get("amount_breakdown")
                if ab:
                    f.write(f"\n**Amount Breakdown:**\n\n")
                    f.write(f"| Step | Value |\n|------|-------|\n")
                    f.write(f"| Original claimed | ₹{ab['original_amount']:,.0f} |\n")
                    if ab.get("after_exclusions") is not None:
                        f.write(f"| After exclusions | ₹{ab['after_exclusions']:,.0f} |\n")
                    if ab.get("network_discount_applied"):
                        f.write(f"| Network discount ({ab['network_discount_applied']:.0%}) | ₹{ab['after_network_discount']:,.0f} |\n")
                    if ab.get("copay_percent"):
                        f.write(f"| Copay ({ab['copay_percent']:.0%}) | ₹{ab['after_copay']:,.0f} |\n")
                    if ab.get("sub_limit_cap"):
                        f.write(f"| Sub-limit cap | ₹{ab['sub_limit_cap']:,.0f} |\n")
                    if ab.get("per_claim_limit_cap"):
                        f.write(f"| Per-claim cap | ₹{ab['per_claim_limit_cap']:,.0f} |\n")
                    if ab.get("annual_limit_cap"):
                        f.write(f"| Annual limit cap | ₹{ab['annual_limit_cap']:,.0f} |\n")
                    f.write(f"| **Final approved** | **₹{ab['final_approved']:,.0f}** |\n")

                # Line item decisions
                line_items = r.get("line_item_decisions", [])
                if line_items:
                    f.write(f"\n**Line Item Decisions:**\n\n")
                    f.write(f"| Description | Amount | Status | Reason |\n")
                    f.write(f"|-------------|--------|--------|--------|\n")
                    for li in line_items:
                        reason = li.get("reason") or ""
                        f.write(f"| {li['description']} | ₹{li['amount']:,.0f} | {li['status']} | {reason} |\n")

                # Document errors
                doc_errors = r.get("doc_errors", [])
                if doc_errors:
                    f.write(f"\n**Document Errors:**\n\n")
                    for de in doc_errors:
                        f.write(f"- `{de['error_type']}`: {de['message']}\n")

                # Fraud signals
                fraud_signals = r.get("fraud_signals", [])
                if fraud_signals:
                    f.write(f"\n**Fraud Signals:**\n\n")
                    for fs in fraud_signals:
                        f.write(f"- `{fs['flag']}`: {fs['details']}\n")

                # Checks
                f.write(f"\n**Checks:**\n\n")
                for check in r.get("checks", []):
                    icon = "+" if check[3] else "-"
                    f.write(f"  - [{icon}] `{check[0]}`: expected=`{check[1]}`, actual=`{check[2]}`\n")

                # Full trace
                trace_steps = r.get("trace_steps", [])
                if trace_steps:
                    f.write(f"\n**Trace ({len(trace_steps)} steps):**\n\n")
                    f.write(f"| Agent | Check | Status | Confidence Δ | Details |\n")
                    f.write(f"|-------|-------|--------|--------------|---------|\n")
                    for step in trace_steps:
                        impact = step["confidence_impact"]
                        impact_str = f"{impact:+.2f}" if impact != 0 else "—"
                        details = step["details"].replace("|", "\\|").replace("\n", " ")[:120]
                        f.write(
                            f"| {step['agent']} | {step['check_name']} | {step['status']} "
                            f"| {impact_str} | {details} |\n"
                        )

            f.write("\n---\n\n")

    print(f"Report saved to: {report_path}")
    return passed_count == total


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
