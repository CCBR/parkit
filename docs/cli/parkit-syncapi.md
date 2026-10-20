# parkit syncapi

Moves local `HPC_DME_APIs` to its target ref and refreshes the HPC-DME token.

The target is the latest stable release: the highest-numbered
`releases/X.Y.Z` branch merged into `master` (HPC_DME_APIs no longer publishes
GitHub tags or releases), unless a tag or branch is pinned.

## Syntax

```bash
parkit syncapi [--repo /path/to/HPC_DME_APIs] [--ref TAG_OR_BRANCH]
```

- `--ref`: sync to a specific tag or branch (`X.Y.Z` is shorthand for `releases/X.Y.Z`). Defaults to `$HPC_DME_APIs_REF` when set.

## What It Does

1. Resolves the API repo path and the target ref.
2. Moves the repo to the target without merge commits:
   - branch: local branch of the same name tracking `origin` (fast-forwarded if it exists)
   - tag: detached `HEAD` at the tag commit
   - never downgrades automatically; an explicit `--ref` may downgrade (with a warning)
   - aborts on uncommitted changes to tracked files or local-only commits; untracked/ignored files such as `utils/hpcdme.properties` are kept
3. Verifies `HEAD` is at the target commit.
4. Sources API functions and runs `dm_generate_token` interactively.

Exit codes: `0` success, `1` sync or token failure, `2` configuration error.

## Typical Use

```bash
parkit checkapisync
parkit syncapi
parkit checkapisync
```

Pin a specific release:

```bash
parkit syncapi --ref 3.31.0
export HPC_DME_APIs_REF=3.31.0   # keep checkapisync/projark on the same ref
```
