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
- On completion/failure, `projark deposit` and `projark retrieve` send email to `$USER@nih.gov`.
- Notification sender is `NCICCBR@mail.nih.gov`.
- `projark ls` and `parkit ls` do not send email and require no session/gate checks.

## HPC-DME Configuration

- **Proxy settings** (`hpc.server.proxy.url`, `hpc.server.proxy.port`) must be **commented out** in `$HPC_DM_UTILS/hpcdme.properties`. `projark deposit` checks this and aborts with an error if active proxy lines are found.
- After the preflight checks, `projark deposit` prints the active lines from `hpcdme.properties` so you can verify configuration before the transfer begins.

## Dot-File Exclusion

Hidden files (filenames starting with `.`) are automatically excluded from `dm_register_directory` during deposit. This prevents shell per-directory history files and other hidden files from being registered to HPC-DME.

## Temp File Isolation

`dm_*` CLI commands produce response files (e.g. `*.tmp`) that are now isolated inside a per-call temporary directory and automatically deleted after each command. No temp files accumulate in your working directory.

## DME Search Index Lag

The HPC-DME search index used by `projark ls` and `parkit ls` can lag up to **60 minutes** behind a recent deposit. If newly deposited files do not appear in `ls` output, wait and retry.
