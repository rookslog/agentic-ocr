"""Synthetic extraction-contract tests; no corpus bytes or acquisition metadata."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest

from eval.gtb.extract import extract_epub_text, extract_pdf_text, split_pdf_pages


def test_epub_xml_namespaces_quotes_and_relative_percent_encoded_hrefs(tmp_path: Path) -> None:
    epub = tmp_path / "synthetic.epub"
    with zipfile.ZipFile(epub, "w") as zf:
        zf.writestr(
            "META-INF/container.xml",
            "<container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'>"
            "<rootfiles><rootfile full-path='OPS/package.opf'/></rootfiles></container>",
        )
        zf.writestr(
            "OPS/package.opf",
            "<package xmlns='http://www.idpf.org/2007/opf'>"
            "<manifest>"
            "<item id='a' href='../Text/first%20part.xhtml' media-type='application/xhtml+xml'/>"
            "<item id='b' href='../Text/second.xhtml' media-type='application/xhtml+xml'/>"
            "</manifest><spine><itemref idref='b'/><itemref idref='a'/></spine></package>",
        )
        zf.writestr("Text/first part.xhtml", "<html><body><p>first item</p></body></html>")
        zf.writestr("Text/second.xhtml", "<html><body><p>second item</p></body></html>")

    assert extract_epub_text(epub) == "second item\n\nfirst item"


def test_split_pdf_pages_keeps_interior_blank_and_drops_one_trailing_chunk() -> None:
    assert split_pdf_pages("first\f\fthird\f") == ["first", "", "third"]
    assert split_pdf_pages("first\f") == ["first"]


def test_extract_pdf_text_propagates_pdftotext_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.CalledProcessError(1, ["pdftotext"])

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        extract_pdf_text(tmp_path / "synthetic.pdf")
