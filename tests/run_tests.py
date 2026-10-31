"""Run the test scenarios against the real agent and save evidence.

Usage (from the repo root):
    python tests/run_tests.py                 # all scenarios, prompt v1
    python tests/run_tests.py --only T1 T2a   # selected scenarios
    python tests/run_tests.py --version v2

The API key is read from the ANTHROPIC_API_KEY environment variable, or asked for (hidden input).
It is never written to disk. Output: evidence/<id>_<version>.json
Existing evidence is never overwritten: if any selected scenario already has a file for this
version, the script stops before running anything.

Auto checks are quick factual checks on the trace and answer (which tools ran, which numbers
appear). They help the review but do not replace it: the owner fills in owner_verdict.
"""
import argparse
import datetime
import getpass
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent import tools  # noqa: E402
from agent.agent import MODEL, run_agent  # noqa: E402

SCENARIOS = ROOT / "tests" / "scenarios"
EVIDENCE = ROOT / "evidence"
NUMBER_TOLERANCE = 0.1


def numbers_in(text):
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text).replace("−", "-")  # "1,347.8" -> "1347.8"
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text)]


def auto_check(checks, answer, trace):
    called = [t["tool"] for t in trace if "tool" in t]
    found = numbers_in(answer)
    results = []
    for name in checks.get("tools_called", []):
        results.append({"check": f"tool called: {name}", "pass": name in called})
    for name in checks.get("tools_not_called", []):
        results.append({"check": f"tool NOT called: {name}", "pass": name not in called})
    for x in checks.get("numbers_in_answer", []):
        # thousands separators stripped; tolerance +/-0.1; sign-insensitive ("fell 26.9%" vs "-26.9%"),
        # signs are checked in the owner review
        results.append({"check": f"number in answer: {x}",
                        "pass": any(abs(abs(f) - abs(x)) <= NUMBER_TOLERANCE + 1e-9 for f in found)})
    if checks.get("no_adjustment_used"):
        adj = [t["input"].get("adjustment_pct", 0) for t in trace
               if t.get("tool") in ("run_forecasts", "inventory_policy", "validate")]
        results.append({"check": "no forecast adjustment used", "pass": all(not a for a in adj),
                        "adjustments_seen": adj})
    return results


def run_scenario(path, api_key, version):
    sc = json.loads(path.read_text())
    tools.REVIEW_LOG.clear()
    messages, turns, full_trace = [], [], []
    for user_text in sc["turns"]:
        answer, messages, trace = run_agent(api_key, messages + [{"role": "user", "content": user_text}], version)
        turns.append({"user": user_text, "answer": answer})
        full_trace += trace
    final_answer = "\n\n".join(t["answer"] for t in turns)
    checks = auto_check(sc.get("auto_checks", {}), final_answer, full_trace)
    evidence = {
        "scenario": sc,
        "run": {"timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                "model": MODEL, "prompt_version": version},
        "turns": turns,
        "trace": full_trace,
        "auto_checks": checks,
        "auto_checks_all_pass": all(c["pass"] for c in checks),
        "owner_verdict": None,   # PASS / FAIL, filled in by the owner after reading the answer and trace
        "owner_notes": "",
    }
    EVIDENCE.mkdir(exist_ok=True)
    out = EVIDENCE / f"{sc['id']}_{version}.json"
    with open(out, "x") as f:  # "x" = fail rather than overwrite existing evidence
        f.write(json.dumps(evidence, indent=2, default=str))
    return sc["id"], evidence["auto_checks_all_pass"], out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    api_key = os.environ.get("ANTHROPIC_API_KEY") or getpass.getpass("Anthropic API key (hidden): ")
    paths = sorted(SCENARIOS.glob("*.json"))
    if args.only:
        paths = [p for p in paths if p.stem in args.only]
    # Each scenario runs once per prompt version; the first result is the evidence.
    existing = [EVIDENCE / f"{p.stem}_{args.version}.json" for p in paths
                if (EVIDENCE / f"{p.stem}_{args.version}.json").exists()]
    if existing:
        print("STOPPED: evidence already exists and will not be overwritten:")
        for e in existing:
            print("  ", e.relative_to(ROOT))
        print("Nothing was run. Use --only to run the scenarios that have no evidence yet.")
        sys.exit(1)
    for p in paths:
        sid, ok, out = run_scenario(p, api_key, args.version)
        print(f"{sid}: auto checks {'all pass' if ok else 'SOME FAIL'} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
