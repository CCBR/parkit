# Operational Guidance

## Session Requirement

Run all operations in resilient sessions:

```bash
tmux new -s parkit
# or
screen -S parkit
```

`projark` enforces this for both `deposit` and `retrieve`.

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
