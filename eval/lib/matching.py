"""Match predicted elements to ground truth elements.

This module provides:
1. MatchConfig - Configuration for matching behavior
2. ElementMatch - A matched pair of elements with similarity info
3. match_elements() - Core matching algorithm
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from rapidfuzz import fuzz

from eval.lib.normalize import NormalizedElement


@dataclass
class MatchConfig:
    """Configuration for element matching."""

    # Minimum similarity score to consider a match
    threshold: float = 0.5

    # Weights for different matching criteria
    position_weight: float = 0.3
    text_weight: float = 0.5
    attributes_weight: float = 0.2

    # Position tolerance in characters
    position_tolerance: int = 50

    # Text matching strategy
    text_strategy: Literal["exact", "fuzzy", "token"] = "fuzzy"


@dataclass
class ElementMatch:
    """A matched pair of ground truth and predicted elements."""

    ground_truth: NormalizedElement | None
    predicted: NormalizedElement | None
    match_type: Literal["exact", "partial", "missed", "spurious"]
    similarity_score: float
    position_similarity: float = 0.0
    text_similarity: float = 0.0
    error_details: dict | None = None

    @property
    def is_match(self) -> bool:
        """Return True if this is a successful match (exact or partial)."""
        return self.match_type in ("exact", "partial")


def match_elements(
    ground_truth: list[NormalizedElement],
    predicted: list[NormalizedElement],
    element_type: str,
    config: MatchConfig | None = None,
) -> list[ElementMatch]:
    """Match predicted elements to ground truth for a specific element type.

    Uses a greedy matching algorithm that pairs elements based on similarity.
    Each ground truth element can match at most one predicted element.

    Args:
        ground_truth: List of normalized ground truth elements
        predicted: List of normalized predicted elements
        element_type: Type of element to match ("footnote", "citation", etc.)
        config: Matching configuration (uses defaults if None)

    Returns:
        List of ElementMatch objects, including:
        - Matched pairs (exact or partial)
        - Missed elements (ground truth with no match)
        - Spurious elements (predicted with no match)
    """
    if config is None:
        config = MatchConfig()

    # Filter by element type
    gt_elements = [e for e in ground_truth if e.element_type == element_type]
    pred_elements = [e for e in predicted if e.element_type == element_type]

    matches: list[ElementMatch] = []
    matched_pred_ids: set[str] = set()

    # For each ground truth element, find best matching prediction
    for gt in gt_elements:
        best_match: NormalizedElement | None = None
        best_score = 0.0
        best_position_sim = 0.0
        best_text_sim = 0.0

        for pred in pred_elements:
            if pred.element_id in matched_pred_ids:
                continue

            # Compute similarity
            position_sim, pages_match = _compute_position_similarity(gt, pred, config)

            # Skip if pages don't match at all
            if not pages_match:
                continue

            text_sim = _compute_text_similarity(gt.text, pred.text, config)
            attr_sim = _compute_attribute_similarity(gt, pred)

            total_score = (
                config.position_weight * position_sim
                + config.text_weight * text_sim
                + config.attributes_weight * attr_sim
            )

            if total_score > best_score and total_score >= config.threshold:
                best_score = total_score
                best_match = pred
                best_position_sim = position_sim
                best_text_sim = text_sim

        if best_match:
            matched_pred_ids.add(best_match.element_id)
            match_type: Literal["exact", "partial"] = "exact" if best_score >= 0.95 else "partial"
            error_details = None
            if match_type == "partial":
                error_details = _compute_error_details(gt, best_match, best_text_sim)

            matches.append(
                ElementMatch(
                    ground_truth=gt,
                    predicted=best_match,
                    match_type=match_type,
                    similarity_score=best_score,
                    position_similarity=best_position_sim,
                    text_similarity=best_text_sim,
                    error_details=error_details,
                )
            )
        else:
            # Missed element
            matches.append(
                ElementMatch(
                    ground_truth=gt,
                    predicted=None,
                    match_type="missed",
                    similarity_score=0.0,
                    error_details={"reason": "not_found"},
                )
            )

    # Add spurious predictions (not matched to any ground truth)
    for pred in pred_elements:
        if pred.element_id not in matched_pred_ids:
            matches.append(
                ElementMatch(
                    ground_truth=None,
                    predicted=pred,
                    match_type="spurious",
                    similarity_score=0.0,
                    error_details={"reason": "false_positive"},
                )
            )

    return matches


def _compute_position_similarity(
    gt: NormalizedElement,
    pred: NormalizedElement,
    config: MatchConfig,
) -> tuple[float, bool]:
    """Compute position-based similarity between elements.

    Returns:
        Tuple of (similarity_score, pages_match). If pages_match is False,
        the elements should not be matched regardless of other similarities.
    """
    # Must be on same page (or overlapping pages for multi-page)
    gt_pages = set(gt.pages)
    pred_pages = set(pred.pages)

    if not gt_pages.intersection(pred_pages):
        return 0.0, False  # Pages don't match - cannot be matched

    # If both have character offsets, compare positions
    if gt.char_offset is not None and pred.char_offset is not None:
        offset_diff = abs(gt.char_offset - pred.char_offset)
        position_sim = max(0.0, 1.0 - offset_diff / config.position_tolerance)
        return position_sim, True

    # If no position info, give neutral score if pages match
    return 0.5, True


def _compute_text_similarity(text1: str, text2: str, config: MatchConfig) -> float:
    """Compute text similarity between two strings."""
    # Normalize whitespace
    t1 = " ".join(text1.split())
    t2 = " ".join(text2.split())

    if not t1 or not t2:
        return 0.0 if t1 != t2 else 1.0

    if t1 == t2:
        return 1.0

    if config.text_strategy == "exact":
        return 1.0 if t1 == t2 else 0.0

    if config.text_strategy == "token":
        # Token-based matching
        return fuzz.token_sort_ratio(t1, t2) / 100.0

    # Default: fuzzy matching
    return fuzz.ratio(t1, t2) / 100.0


def _compute_attribute_similarity(gt: NormalizedElement, pred: NormalizedElement) -> float:
    """Compute similarity of element-specific attributes."""
    # If both have no attributes, they match perfectly on attributes
    if not gt.attributes and not pred.attributes:
        return 1.0

    # If one has attributes and the other doesn't, neutral score
    if not gt.attributes or not pred.attributes:
        return 0.5

    # Compare common attributes
    common_keys = set(gt.attributes.keys()) & set(pred.attributes.keys())
    if not common_keys:
        return 0.5

    matches = 0.0
    for key in common_keys:
        gt_val = gt.attributes.get(key)
        pred_val = pred.attributes.get(key)

        if gt_val == pred_val:
            matches += 1
        elif isinstance(gt_val, str) and isinstance(pred_val, str):
            # Fuzzy compare strings
            if fuzz.ratio(gt_val, pred_val) > 80:
                matches += 0.5

    return matches / len(common_keys)


def _compute_error_details(
    gt: NormalizedElement,
    pred: NormalizedElement,
    text_sim: float,
) -> dict | None:
    """Compute detailed error information for partial matches."""
    errors: dict = {}

    # Text differences
    if text_sim < 0.95:
        gt_text = " ".join(gt.text.split())
        pred_text = " ".join(pred.text.split())

        if len(gt_text) != len(pred_text):
            errors["text_length_diff"] = len(pred_text) - len(gt_text)

        # Find character-level differences
        if gt_text != pred_text:
            errors["text_mismatch"] = True
            # Find first difference position
            for i, (c1, c2) in enumerate(zip(gt_text, pred_text, strict=False)):
                if c1 != c2:
                    errors["first_diff_pos"] = i
                    errors["first_diff"] = f"expected '{c1}', got '{c2}'"
                    break

    # Position differences
    if gt.char_offset is not None and pred.char_offset is not None:
        if gt.char_offset != pred.char_offset:
            errors["position_diff"] = pred.char_offset - gt.char_offset

    # Attribute differences
    attr_diffs = {}
    for key in set(gt.attributes.keys()) | set(pred.attributes.keys()):
        gt_val = gt.attributes.get(key)
        pred_val = pred.attributes.get(key)
        if gt_val != pred_val:
            attr_diffs[key] = {"expected": gt_val, "got": pred_val}
    if attr_diffs:
        errors["attribute_diffs"] = attr_diffs

    return errors if errors else None
