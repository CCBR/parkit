# parkit syncapi

Syncs local `HPC_DME_APIs` and refreshes HPC-DME token.

## Syntax

```bash
parkit syncapi [--repo /path/to/HPC_DME_APIs]
```

## What It Does

1. Resolves API repo path.
2. Runs `git pull`.
3. Sources API functions.
4. Runs `dm_generate_token` interactively.

## Typical Use

```bash
parkit checkapisync
parkit syncapi
parkit checkapisync
```
