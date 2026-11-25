#!/usr/bin/env python3
"""Unit tests for the consequential stop ask (spec-review D-024).

Expected values come from the contract — gates/recommendation.md §
Consequential stops and contracts/panel.md § The report — never from
recomputing them with the code under test: a `human` report (or a
spent loop's `fix-first`) carries a stop ask whose options come from
its own state; a report with nothing to judge carries none; a
recommendation names an offered option and the criterion that picked
it, or the ask says why it is the owner's call; an unchanged spent
loop is offered no further round."""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "review_orchestrator.py"


def run(args):
    import subprocess
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


def ok(args):
    r = run(args)
    assert r.returncode == 0, f"expected ok, got {r.returncode}: {r.stdout}{r.stderr}"
    return json.loads(r.stdout)


def report(data, kind="fix"):
    return ok(["report", "--kind", kind, "--data", json.dumps(data)])


def tracked(fid, fix="pending", status="verified", severity="medium"):
    return {"finding": {"id": fid, "where": "a.py:1", "what": "w", "evidence": "e",
                        "severity": severity, "lens": "general",
                        "confirmation": {"status": status, "note": ""}},
            "fix": fix}


def base_data(*items, gate_green=True, rounds_used=2, conclusion=None,
              gate_rows=(), **extra):
    data = {"tracked": list(items), "gate_rows": list(gate_rows),
            "gate_green": gate_green, "rounds_used": rounds_used,
            "assessment": {"verdict": "v", "testGaps": [], "residualRisks": []},
            **extra}
    if conclusion is not None:
        data["conclusion"] = conclusion
    return data


def module():
    # a fresh import of the oracle module, for the derivation helpers the
    # CLI cannot reach with crafted internals
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("review_orchestrator_stop", SCRIPT)
    ro = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ro)
    return ro


