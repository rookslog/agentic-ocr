"""Round-4 cross-vendor review regressions — the reviewers' probes, as tests.

The round-4 reviewers left executable probes; each reproduction below is one of them.
Round 5 was scoped to conformance, honesty and bugs: the per-region *tolerance
semantics* (MINOR_REGION_DEFECT_RATE, MAX_REGION_FOREIGN_RATIO's value, whether the
aggregate should be count-based at all) are FROZEN pending an operator design
decision, so probe P4 is pinned as an xfail rather than fixed — see
``test_p4_short_region_boundary_slip``.

Pre-fix behaviour, for the record:

    P3  nested flattering declared order        exit 0  ← exploit passed
    P6  in-place mutation, memoised alignment   stale mapping returned
    P8b float reading_order_index               contract clean
    P8c child declared before its parent        contract clean, invariant violated
    P2  "no declared order" invariance test     vacuous — the page had indices
    codex null reading_order                    contract clean
    codex smear + novel padding                 all five PASS, misplaced_regions 0
    MAJOR-4 fixture guard                       apparatus routed to the wrong branch
"""

from __future__ import annotations

import copy

import pytest

from eval.checkers import build_default_suite, run_checkers
from eval.checkers.align import align_regions, reset_cache
from eval.checkers.pagegt import PageView, declared_order_is_canonical
from eval.checkers.text_fidelity import TextFidelityChecker


def _card(candidate, gt):
    return run_checkers(candidate, gt, build_default_suite())


def _result(candidate, gt, checker_id):
    return next(r for r in _card(candidate, gt).results if r.id == checker_id)


# ── BLOCKER-1 / P3: the depth-uniform declared-order rule ─────────────────────

_BODY = "Socrates then addressed the assembled jury with these carefully measured words today"
_QUOTE = "the unexamined life is not worth living for any human being at all"
_NOTE = "Apology thirty eight a in the Jowett translation of the dialogues"


def _nested_page(nest_under: str, declared: list[str] | None = None) -> dict:
    quote = {
        "id": "quote-1",
        "label": "block_quote",
        "bbox": {"x0": 0.15, "y0": 0.20, "x1": 0.85, "y1": 0.40},
        "text": _QUOTE,
    }
    body = {
        "id": "body-1",
        "label": "text_block",
        "reading_order_index": 0,
        "bbox": {"x0": 0.10, "y0": 0.10, "x1": 0.90, "y1": 0.45},
        "text": _BODY,
        "children": [],
    }
    note = {
        "id": "note-1",
        "label": "note_area",
        "semantic_labels": ["note"],
        "reading_order_index": 1,
        "bbox": {"x0": 0.10, "y0": 0.80, "x1": 0.90, "y1": 0.95},
        "text": _NOTE,
        "children": [],
    }
    parent: dict = body if nest_under == "body" else note
    children: list[dict] = parent["children"]
    children.append(quote)
    page: dict = {"regions": [body, note]}
    if declared is not None:
        page["reading_order"] = declared
    return page


_NESTED_GT = _nested_page("body", ["body-1", "quote-1", "note-1"])


def test_p3_flattering_declared_order_cannot_hide_a_misnested_child():
    # The candidate nests the quotation under the note instead of the body — a real
    # structural error, which its own signals expose. It then declares the GT's order.
    # Top-level-only completeness accepted that list, so the misnesting vanished and
    # all five checkers passed.
    exploit = _nested_page("note", ["body-1", "quote-1", "note-1"])
    card = _card(exploit, _NESTED_GT)
    assert card.exit_code() == 1, card.render()
    verdicts = {r.id: r.passed for r in card.results}
    assert verdicts["structural-contract"] is False
    assert verdicts["reading-order"] is False
    # The declared list is refused, so the page is scored on its own index signal —
    # the same verdict the honest candidate (which declares no order) receives.
    assert PageView(exploit).reading_order == ["body-1", "note-1", "quote-1"]
    honest = _nested_page("note")
    assert PageView(honest).reading_order == ["body-1", "note-1", "quote-1"]
    assert _card(honest, _NESTED_GT).exit_code() == 1


def test_p8c_child_declared_before_its_parent_is_a_violation():
    # The documented invariant is "a region is immediately followed by its
    # descendants". Emission did not honour it for the declared path: declared
    # ["K","P","Q"] with K nested under P produced exactly that, child first.
    page = {
        "regions": [
            {
                "id": "P",
                "label": "text_block",
                "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.5},
                "text": "parent prose here",
                "children": [
                    {
                        "id": "K",
                        "label": "block_quote",
                        "bbox": {"x0": 0.2, "y0": 0.2, "x1": 0.8, "y1": 0.4},
                        "text": "child prose here",
                    }
                ],
            },
            {
                "id": "Q",
                "label": "note_area",
                "semantic_labels": ["note"],
                "bbox": {"x0": 0.1, "y0": 0.7, "x1": 0.9, "y1": 0.9},
                "text": "note prose here",
            },
        ],
        "reading_order": ["K", "P", "Q"],
    }
    result = _result(page, page, "structural-contract")
    assert result.passed is False
    assert result.metrics["candidate_order_breaks_block_structure"] > 0
    # And emission now satisfies the invariant it documents.
    assert PageView(page).reading_order == ["P", "K", "Q"]


