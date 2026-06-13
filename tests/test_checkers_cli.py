"""Milestone 4: the CLI exits 0 on a faithful candidate, non-zero on mutations."""

from __future__ import annotations

import json
from pathlib import Path

from eval.checkers.__main__ import main
from tests import _mutations as M

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_exit_zero_on_faithful_candidate(capsys):
    code = main(
        [
            "--gt",
            str(FIXTURES / "minimal_page.gt.json"),
            "--candidate",
            str(FIXTURES / "minimal_page.candidate.json"),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "text-fidelity" in out
    assert "exit 0" in out


def test_cli_exit_zero_on_apparatus(capsys):
    code = main(
        [
            "--gt",
            str(FIXTURES / "apparatus_page.gt.json"),
            "--candidate",
            str(FIXTURES / "apparatus_page.candidate.json"),
        ]
    )
    assert code == 0


def test_cli_exit_nonzero_on_mutation(tmp_path, capsys):
    gt = FIXTURES / "apparatus_page.gt.json"
    candidate = json.loads((FIXTURES / "apparatus_page.candidate.json").read_text())
    mutated = M.corrupt_chars(candidate, 0.05)
    mutated_path = tmp_path / "corrupted.json"
    mutated_path.write_text(json.dumps(mutated), encoding="utf-8")

    code = main(["--gt", str(gt), "--candidate", str(mutated_path)])
    assert code == 1


def test_cli_json_output(capsys):
    code = main(
        [
            "--gt",
            str(FIXTURES / "apparatus_page.gt.json"),
            "--candidate",
            str(FIXTURES / "apparatus_page.candidate.json"),
            "--json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_code"] == 0
    assert payload["summary"]["total"] == 4
    assert {r["id"] for r in payload["results"]} == {
        "text-fidelity",
        "reading-order",
        "footnote-anchor",
        "structure-typing",
    }
