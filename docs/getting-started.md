# Getting Started

## Platform Scope

- Supported environment: Helix or Biowulf.
- `projark` workflows are Helix-focused and enforce host checks.

## Activate Environment

If `mamba` is already in your `PATH`, run:

```bash
mamba activate /vf/users/CCBR_Pipeliner/db/PipeDB/miniforge3/envs/parkit
```

If `mamba` is not already in your `PATH`, add the following block to your `~/.bashrc` or `~/.zshrc`:

```bash
# >>> mamba initialize >>>
# !! Contents within this block are managed by 'mamba shell init' !!
export MAMBA_EXE='/vf/users/CCBR_Pipeliner/db/PipeDB/miniforge3/bin/mamba';
export MAMBA_ROOT_PREFIX='/vf/users/CCBR_Pipeliner/db/PipeDB/miniforge3';
__mamba_setup="$("$MAMBA_EXE" shell hook --shell zsh --root-prefix "$MAMBA_ROOT_PREFIX" 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__mamba_setup"
else
    alias mamba="$MAMBA_EXE"  # Fallback on help from mamba activate
fi
unset __mamba_setup
# <<< mamba initialize <<<
```

Then run:

```bash
mamba activate /vf/users/CCBR_Pipeliner/db/PipeDB/miniforge3/envs/parkit
```

## Required Environment

- `HPC_DME_APIs` repository should be available locally. Follow this setup guide: https://ccbr.github.io/HowTos/docs/HPCDME/setup.html
- `HPC_DM_UTILS` must resolve to `<HPC_DME_APIs>/utils`.
- `HPC_DM_JAVA_VERSION` is auto-set on Helix/Biowulf if missing. Minimum required value is `23` (as of today).

## Sync Preflight

Before archival/retrieval runs:

```bash
parkit checkapisync
```

If out of sync:

```bash
parkit syncapi
```

`projark` runs this check automatically and blocks if not synced.

## Session Safety

Run all operations inside `tmux`, `screen`, or an Open OnDemand graphical session:

```bash
tmux new -s parkit
# or
screen -S parkit
```

`projark deposit` and `projark retrieve` enforce this check.
Disclaimer: Open OnDemand is currently available only on Biowulf compute nodes, not directly on Helix. Since `projark` is Helix-only today, use `tmux`/`screen` on Helix; Open OnDemand support is future-facing until Helix access is available.
