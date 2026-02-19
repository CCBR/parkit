# Operational Guidance

## Session Requirement

Run all operations in resilient sessions:

```bash
tmux new -s parkit
# or
screen -S parkit
```

Open OnDemand graphical sessions are also accepted.
`projark` enforces this for both `deposit` and `retrieve`.
Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.

## Scratch Paths

Default staging/retrieval base:

`/scratch/$USER/CCBR-<projectnumber>/`

Datatype subfolders (`Analysis`/`Rawdata`) are managed automatically.

## Split Threshold

`projark deposit` supports configurable split threshold/chunk size:

```bash
projark deposit ... --split-size-gb 500
```

Default is `500` GB.

## Cleanup Policy

- Default: cleanup enabled after successful deposit.
- To retain artifacts: `--no-cleanup`.

## Logging and Notifications

- `projark` logs include ISO 8601 timestamps.
- On completion/failure, `projark` sends email to `$USER@nih.gov`.
- Notification sender is `NCICCBR@mail.nih.gov`.