class StopAskTests(unittest.TestCase):
    def test_human_report_carries_a_stop_ask_built_from_its_state(self):
        # the human criterion fires on the unconfirmed residue; the ask's
        # options come from that state (gates/recommendation.md § Consequential stops)
        d = report(base_data(
            tracked("F-1", fix="unfixed"),
            tracked("F-2", fix="pending", status="unconfirmed"),
            tracked("F-3", fix="fixed"),
            conclusion="human"))
        stop = d["stopAsk"]
        self.assertIsNotNone(stop)
        self.assertIn("F-2", stop["whatStops"])
        self.assertIn("unconfirmed", stop["whatStops"])
        self.assertIn("the recommendation gate (gates/recommendation.md)", stop["whatStops"])
        self.assertIn("risk:", stop["whyItMatters"])
        labels = [o["label"] for o in stop["options"]]
        self.assertTrue(2 <= len(labels) <= 4, labels)
        self.assertTrue(all(set(o) == {"label", "consequence"} for o in stop["options"]))
        self.assertIn("Adjudicate the unconfirmed findings", labels)
        self.assertIn("Accept the change as it is, risks on record", labels)
        # the human criterion is the rule that picks adjudication — named in the output
        self.assertEqual(stop["recommendation"], "Adjudicate the unconfirmed findings")
        self.assertIn("gates/recommendation.md", stop["recommendationReason"])
        self.assertIsNone(stop["noRecommendationReason"])

    def test_markdown_renders_the_ask_in_the_contracts_order_under_the_recommendation(self):
        d = report(base_data(tracked("F-1", fix="unfixed", status="unconfirmed"),
                             conclusion="human"))
        md = d["markdown"]
        self.assertIn("## Recommendation — human", md)
        order = ["**What stopped:**", "**Why it matters:**", "**Options:**",
                 "**Recommendation:**", "**What the answer covers:**"]
        at = [md.index(line) for line in order]
        self.assertEqual(at, sorted(at), f"ask out of contract order at {at}")
        self.assertGreater(at[0], md.index("## Recommendation"))
        self.assertIn("your yes covers exactly the chosen option and nothing else", md)

    def test_a_report_with_nothing_to_judge_carries_no_stop_ask(self):
        # merge-derivable state: everything resolved, gate green
        d = report(base_data(tracked("F-1", fix="fixed"),
                             tracked("F-2", fix="rejected-valid"),
                             conclusion="merge"))
        self.assertIsNone(d["stopAsk"])
        self.assertNotIn("**What stopped:**", d["markdown"])
        # a review-only run never recommends and never asks (D-021)
        d = report(base_data(tracked("F-1", status="unconfirmed")), kind="review")
        self.assertIsNone(d["stopAsk"])
        self.assertNotIn("## Recommendation", d["markdown"])

    def test_a_recommendation_that_names_no_option_is_dropped(self):
        ro = module()
        options = [{"label": "Adjudicate the unconfirmed findings", "consequence": "c"}]
        label, reason = ro.stop_recommendation(options, "Adjudicate the unconfirmed findings",
                                               "the human criterion")
        self.assertEqual(label, "Adjudicate the unconfirmed findings")
        self.assertEqual(reason, "the human criterion")
        label, reason = ro.stop_recommendation(options, "Run it again", "because")
        self.assertIsNone(label)
        self.assertIsNone(reason)

    def test_exhausted_rounds_with_nothing_changed_offer_no_further_round(self):
        # the fix-first criterion picks the author turn; the retry rule
        # forbids offering a round over an unchanged state
        d = report(base_data(tracked("F-1", fix="unfixed"), conclusion="fix-first"))
        stop = d["stopAsk"]
        self.assertIsNotNone(stop)
        labels = [o["label"] for o in stop["options"]]
        self.assertTrue(all("fix round" not in label for label in labels), labels)
        self.assertIn("nothing has changed since the last one", stop["whyItMatters"])
        self.assertEqual(stop["recommendation"], "Clear what remains in a normal author turn")
        self.assertIn("fix-first criterion", stop["recommendationReason"])
        self.assertIn("unresolved after 2 fix round(s)", stop["whatStops"])

    def test_a_named_change_since_the_last_attempt_reopens_the_round(self):
        d = report(base_data(tracked("F-1", fix="unfixed"), conclusion="fix-first",
                             changed_since="the owner overturned the F-2 skip ruling"))
        labels = [o["label"] for o in d["stopAsk"]["options"]]
        self.assertIn("Another fix round", labels)
        round_opt = next(o for o in d["stopAsk"]["options"]
                         if o["label"] == "Another fix round")
        self.assertIn("the owner overturned the F-2 skip ruling", round_opt["consequence"])
        # the change reopens the option, never the recommendation
        self.assertNotIn("nothing has changed since the last one",
                         d["stopAsk"]["whyItMatters"])
        self.assertNotEqual(d["stopAsk"]["recommendation"], "Another fix round")

    def test_an_out_of_scope_finding_is_the_owners_call_with_no_recommendation(self):
        # D-022: the widening call derives human and picks no option
        d = report(base_data(tracked("F-1", fix="out-of-scope"), conclusion="human"))
        stop = d["stopAsk"]
        labels = [o["label"] for o in stop["options"]]
        self.assertIn("Widen the change and fix the out-of-scope findings", labels)
        self.assertIn("Keep them out of scope and carry the findings", labels)
        self.assertIsNone(stop["recommendation"])
        self.assertIn("widening call is the owner's", stop["noRecommendationReason"])

    def test_a_standing_ci_row_recommends_the_rerun_only_when_evidence_picks_it(self):
        infra = {"name": "CI: build", "exit_code": 0, "status": "infrastructure",
                 "source": "ci", "class": "infrastructure", "failedStep": None,
                 "reason": "the run was cancelled", "rerun": "gh run rerun 4123 --failed",
                 "tail": ""}
        d = report(base_data(tracked("F-1", fix="fixed"), conclusion="human",
                             gate_rows=[infra]))
        stop = d["stopAsk"]
        self.assertEqual(stop["recommendation"], "Rerun the failed CI run")
        self.assertIn("D-023", stop["recommendationReason"])
        self.assertIn("CI: build", stop["whatStops"])
        # unknown class: no step evidence, no pick — the owner's call
        unknown = {**infra, "name": "CI: ext", "status": "unknown", "class": "unknown",
                   "reason": "no step data behind the status", "rerun": None}
        stop = report(base_data(tracked("F-1", fix="fixed"), conclusion="human",
                                gate_rows=[unknown]))["stopAsk"]
        self.assertIsNone(stop["recommendation"])
        self.assertIn("owner's call", stop["noRecommendationReason"])

    def test_an_overruled_skip_hands_over_only_when_the_verdict_says_so(self):
        # human verdict: settling the contested skip is one of the ask's options
        stop = report(base_data(tracked("F-1", fix="rejected-invalid"),
                                conclusion="human"))["stopAsk"]
        self.assertIsNone(stop["recommendation"])
        self.assertIn("Settle the overruled skips",
                      [o["label"] for o in stop["options"]])
        self.assertIn("split on the overruled skip", stop["noRecommendationReason"])
        # fix-first floor: ordinary residue an author turn clears — the move
        # is an edit, so no contested-skip hand-over, but the spent loop still asks
        stop = report(base_data(tracked("F-1", fix="rejected-invalid"),
                                conclusion="fix-first"))["stopAsk"]
        self.assertNotIn("Settle the overruled skips",
                         [o["label"] for o in stop["options"]])
        self.assertEqual(stop["recommendation"], "Clear what remains in a normal author turn")

    def test_what_stops_names_the_findings_with_their_evidence(self):
        # contract item 1: what stopped carries the evidence itself — the
        # finding's evidence beside the id, not only the id and the path
        d = report(base_data(tracked("F-2", fix="pending", status="unconfirmed"),
                             conclusion="human"))
        what = d["stopAsk"]["whatStops"]
        self.assertIn("F-2 (a.py:1) — e", what)
        self.assertNotIn("\n", what)
        # the spent loop's residue names its findings the same way
        item = tracked("F-1", fix="unfixed")
        item["finding"]["evidence"] = "the loop drops the last line"
        d = report(base_data(item, conclusion="fix-first"))
        self.assertIn("F-1 — the loop drops the last line",
                      d["stopAsk"]["whatStops"])

    def test_a_state_with_more_moves_than_slots_folds_them(self):
        # the compound state (unconfirmed + unfixed + overruled skip +
        # standing infra row + spent loop) derives six moves; the ask
        # shows four, and none its own lines name goes missing (contract
        # items 3-4): adjudicate and the rerun (the rules) and the
        # contested skips (the split) stay offered, the accept fallback
        # stays last, and a folded move's route stays stated in a kept
        # consequence
        infra = {"name": "CI: build", "exit_code": 0, "status": "infrastructure",
                 "source": "ci", "class": "infrastructure", "failedStep": None,
                 "reason": "the run was cancelled", "rerun": "gh run rerun 4123 --failed",
                 "tail": ""}
        stop = report(base_data(
            tracked("F-1", fix="pending", status="unconfirmed"),
            tracked("F-2", fix="unfixed"),
            tracked("F-3", fix="rejected-invalid"),
            tracked("F-4", fix="fixed"),
            conclusion="human", gate_rows=[infra]))["stopAsk"]
        labels = [o["label"] for o in stop["options"]]
        self.assertTrue(2 <= len(labels) <= 4, labels)
        self.assertEqual(labels[-1], "Accept the change as it is, risks on record")
        self.assertIn("Adjudicate the unconfirmed findings", labels)
        self.assertIn("Rerun the failed CI run", labels)
        self.assertIn("Settle the overruled skips", labels)
        self.assertIn("clear what remains in a normal author turn",
                      json.dumps(stop["options"]).lower())
        self.assertIn("Adjudicate the unconfirmed findings",
                      stop["noRecommendationReason"])
        self.assertIn("Rerun the failed CI run",
                      stop["noRecommendationReason"])
        # an uncrowded state keeps the follow-through option it always had
        stop = report(base_data(
            tracked("F-1", fix="pending", status="unconfirmed"),
            tracked("F-2", fix="unfixed"), conclusion="human"))["stopAsk"]
        self.assertIn("Re-enter the fix loop after adjudicating (fix_from)",
                      [o["label"] for o in stop["options"]])


if __name__ == "__main__":
    unittest.main()