def test_declared_order_canonicality_predicate():
    view = PageView(_NESTED_GT)
    top = view.top_level_regions
    assert declared_order_is_canonical(top, ["body-1", "quote-1", "note-1"]) is True
    assert declared_order_is_canonical(top, ["note-1", "body-1", "quote-1"]) is True
    assert declared_order_is_canonical(top, ["body-1", "note-1"]) is False  # incomplete
    assert declared_order_is_canonical(top, ["quote-1", "body-1", "note-1"]) is False  # split
    assert declared_order_is_canonical(top, ["body-1", "note-1", "quote-1"]) is False  # split


# ── codex HIGH: novel padding must not mask misplacement ─────────────────────


def _novel(region_index: int, n_tokens: int) -> str:
    return " ".join(f"zq{region_index}v{j}" for j in range(n_tokens))


def test_novel_padding_cannot_mask_a_smear(minimal_gt, minimal_candidate):
    # codex's construction: smear every block with the whole page, then pad each
    # region with 200 novel tokens. Novel grams used to sit in the misplacement
    # denominator only, so the ratio fell under the threshold and all five passed.
    whole = " ".join(r["text"] for r in minimal_gt["regions"])
    exploit = copy.deepcopy(minimal_candidate)
    for index, region in enumerate(exploit["regions"]):
        region["text"] = f"{whole} {_novel(index, 200)}"
    card = _card(exploit, minimal_gt)
    assert card.exit_code() == 1, card.render()
    result = next(r for r in card.results if r.id == "text-fidelity")
    assert result.metrics["misplaced_regions"] >= 1
    assert result.metrics["containment"] == 1.0  # the page metric is still blind


@pytest.mark.parametrize("padding", [0, 50, 200, 1000], ids=lambda n: f"pad{n}")
def test_misplacement_verdict_is_independent_of_novel_padding(
    padding, minimal_gt, minimal_candidate
):
    # The property behind the fix: novel text is *neutral* — it neither convicts nor
    # exculpates, so adding arbitrarily much of it cannot change this gate's verdict.
    whole = " ".join(r["text"] for r in minimal_gt["regions"])
    exploit = copy.deepcopy(minimal_candidate)
    for index, region in enumerate(exploit["regions"]):
        region["text"] = whole + (f" {_novel(index, padding)}" if padding else "")
    result = _result(exploit, minimal_gt, "text-fidelity")
    assert result.passed is False
    assert result.metrics["misplaced_regions"] == 1


def test_heavy_novel_text_without_misplacement_is_untouched_by_the_gate(
    apparatus_gt, apparatus_candidate
):
    # The other half of "neutral means neutral": hallucination alone stays ungated
    # (the D-008 escalation), so a region padded with novel text but holding no other
    # block's content must not trip misplacement.
    padded = copy.deepcopy(apparatus_candidate)
    for index, region in enumerate(padded["regions"]):
        region["text"] = region["text"] + " " + _novel(index, 300)
    result = _result(padded, apparatus_gt, "text-fidelity")
    assert result.metrics["misplaced_regions"] == 0
    assert result.passed is True
    assert result.metrics["precision"] < 0.1  # surfaced, not gated
    assert result.metrics["excess_ngrams"] > 0


# ── MAJOR-3 / P6: memo staleness under in-place mutation ─────────────────────


def test_p6_in_place_mutation_does_not_return_a_stale_alignment():
    box = lambda y: {"x0": 0.1, "y0": y, "x1": 0.9, "y1": y + 0.3}  # noqa: E731
    gt = {
        "regions": [
            {"id": "g-1", "label": "text_block", "bbox": box(0.1), "text": "alpha beta gamma"},
            {"id": "g-2", "label": "text_block", "bbox": box(0.5), "text": "delta epsilon zeta"},
        ]
    }
    cand = {
        "regions": [
            {"id": "c-1", "label": "text_block", "bbox": box(0.1), "text": "alpha beta gamma"},
            {"id": "c-2", "label": "text_block", "bbox": box(0.5), "text": "delta epsilon zeta"},
        ]
    }
    assert align_regions(PageView(gt), PageView(cand)) == {"g-1": "c-1", "g-2": "c-2"}

    # Swap the candidate boxes IN PLACE — same dict object, different geometry.
    regions = cand["regions"]
    regions[0]["bbox"], regions[1]["bbox"] = regions[1]["bbox"], regions[0]["bbox"]
    memoised = align_regions(PageView(gt), PageView(cand))

    reset_cache()
    truth = align_regions(PageView(gt), PageView(cand))
    assert memoised == truth == {"g-1": "c-2", "g-2": "c-1"}


