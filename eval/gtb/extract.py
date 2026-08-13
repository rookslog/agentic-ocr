"""Text extraction for GT-B pairs: born-digital EPUB and scan/text-layer PDF.

Generalized from ``.local/eval/og_smoke.py`` (the Of-Grammatology smoke). The
EPUB path is pure Python (``zipfile`` + OPF-spine order + XHTML tag-strip); the
PDF path shells out to poppler ``pdftotext`` (the candidate side the smoke read).
Both return plain text; tokenization/normalization is the aligner's job
(``eval.gtb.align`` reuses ``eval.checkers._normalize``), so this module is pure
extraction and carries no scoring logic.

Determinism: EPUB extraction walks the OPF spine in declared order; ``pdftotext``
is deterministic for a given binary + file. No randomness, no network.
"""

from __future__ import annotations

import html
import posixpath
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

# ── XHTML -> plain text (verbatim policy from og_smoke.strip_xhtml) ───────────────────────
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WS_RE = re.compile(r"[ \t ]+")
_MULTI_NL_RE = re.compile(r"\n{2,}")


def strip_xhtml(markup: str) -> str:
    """Reduce one XHTML document to plain text.

    Drops script/style, turns block-level ends into newlines, strips remaining
    tags, unescapes entities, and collapses whitespace. Block boundaries become
    newlines so paragraphs do not run together (which would forge spurious
    cross-paragraph n-grams).
    """
    markup = _SCRIPT_STYLE_RE.sub(" ", markup)
    markup = re.sub(r"(?i)<br\s*/?>", "\n", markup)
    markup = re.sub(
        r"(?i)</(p|div|h[1-6]|li|blockquote|tr|td|th|section|article|figcaption)>",
        "\n",
        markup,
    )
    text = _TAG_RE.sub("", markup)
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTI_NL_RE.sub("\n\n", text)
    return text.strip()


def opf_spine_hrefs(zf: zipfile.ZipFile) -> tuple[str, list[str]]:
    """Return ``(opf_dir, ordered content-document hrefs)`` following the OPF spine.

    Resolves ``container.xml`` -> ``.opf`` rootfile, maps manifest id->href, then
    walks the spine ``itemref`` ids in declared order, keeping only (x)html
    documents (the GT text spine, in reading order).
    """
    container = ET.fromstring(zf.read("META-INF/container.xml"))
    rootfile = container.find(".//{*}rootfile")
    if rootfile is None or not rootfile.get("full-path"):
        raise RuntimeError("container.xml has no rootfile full-path")
    opf_path = unquote(rootfile.get("full-path", ""))
    opf_dir = posixpath.dirname(opf_path)
    opf = ET.fromstring(zf.read(opf_path))

    manifest: dict[str, tuple[str, str]] = {}  # id -> (href, media_type)
    for item in opf.findall(".//{*}manifest/{*}item"):
        item_id = item.get("id")
        href = item.get("href")
        if item_id and href:
            manifest[item_id] = (href, item.get("media-type", ""))

    hrefs: list[str] = []
    for itemref in opf.findall(".//{*}spine/{*}itemref"):
        entry = manifest.get(itemref.get("idref", ""))
        if not entry:
            continue
        href, media = entry
        href = unquote(urlsplit(href).path)
        if media and "html" not in media.lower():
            continue
        if href.lower().endswith((".html", ".xhtml", ".htm")):
            hrefs.append(href)
    return opf_dir, hrefs


def extract_epub_text(path: Path) -> str:
    """Concatenated plain text of the EPUB spine, in reading order."""
    with zipfile.ZipFile(path) as zf:
        opf_dir, hrefs = opf_spine_hrefs(zf)
        names = set(zf.namelist())
        parts: list[str] = []
        for href in hrefs:
            href = href.split("#", 1)[0]
            full = posixpath.normpath(posixpath.join(opf_dir, href))
            if full not in names:
                continue
            markup = zf.read(full).decode("utf-8", "replace")
            txt = strip_xhtml(markup)
            if txt:
                parts.append(txt)
        return "\n\n".join(parts)


def extract_pdf_text(path: Path) -> str:
    """Plain text of ``path`` via poppler ``pdftotext`` (no OCR; reads the text layer).

    Raises ``CalledProcessError`` on a non-zero exit so a missing/broken binary
    surfaces loudly rather than as a silent empty candidate.
    """
    proc = subprocess.run(
        ["pdftotext", "-q", "-enc", "UTF-8", str(path), "-"],
        capture_output=True,
        check=True,
    )
    return proc.stdout.decode("utf-8", "replace")


PAGE_BREAK = "\f"
"""Form feed — the page separator ``pdftotext`` writes after *every* page."""


def split_pdf_pages(text: str) -> list[str]:
    """Split ``pdftotext`` output into one text per PDF page, in page order.

    ``pdftotext`` terminates every page (including the last) with a form feed, so
    a naive split leaves an empty chunk at the end; that one trailing
    content-free chunk is dropped. Interior blank pages are kept, so index *i* of
    the result is always PDF page *i+1*.

    Splitting here is safe for token identity: the form feed is not a letter or a
    decimal digit, so ``eval.checkers._normalize`` already treats it as a token
    separator. Splitting on it therefore can neither merge nor split a token, and
    the concatenation of the per-page token lists equals the whole-document token
    list (verified by :func:`eval.gtb.page_keys.page_token_ranges`).
    """
    parts = text.split(PAGE_BREAK)
    if parts and not parts[-1].strip():
        parts.pop()
    return parts


def extract_pdf_page_texts(path: Path) -> list[str]:
    """Per-PDF-page plain text via one ``pdftotext`` pass (index *i* = page *i+1*)."""
    return split_pdf_pages(extract_pdf_text(path))
