"""Footnote-anchor integrity checker (page-level, partial — see ESCALATION).

Footnote anchoring — the in-text marker (``¹``, ``*``, ``a``) bound to the note it
refers to — is exactly the apparatus capability that public OCR benchmarks exclude
(PLAN §2.2) and that this suite exists to score.

ESCALATION (review finding D-008, schema lens): the *canonical* marker↔note binding
in the scholar-schema contract lives at the **DocumentGT** level — ``Note.body_marker``
(a ``LocationRef``) and ``Note.marker_text`` — which a *page*-level checker does not
consume. ``Region.text_anchors`` is documented as "notable text spans within region",
**not** a dedicated footnote-marker channel. So full in-text-marker↔note integrity
needs DocumentGT (or a schema addition) and is **escalated** to the schema/experiments
track, not forked locally. This checker therefore enforces the two integrity
properties that *are* observable at the page level:

(a) **Note presence** — every GT note region (spatial ``note_area`` etc., or
    semantic ``note``) has a counterpart of the same kind in the candidate.
(b) **Notable-span preservation** — every notable span the GT declares in
    ``text_anchors`` *and that actually occurs in that GT region's own text* is
    preserved in the candidate's counterpart region with the **same occurrence
    count** ("appears in the right block, the right number of times"). For an
    apparatus page whose declared span is the footnote marker (``¹``), this is the
    anchor-integrity check; a dropped or duplicated marker fails. A span the GT
    declares but does not itself contain is skipped (not fabricated into a
    requirement — review finding D-008, Case A).

On a minimal page that declares notes but no notable spans (the scriptorium
``minimal_page`` fixture), (b) is vacuous and the checker reduces to note presence
— it scores what the GT expresses, never inventing a requirement the GT omits.
"""

from __future__ import annotations

from .align import align_regions
from .base import Checker, CheckResult, PageLike
from .pagegt import PageView


class FootnoteAnchorChecker(Checker):
    """Note regions are recovered and every declared anchor appears once, in place."""

    id = "footnote-anchor"

    def check(self, candidate: PageLike, gt: PageLike) -> CheckResult:
        gt_view = PageView(gt)
        cand_view = PageView(candidate)
        mapping = align_regions(gt_view, cand_view)

        # (a) Note presence: each GT note region maps to a candidate note region.
        gt_notes = gt_view.notes()
        notes_total = len(gt_notes)
        notes_matched = 0
        missing_notes: list[str] = []
        mistyped_notes: list[str] = []
        for note in gt_notes:
            cand_id = mapping.get(note.id)
            cand_region = cand_view.region(cand_id) if cand_id else None
            if cand_region is None:
                missing_notes.append(note.id)
            elif not cand_region.is_note:
                mistyped_notes.append(note.id)
            else:
                notes_matched += 1

        # (b) Notable-span preservation: each GT-declared span that actually occurs
        # in its GT region's own text must occur the same number of times in the
        # aligned candidate region (the "right block"). The GT's own occurrence
        # count is the expectation — never fabricated (review finding D-008, Case A:
        # a span the GT declares but does not itself contain is skipped, not forced
        # to an expected count of 1).
        anchors_total = 0
        anchors_ok = 0
        anchor_defects: list[str] = []
        skipped_spans: list[str] = []
        for region in gt_view.regions:
            for marker in region.text_anchors:
                gt_count = region.text.count(marker)
                if gt_count == 0:
                    # Declared span is not a literal substring of the GT region's
                    # own text → not a verifiable in-text span at the page level.
                    skipped_spans.append(f"{region.id}:'{marker}'")
                    continue
                anchors_total += 1
                cand_id = mapping.get(region.id)
                cand_region = cand_view.region(cand_id) if cand_id else None
                if cand_region is None:
                    anchor_defects.append(f"{region.id}:'{marker}' block missing in candidate")
                    continue
                cand_count = cand_region.text.count(marker)
                if cand_count == gt_count:
                    anchors_ok += 1
                elif cand_count < gt_count:
                    anchor_defects.append(
                        f"{region.id}:'{marker}' under-preserved "
                        f"({cand_count}x, expected {gt_count})"
                    )
                else:
                    anchor_defects.append(
                        f"{region.id}:'{marker}' duplicated ({cand_count}x, expected {gt_count})"
                    )

        passed = not missing_notes and not mistyped_notes and not anchor_defects

        detail_parts = [
            f"notes {notes_matched}/{notes_total} recovered",
            f"spans {anchors_ok}/{anchors_total} preserved",
        ]
        if missing_notes:
            detail_parts.append(f"missing notes: {missing_notes}")
        if mistyped_notes:
            detail_parts.append(f"notes recovered but mistyped: {mistyped_notes}")
        if anchor_defects:
            detail_parts.append(f"span defects: {anchor_defects}")
        if skipped_spans:
            detail_parts.append(f"spans not in GT text, skipped: {skipped_spans}")
        detail = "; ".join(detail_parts)

        return self._result(
            passed=passed,
            detail=detail,
            metrics={
                "gt_notes": notes_total,
                "notes_matched": notes_matched,
                "missing_notes": len(missing_notes),
                "mistyped_notes": len(mistyped_notes),
                "gt_spans": anchors_total,
                "spans_preserved": anchors_ok,
                "span_defects": len(anchor_defects),
                "spans_skipped": len(skipped_spans),
            },
        )
