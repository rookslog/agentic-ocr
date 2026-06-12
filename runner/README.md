# runner — execution abstraction (WALKING SKELETON)

> **Walking skeleton.** PLAN.md §7.1: *one execution abstraction from day 0 — jobs
> declare a target; the runner is plain SSH-over-Tailscale + rsync'd artifacts.*
> **No queue, no orchestrator, no scheduling** — those are added only when
> batch-experiment scale demonstrates the need (and that is a T4 design review,
> not a casual addition).

## What it is

- [`targets.toml`](targets.toml) — the three execution targets (PLAN §7.1):
  - **`local-mac`** — runs in-process on this Mac (niced for batch).
  - **`dionysus`** — SSH over Tailscale to host `dionysus` as user `logansrooks`;
    the standing remote batch workhorse (Pascal GPU; no vLLM/FP8).
  - **`rental`** — placeholder, `enabled = false`, unused until a GPU is rented.
- [`run.py`](run.py) — the runner. A *job* is a directory containing an executable
  `run.sh`; the runner places it on a target and invokes that entrypoint.

## Model

```
job dir (with run.sh)  +  --target <name>
        │
        ├── local   → run run.sh in place (optionally niced)
        └── ssh     → rsync job dir → remote, ssh "bash run.sh",
                      rsync remote ./artifacts/ → local
```

The runner is intentionally ignorant of what a job does. Jobs write outputs into
their own `./artifacts/` directory, which is rsynced back from remote targets.

## Usage

```bash
# Dry-run: print the exact ssh/rsync plan, execute nothing.
python -m runner.run --job experiments/E2/jobs/smoke --target dionysus --dry-run

# Run locally.
python -m runner.run --job experiments/E2/jobs/smoke --target local-mac
```

## Status / next step

The skeleton is wired but **not yet demonstrated end-to-end on dionysus** — doing
so (the same trivial job running on both Mac and dionysus through this abstraction)
is a Phase 0 gate item (PLAN §10, STATE.md). Job directories under `runner/jobs/`
are gitignored.
