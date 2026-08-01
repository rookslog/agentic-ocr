"""Round-3 cross-vendor review regressions — every measured probe, as a test.

Both round-3 reviewers reproduced concrete inputs that the round-2 suite scored
wrongly. Each is pinned here with the behaviour it must now have. Grouped by the
consolidated fix that closes it.

Pre-fix behaviour, for the record:

    smear (every region := whole page)      exit 0  ← exploit passed
    truncated reading_order + reversed idx  exit 0, tau 1.0  ← exploit passed
    string-valued reading_order             exit 0  ← exploit passed
    null entry in regions                   exit 0  ← exploit passed
    GT nested 40 deep                       exit 0  ← GT silently truncated
    "Book I" -> "Book l"                    exit 1  ← honest candidate false-failed
    40 regions, 1 hyphenation artifact      exit 1  ← honest candidate false-failed
    17-node IoU component                   16 of 17 matched (greedy fallback)
    1 candidate vs ~1000 GT regions         RecursionError in 4 checkers
"""

from __future__ import annotations

import copy
import time

import pytest

from eval.checkers import build_default_suite, run_checkers
from eval.checkers.align import align_regions
from eval.checkers.pagegt import MAX_REGION_DEPTH, PageView
from tests import _mutations as M


def _card(candidate, gt):
    return run_checkers(candidate, gt, build_default_suite())


def _verdicts(candidate, gt) -> dict[str, bool]:
    return {r.id: r.passed for r in _card(candidate, gt).results}


def _result(candidate, gt, checker_id):
    return next(r for r in _card(candidate, gt).results if r.id == checker_id)


# ── FIX-A: order-signal integrity (L1-1) ──────────────────────────────────────


def test_truncated_reading_order_with_reversed_indices_fails(apparatus_gt, apparatus_candidate):
    exploit = M.truncate_reading_order(apparatus_candidate, keep=1)
    card = _card(exploit, apparatus_gt)
    assert card.exit_code() == 1, card.render()
    verdicts = {r.id: r.passed for r in card.results}
    assert verdicts["structural-contract"] is False
    # And the order signal itself is no longer suppressible: the index evidence now
    # drives the comparison, so tau reflects the reversal instead of reading 1.0.
    order = next(r for r in card.results if r.id == "reading-order")
    assert order.passed is False
    assert order.metrics["kendall_tau"] < 1.0


def test_reading_order_contradicting_its_indices_is_a_violation(
    apparatus_gt, apparatus_candidate
):
    exploit = M.contradict_reading_order_indices(apparatus_candidate)
    result = _result(exploit, apparatus_gt, "structural-contract")
    assert result.passed is False
    assert result.metrics["candidate_order_contradicts_indices"] > 0


def test_incomplete_reading_order_is_a_violation(apparatus_gt, apparatus_candidate):
    partial = copy.deepcopy(apparatus_candidate)
    partial["reading_order"] = partial["reading_order"][:-1]
    result = _result(partial, apparatus_gt, "structural-contract")
    assert result.passed is False
    assert result.metrics["candidate_order_omits_regions"] == 1


def test_partial_declared_order_does_not_suppress_the_index_signal(apparatus_candidate):
    # The unit-level property behind the exploit: an incomplete declared list is not
    # honoured, so the page's own reading_order_index is what orders it.
    page = M.truncate_reading_order(apparatus_candidate, keep=1)
    assert PageView(page).reading_order == ["note-1", "body-2", "body-1", "head-1"]


# ── FIX-D: contract completeness over the RAW page (filtered-view finding) ────


@pytest.mark.parametrize(
    "value,kind",
    [
        ("head-1", "candidate_reading_order_not_a_list"),
        ({"a": 1}, "candidate_reading_order_not_a_list"),
        (7, "candidate_reading_order_not_a_list"),
        (["head-1", 3, "body-1", "body-2", "note-1"], "candidate_non_string_order_entries"),
    ],
    ids=["string", "dict", "int", "non-string-entry"],
)
def test_mistyped_reading_order_is_a_violation(value, kind, apparatus_gt, apparatus_candidate):
    exploit = M.mistype_reading_order(apparatus_candidate, value)
    result = _result(exploit, apparatus_gt, "structural-contract")
    assert result.passed is False, result.detail
    assert result.metrics[kind] > 0


