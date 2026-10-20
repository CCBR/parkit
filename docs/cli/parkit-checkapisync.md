# parkit checkapisync

Checks whether local `HPC_DME_APIs` is at its target ref: the latest stable
release, i.e. the highest-numbered `releases/X.Y.Z` branch merged into `master`
(HPC_DME_APIs no longer publishes GitHub tags or releases).

## Syntax

```bash
parkit checkapisync [--repo /path/to/HPC_DME_APIs] [--ref TAG_OR_BRANCH]
```

- `--ref`: compare against a specific tag or branch instead (`X.Y.Z` is shorthand for `releases/X.Y.Z`). Defaults to `$HPC_DME_APIs_REF` when set.

## Repo Resolution Order

1. `--repo`
2. `HPC_DME_APIs` env var
3. Parent of `HPC_DM_UTILS` if it ends with `utils`

## Exit Meaning

- `0` in sync: `HEAD` is at the target commit (or has identical content), or, when no ref is pinned, the local release is newer than the latest stable release. Safe to proceed.
- `1` out of sync: run `parkit syncapi` before `projark` operations.
- `2` configuration error: repo not found or unknown `--ref`.

The check only fetches; it never changes your checkout.

`projark` runs this check as Step 1 in both `deposit` and `retrieve`, honoring `HPC_DME_APIs_REF`.