def test_memo_ignores_fields_the_alignment_does_not_read(apparatus_gt, apparatus_candidate):
    # The precondition stated in align.py, asserted: the key is ids and bboxes, so
    # editing text/labels neither invalidates an entry nor changes the mapping.
    baseline = align_regions(PageView(apparatus_gt), PageView(apparatus_candidate))
    edited = copy.deepcopy(apparatus_candidate)
    for region in edited["regions"]:
        region["text"] = "entirely different prose"
        region["label"] = "note_area"
    assert align_regions(PageView(apparatus_gt), PageView(edited)) == baseline


def test_reset_cache_is_a_supported_no_op_for_correctness(apparatus_gt, apparatus_candidate):
    before = align_regions(PageView(apparatus_gt), PageView(apparatus_candidate))
    reset_cache()
    assert align_regions(PageView(apparatus_gt), PageView(apparatus_candidate)) == before


# ── MINOR-1 / P8b + codex null-order: mistyped order signals ─────────────────


def test_p8b_float_reading_order_index_is_a_violation(apparatus_gt, apparatus_candidate):
    mutated = copy.deepcopy(apparatus_candidate)
    for region in mutated["regions"]:
        region["reading_order_index"] = float(region["reading_order_index"])
    result = _result(mutated, apparatus_gt, "structural-contract")
    assert result.passed is False
    assert result.metrics["candidate_non_integer_reading_order_index"] == 4


@pytest.mark.parametrize("value", [1.0, "0", True, None], ids=["float", "str", "bool", "null"])
def test_non_integer_reading_order_index_kinds(value, apparatus_gt, apparatus_candidate):
    mutated = copy.deepcopy(apparatus_candidate)
    mutated["regions"][0]["reading_order_index"] = value
    result = _result(mutated, apparatus_gt, "structural-contract")
    assert result.passed is False
    assert result.metrics["candidate_non_integer_reading_order_index"] == 1


def test_null_reading_order_is_a_violation(apparatus_gt, apparatus_candidate):
    # Validation used to begin only when the value was not None, so a JSON null
    # reading_order passed the "a present order must be a list" rule it violates.
    mutated = copy.deepcopy(apparatus_candidate)
    mutated["reading_order"] = None
    card = _card(mutated, apparatus_gt)
    assert card.exit_code() == 1, card.render()
    result = next(r for r in card.results if r.id == "structural-contract")
    assert result.metrics["candidate_reading_order_not_a_list"] == 1


def test_absent_reading_order_key_is_not_a_violation(apparatus_gt, apparatus_candidate):
    # Absent and null are different: a page that simply does not declare an order is
    # well-formed and falls to its index signal.
    mutated = copy.deepcopy(apparatus_candidate)
    mutated.pop("reading_order")
    result = _result(mutated, apparatus_gt, "structural-contract")
    assert result.passed is True
    assert PageView(mutated).order_signal == "indices"


# ── MAJOR-2 / P2: the order-signal the page was actually scored on ───────────

_NO_SIGNAL_REGIONS = [
    {
        "id": "body-1",
        "label": "text_block",
        "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.4},
        "text": "I went down yesterday to the Piraeus with Glaucon the son of Ariston",
    },
    {
        "id": "note-1",
        "label": "note_area",
        "semantic_labels": ["note"],
        "bbox": {"x0": 0.1, "y0": 0.6, "x1": 0.9, "y1": 0.9},
        "text": "The festival of Bendis a Thracian goddess identified with Artemis",
    },
]


def test_p2_array_order_is_the_last_resort_signal_and_is_load_bearing():
    """With no declared order and no indices, permuting the array DOES change the score.

    The round-3 test claimed to assert invariance "with no declared reading_order"
    but its pages carried ``reading_order_index`` on every region, so it never
    exercised the array path and the claim was vacuous (round-4 MAJOR-2). The true
    behaviour, asserted here: array order is the last-resort order signal, so on a
    page that declares nothing else it is real order information and a permutation is
    NOT semantics-preserving. D-008's invariance property is conditional on an order
    signal existing — it says a *semantics-preserving* permutation must not flip a
    verdict, and this one is not that.
    """
    gt = {"regions": copy.deepcopy(_NO_SIGNAL_REGIONS)}
    assert PageView(gt).order_signal == "array"

    same = _card({"regions": copy.deepcopy(_NO_SIGNAL_REGIONS)}, gt)
    permuted = _card({"regions": list(reversed(copy.deepcopy(_NO_SIGNAL_REGIONS)))}, gt)

    assert same.exit_code() == 0, same.render()
    assert permuted.exit_code() == 1, "array order is load-bearing when nothing else exists"
    order = next(r for r in permuted.results if r.id == "reading-order")
    assert order.passed is False
    assert order.metrics["kendall_tau"] == -1.0
    assert order.metrics["order_signal"] == "array"