@pytest.mark.parametrize("entry", [None, "a-string", 42], ids=["null", "string", "int"])
def test_non_object_region_entry_is_a_violation(entry, apparatus_gt, apparatus_candidate):
    exploit = M.append_non_object_region(apparatus_candidate, entry)
    result = _result(exploit, apparatus_gt, "structural-contract")
    assert result.passed is False
    assert result.metrics["candidate_non_object_regions"] == 1


def test_region_without_id_is_a_violation(apparatus_gt, apparatus_candidate):
    exploit = M.append_region_without_id(apparatus_candidate)
    result = _result(exploit, apparatus_gt, "structural-contract")
    assert result.passed is False
    assert result.metrics["candidate_regions_without_id"] == 1
    # The passing detail claims unique ids; that claim must not be made over a page
    # containing a region that has none.
    assert "unique-id" not in result.detail


def test_nesting_past_the_depth_cap_is_a_violation_not_a_silent_truncation(
    apparatus_gt, apparatus_candidate
):
    deep_gt = M.nest_beyond_depth_cap(apparatus_gt, MAX_REGION_DEPTH + 8)
    card = _card(apparatus_candidate, deep_gt)
    assert card.exit_code() == 1, card.render()
    result = next(r for r in card.results if r.id == "structural-contract")
    assert result.metrics["gt_regions_below_depth_cap"] == 1
    assert card.crashed == []


def test_nesting_within_the_depth_cap_is_not_a_violation(apparatus_gt, apparatus_candidate):
    shallow_gt = M.nest_beyond_depth_cap(apparatus_gt, 3)
    result = _result(apparatus_candidate, shallow_gt, "structural-contract")
    assert result.metrics["gt_regions_below_depth_cap"] == 0


# ── FIX-B: misplacement symmetry and short-region realism ─────────────────────


@pytest.mark.parametrize("fixture", ["apparatus", "minimal"])
def test_smear_fails(fixture, apparatus_gt, apparatus_candidate, minimal_gt, minimal_candidate):
    pages = {
        "apparatus": (apparatus_gt, apparatus_candidate),
        "minimal": (minimal_gt, minimal_candidate),
    }
    gt, candidate = pages[fixture]
    smeared = M.smear_page_text(candidate, source=gt)
    card = _card(smeared, gt)
    assert card.exit_code() == 1, card.render()
    result = next(r for r in card.results if r.id == "text-fidelity")
    assert result.passed is False
    assert result.metrics["misplaced_regions"] >= 1
    # The point of the finding: retention alone cannot see this — every GT region is
    # perfectly contained in its counterpart. Only misplacement catches it.
    assert result.metrics["containment"] == 1.0
    assert result.metrics["gross_region_defects"] == 0


def test_single_character_ocr_error_in_a_short_heading_passes(
    apparatus_gt, apparatus_candidate
):
    # "Book I" -> "Book l": containment 0.0 at every n, character similarity ~0.83.
    noisy = M.single_char_error(apparatus_candidate, "head-1", "Book I", "Book l")
    card = _card(noisy, apparatus_gt)
    assert card.exit_code() == 0, card.render()
    result = next(r for r in card.results if r.id == "text-fidelity")
    assert result.metrics["gross_region_defects"] == 0
    assert result.metrics["minor_region_defects"] <= result.metrics[
        "minor_region_defects_allowed"
    ]


def test_blanked_short_heading_still_fails(apparatus_gt, apparatus_candidate):
    # The rescue must not rescue deletion: similarity to "" is 0.0.
    blanked = M.blank_region_text(apparatus_candidate, "head-1")
    result = _result(blanked, apparatus_gt, "text-fidelity")
    assert result.passed is False
    assert result.metrics["gross_region_defects"] == 1
    assert result.metrics["worst_region_retention"] == 0.0


def _hyphenation_page(n_regions: int, artifact: bool) -> dict:
    regions, order = [], []
    for i in range(n_regions):
        text = f"the {i} quick brown fox jumps over the lazy dog near the river bank today"
        if artifact and i == 7:
            text = text.replace("brown fox", "bro wn fox")  # a hyphenation artifact
        regions.append(
            {
                "id": f"r{i}",
                "label": "text_block",
                "bbox": {"x0": 0.1, "y0": i / n_regions, "x1": 0.9, "y1": (i + 0.9) / n_regions},
                "text": text,
                "reading_order_index": i,
            }
        )
        order.append(f"r{i}")
    return {"regions": regions, "reading_order": order}


