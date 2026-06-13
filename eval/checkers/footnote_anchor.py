"""Footnote-anchor integrity checker.

Footnote anchoring — the in-text marker (``¹``, ``*``, ``a``) bound to the note it
refers to — is exactly the apparatus capability that public OCR benchmarks exclude
(PLAN §2.2) and that this suite exists to score. The scholar-schema contract models
it richly (DocumentGT ``Note.body_marker``/``marker_text``, ``Region.text_anchors``,
``PageDependency.unresolved_markers``); at the page level the observable signals are
a region's ``text_anchors`` (the in-text markers) and the note regions themselves.

This checker enforces two integrity properties, using whatever the GT page
actually expresses:

(a) **Note presence** — every GT note region (spatial ``note_area`` etc., or
    semantic ``note``) has a counterpart of the same kind in the candidate.
(b) **Anchor integrity** — every in-text anchor marker the GT declares on a body
    region appears *exactly once* in that region's candidate counterpart ("appears
    once, attached to the right block"). A dropped marker, a duplicated marker, or
    a marker that migrated to the wrong block all fail.

On a minimal page that declares notes but no in-text markers (the scriptorium
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

        # (b) Anchor integrity: each GT anchor marker appears exactly once in the
        # aligned candidate region (the "right block").
        anchors_total = 0
        anchors_ok = 0
        anchor_defects: list[str] = []
        for region in gt_view.regions:
            for marker in region.text_anchors:
                anchors_total += 1
                gt_count = region.text.count(marker)
                cand_id = mapping.get(region.id)
                cand_region = cand_view.region(cand_id) if cand_id else None
                if cand_region is None:
                    anchor_defects.append(f"{region.id}:'{marker}' block missing in candidate")
                    continue
                cand_count = cand_region.text.count(marker)
                # The GT itself defines the expected count (normally 1); the
                # candidate must match it exactly in the *same* block.
                expected = gt_count if gt_count > 0 else 1
                if cand_count == expected:
                    anchors_ok += 1
                elif cand_count == 0:
                    anchor_defects.append(f"{region.id}:'{marker}' dropped (0 in candidate)")
                elif cand_count > expected:
                    anchor_defects.append(
                        f"{region.id}:'{marker}' duplicated ({cand_count}x, expected {expected})"
                    )
                else:
                    anchor_defects.append(
                        f"{region.id}:'{marker}' count {cand_count}, expected {expected}"
                    )

        passed = not missing_notes and not mistyped_notes and not anchor_defects

        detail_parts = [
            f"notes {notes_matched}/{notes_total} recovered",
            f"anchors {anchors_ok}/{anchors_total} intact",
        ]
        if missing_notes:
            detail_parts.append(f"missing notes: {missing_notes}")
        if mistyped_notes:
            detail_parts.append(f"notes recovered but mistyped: {mistyped_notes}")
        if anchor_defects:
            detail_parts.append(f"anchor defects: {anchor_defects}")
        detail = "; ".join(detail_parts)

        return self._result(
            passed=passed,
            detail=detail,
            metrics={
                "gt_notes": notes_total,
                "notes_matched": notes_matched,
                "missing_notes": len(missing_notes),
                "mistyped_notes": len(mistyped_notes),
                "gt_anchors": anchors_total,
                "anchors_ok": anchors_ok,
                "anchor_defects": len(anchor_defects),
            },
        )
