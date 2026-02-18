# parkit checkapisync

Checks whether local `HPC_DME_APIs` is in sync with upstream.

## Syntax

```bash
parkit checkapisync [--repo /path/to/HPC_DME_APIs]
```

## Repo Resolution Order

1. `--repo`
2. `HPC_DME_APIs` env var
3. Parent of `HPC_DM_UTILS` if it ends with `utils`
4. Fallback `/data/kopardevn/SandBox/HPC_DME_APIs`

## Exit Meaning

- In sync: safe to proceed.
- Out of sync: run `parkit syncapi` before `projark` operations.

`projark` runs this check as Step 1 in both `deposit` and `retrieve`.