def test_one_hyphenation_artifact_in_forty_regions_passes():
    gt = _hyphenation_page(40, artifact=False)
    card = _card(_hyphenation_page(40, artifact=True), gt)
    assert card.exit_code() == 0, card.render()
    result = next(r for r in card.results if r.id == "text-fidelity")
    assert result.metrics["gross_region_defects"] == 0


def test_worst_region_retention_is_the_true_minimum_not_the_worst_defect():
    # Review finding L2-6: it used to report a flattering 1.0 whenever no region
    # crossed the floor, hiding how close a passing page ran to it. Scored on a page
    # that passes every gate, so the metric is the only thing under test.
    gt = _hyphenation_page(40, artifact=False)
    result = _result(_hyphenation_page(40, artifact=True), gt, "text-fidelity")
    assert result.passed is True
    assert 0.0 < result.metrics["worst_region_retention"] < 1.0


def test_novel_text_is_not_gated_as_misplacement(apparatus_gt, apparatus_candidate):
    # SCOPE GUARD: hallucination stays an escalated, ungated experiments decision.
    # Appended novel text must lower precision and leave the misplacement gate at 0.
    mutated = copy.deepcopy(apparatus_candidate)
    for region in mutated["regions"]:
        if region["id"] == "body-2":
            region["text"] += " Furthermore the philosopher then flew to the distant moon."
    result = _result(mutated, apparatus_gt, "text-fidelity")
    assert result.passed is True
    assert result.metrics["misplaced_regions"] == 0
    assert result.metrics["precision"] < 1.0
    assert result.metrics["excess_ngrams"] > 0


# ── FIX-C: exact assignment at every size ─────────────────────────────────────


def _chain_pages(n: int) -> tuple[dict, dict]:
    """GT/candidate whose IoU graph is one connected chain of ``n`` region pairs.

    Each GT box overlaps its own counterpart best and its neighbour's acceptably, so
    greedy stranding is possible and the whole thing is a single component.
    """
    gt_regions, cand_regions = [], []
    for i in range(n):
        gt_regions.append(
            {
                "id": f"g{i:03d}",
                "label": "text_block",
                "bbox": {"x0": 0.1, "y0": i * 0.5, "x1": 0.9, "y1": i * 0.5 + 1.0},
                "text": f"region {i} carries its own distinct sentence of prose here",
                "reading_order_index": i,
            }
        )
        cand_regions.append(
            {
                "id": f"c{i:03d}",
                "label": "text_block",
                "bbox": {"x0": 0.1, "y0": i * 0.5 + 0.02, "x1": 0.9, "y1": i * 0.5 + 1.02},
                "text": f"region {i} carries its own distinct sentence of prose here",
                "reading_order_index": i,
            }
        )
    gt = {"regions": gt_regions, "reading_order": [r["id"] for r in gt_regions]}
    cand = {"regions": cand_regions, "reading_order": [r["id"] for r in cand_regions]}
    return gt, cand


def test_seventeen_node_component_matches_every_region():
    # The reproduced M6-NOT-CLOSED case: 17 nodes fell over the old 16-node cap and
    # were matched greedily, 16 of 17. There is no cap now.
    gt, cand = _chain_pages(17)
    mapping = align_regions(PageView(gt), PageView(cand))
    assert len(mapping) == 17
    assert all(v is not None for v in mapping.values()), mapping
    assert mapping == {f"g{i:03d}": f"c{i:03d}" for i in range(17)}


def test_large_asymmetric_component_does_not_crash_and_is_bounded():
    # Review finding L2-4: the recursion ran once per GT region while the cutoff
    # counted only candidates, so 1 candidate vs ~1000 GT regions raised
    # RecursionError inside every alignment-consuming checker.
    box = {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.9}
    gt = {
        "regions": [
            {"id": f"g{i:04d}", "label": "text_block", "bbox": box, "text": f"block {i} prose"}
            for i in range(1100)
        ]
    }
    cand = {"regions": [{"id": "c0", "label": "text_block", "bbox": box, "text": "block 0 prose"}]}
    started = time.perf_counter()
    mapping = align_regions(PageView(gt), PageView(cand))
    elapsed = time.perf_counter() - started
    assert sum(1 for v in mapping.values() if v is not None) == 1
    assert elapsed < 10.0, f"asymmetric alignment took {elapsed:.1f}s"