def test_invariance_holds_once_an_order_signal_exists():
    # The complement: give the same pages an explicit signal and the permutation
    # becomes semantics-preserving again, exactly as D-008 requires.
    with_index = copy.deepcopy(_NO_SIGNAL_REGIONS)
    for position, region in enumerate(with_index):
        region["reading_order_index"] = position
    gt = {"regions": copy.deepcopy(with_index)}
    forward = _card({"regions": copy.deepcopy(with_index)}, gt)
    backward = _card({"regions": list(reversed(copy.deepcopy(with_index)))}, gt)
    assert forward.exit_code() == 0, forward.render()
    assert forward.to_dict() == backward.to_dict()


@pytest.mark.parametrize(
    "page,expected",
    [
        ({"regions": _NO_SIGNAL_REGIONS}, "array"),
        (
            {
                "regions": [
                    dict(r, reading_order_index=i) for i, r in enumerate(_NO_SIGNAL_REGIONS)
                ]
            },
            "indices",
        ),
        (
            {"regions": _NO_SIGNAL_REGIONS, "reading_order": ["body-1", "note-1"]},
            "declared",
        ),
        # A non-canonical declared order is refused, so the page falls through.
        ({"regions": _NO_SIGNAL_REGIONS, "reading_order": ["body-1"]}, "array"),
    ],
    ids=["array", "indices", "declared", "declared-but-refused"],
)
def test_order_signal_metric_reports_the_signal_used(page, expected):
    assert PageView(page).order_signal == expected


def test_order_signal_is_surfaced_in_the_scorecard(apparatus_gt, apparatus_candidate):
    result = _result(apparatus_candidate, apparatus_gt, "reading-order")
    assert result.metrics["order_signal"] == "declared"
    assert result.metrics["gt_order_signal"] == "declared"


# ── MINOR-3: no flattering default when nothing was measured ─────────────────


def test_worst_region_retention_is_absent_when_no_region_was_scored():
    # "Nothing was measured" and "every region was perfect" are different facts;
    # reporting 1.0 for the first is the flattering-default mistake a third time.
    result = TextFidelityChecker().check({"regions": []}, {"regions": []})
    assert result.passed is True
    assert result.metrics["regions_scored"] == 0
    assert "worst_region_retention" not in result.metrics


def test_worst_region_retention_is_present_when_regions_were_scored(
    apparatus_gt, apparatus_candidate
):
    result = TextFidelityChecker().check(apparatus_candidate, apparatus_gt)
    assert result.metrics["worst_region_retention"] == 1.0


# ── MAJOR-1 / P4: FROZEN pending the operator semantics decision ─────────────


@pytest.mark.xfail(
    reason=(
        "pending operator semantics decision — the per-region tolerance/aggregate "
        "design is frozen (round 5). One segmentation slip that moves a following "
        "sentence into a short caption trips the misplacement gate, because a short "
        "region's own n-gram mass is small enough that any imported sentence exceeds "
        "MAX_REGION_FOREIGN_RATIO. Whether that is a true positive (the caption really "
        "does hold another block's text) or a false fail (one boundary slip on a "
        "60-region page) is exactly the frozen question. Pinned here so the case "
        "cannot be lost, and marked xfail so neither answer is enshrined."
    ),
    strict=True,
)
def test_p4_short_region_boundary_slip():
    def page(n: int = 60, drift: bool = False) -> dict:
        regions, order = [], []
        for i in range(n):
            if i == 7:
                text = "Figure three the divided line"
                if drift:
                    text += " for as socrates explains at once the soul ascends"
            elif i == 8:
                text = (
                    "for as socrates explains at once the soul ascends toward "
                    "the intelligible realm above"
                )
            else:
                text = f"the {i} quick brown fox jumps over the lazy dog near the river today"
            regions.append(
                {
                    "id": f"r{i}",
                    "label": "text_block",
                    "bbox": {"x0": 0.1, "y0": i / n, "x1": 0.9, "y1": (i + 0.9) / n},
                    "text": text,
                    "reading_order_index": i,
                }
            )
            order.append(f"r{i}")
        return {"regions": regions, "reading_order": order}

    assert _card(page(drift=True), page()).exit_code() == 0
