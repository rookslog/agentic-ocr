"""Minimal job runner — WALKING SKELETON (PLAN.md §7.1).

This is the *one execution abstraction from day 0*: a job declares a target, and
the runner either runs it locally or rsyncs the job dir to a remote target over
SSH (Tailscale) and runs it there, then rsyncs artifacts back.

WALKING SKELETON — deliberately minimal. There is NO queue, NO orchestrator, NO
retry/scheduling. Do not add them until batch-experiment scale demonstrates the
need (PLAN §7.1). When that need is demonstrated, that is a T4 design review.

A "job" is a directory containing an executable `run.sh` (the entrypoint). The
runner does not know what the job does; it only places the job on a target and
invokes its entrypoint.

Usage:
    python -m runner.run --job experiments/E2/jobs/smoke --target dionysus
    python -m runner.run --job experiments/E2/jobs/smoke --target local-mac --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGETS_FILE = Path(__file__).resolve().parent / "targets.toml"


def load_targets() -> dict[str, dict[str, Any]]:
    """Load the target table from targets.toml."""
    with open(TARGETS_FILE, "rb") as f:
        data = tomllib.load(f)
    return data.get("targets", {})


def _run(cmd: list[str], *, dry_run: bool) -> int:
    """Print, then run a command (unless --dry-run). Returns its exit code."""
    print("  $", " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd).returncode


def run_local(job: Path, *, nice: int | None, dry_run: bool) -> int:
    """Run a job's entrypoint in place on this machine."""
    entry = job / "run.sh"
    if not entry.exists():
        sys.exit(f"job entrypoint not found: {entry}")
    cmd = ["bash", str(entry)]
    if nice is not None:
        cmd = ["nice", "-n", str(nice), *cmd]
    print(f"[local] running {job} in place")
    return _run(cmd, dry_run=dry_run)


def run_ssh(job: Path, target: dict[str, Any], name: str, *, dry_run: bool) -> int:
    """rsync the job dir to a remote target, run its entrypoint, rsync artifacts back."""
    host = target.get("host", "")
    user = target.get("user", "")
    if target.get("enabled", True) is False or not host:
        sys.exit(f"target '{name}' is not usable (enabled=false or empty host)")

    dest_base = target.get("remote_root", "~/agentic-ocr-jobs")
    # Jobs normally live under the repo (e.g. runner/jobs/, experiments/E?/jobs/);
    # preserve that relative path on the remote. Fall back to the basename for
    # jobs outside the repo tree.
    try:
        rel = job.relative_to(REPO_ROOT)
    except ValueError:
        rel = Path(job.name)
    remote = f"{user}@{host}" if user else host
    remote_job = f"{dest_base}/{rel}"

    # 1. push the job dir
    push = ["rsync", "-az", "--delete", f"{job}/", f"{remote}:{remote_job}/"]
    # 2. run the entrypoint remotely
    invoke = ["ssh", remote, f"cd {remote_job} && bash run.sh"]
    # 3. pull artifacts back (the job writes into ./artifacts/)
    pull = ["rsync", "-az", f"{remote}:{remote_job}/artifacts/", f"{job}/artifacts/"]

    print(f"[ssh] target={name} host={remote} job={rel}")
    for step in (push, invoke, pull):
        rc = _run(step, dry_run=dry_run)
        if rc != 0:
            return rc
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, help="path to a job directory (contains run.sh)")
    parser.add_argument("--target", required=True, help="target name from targets.toml")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, run nothing")
    args = parser.parse_args(argv)

    targets = load_targets()
    if args.target not in targets:
        sys.exit(f"unknown target '{args.target}'. known: {', '.join(sorted(targets))}")
    target = targets[args.target]
    job = Path(args.job).resolve()
    if not job.is_dir():
        sys.exit(f"job dir not found: {job}")

    kind = target.get("kind", "ssh")
    if kind == "local":
        return run_local(job, nice=target.get("nice"), dry_run=args.dry_run)
    return run_ssh(job, target, args.target, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