def test_two_hundred_region_component_is_exact_and_bounded():
    gt, cand = _chain_pages(200)
    started = time.perf_counter()
    mapping = align_regions(PageView(gt), PageView(cand))
    elapsed = time.perf_counter() - started
    assert mapping == {f"g{i:03d}": f"c{i:03d}" for i in range(200)}
    # The old recursive matcher took 55.7s on this shape.
    assert elapsed < 20.0, f"200-region alignment took {elapsed:.1f}s"


def test_alignment_memo_returns_equal_but_independent_mappings(
    apparatus_gt, apparatus_candidate
):
    gt_view, cand_view = PageView(apparatus_gt), PageView(apparatus_candidate)
    first = align_regions(gt_view, cand_view)
    first["head-1"] = "tampered"
    second = align_regions(gt_view, cand_view)
    assert second["head-1"] == "head-1"  # the cache handed out a copy, not its state


def test_alignment_memo_does_not_confuse_distinct_pages(apparatus_gt, apparatus_candidate):
    renamed = M.rename_region_ids(apparatus_candidate)
    baseline = align_regions(PageView(apparatus_gt), PageView(apparatus_candidate))
    other = align_regions(PageView(apparatus_gt), PageView(renamed))
    assert baseline == {rid: rid for rid in ["head-1", "body-1", "body-2", "note-1"]}
    assert set(other.values()) == {"m-0", "m-1", "m-2", "m-3"}


# ── FIX-F: the coverage gap the reviewers named ───────────────────────────────


def test_scorecard_is_invariant_to_region_order_with_no_declared_reading_order():
    # The permutation-invariance property (D-008) asserted on a page that declares no
    # reading_order at all, so array order is the only thing being permuted.
    regions = [
        {
            "id": "body-1",
            "label": "text_block",
            "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.4},
            "text": "I went down yesterday to the Piraeus with Glaucon the son of Ariston",
            "reading_order_index": 0,
        },
        {
            "id": "note-1",
            "label": "note_area",
            "semantic_labels": ["note"],
            "bbox": {"x0": 0.1, "y0": 0.6, "x1": 0.9, "y1": 0.9},
            "text": "The festival of Bendis a Thracian goddess identified with Artemis",
            "reading_order_index": 1,
        },
    ]
    gt = {"regions": regions}
    forward = _card({"regions": copy.deepcopy(regions)}, gt)
    backward = _card({"regions": list(reversed(copy.deepcopy(regions)))}, gt)
    assert forward.exit_code() == 0, forward.render()
    assert forward.to_dict() == backward.to_dict()


def test_drop_anchor_mutates_anchors_on_nested_children():
    gt = {
        "regions": [
            {
                "id": "body-1",
                "label": "text_block",
                "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.5},
                "text": "Socrates then addressed the jury with these measured words.",
                "reading_order_index": 0,
                "children": [
                    {
                        "id": "quote-1",
                        "label": "block_quote",
                        "bbox": {"x0": 0.15, "y0": 0.2, "x1": 0.85, "y1": 0.4},
                        "text": "the unexamined life is not worth living for a human being.¹",
                        "text_anchors": ["¹"],
                    }
                ],
            },
            {
                "id": "note-1",
                "label": "note_area",
                "semantic_labels": ["note"],
                "bbox": {"x0": 0.1, "y0": 0.8, "x1": 0.9, "y1": 0.95},
                "text": "¹ Apology 38a, in the Jowett translation.",
                "reading_order_index": 1,
            },
        ],
        "reading_order": ["body-1", "note-1"],
    }
    mutated = M.drop_anchor(gt)
    child = mutated["regions"][0]["children"][0]
    assert "¹" not in child["text"]  # the nested anchor was actually removed
    assert _verdicts(mutated, gt)["footnote-anchor"] is False
