# projark Deposit (Recommended)

Use this for standard CCBR project archival.

## Example

```bash
projark deposit \
  --folder /data/CCBR/projects/CCBR-12345 \
  --projectnumber CCBR-12345 \
  --datatype Analysis
```

## With Custom Tar Name and Split Threshold

```bash
projark deposit \
  --folder /data/CCBR/projects/CCBR-12345 \
  --projectnumber 12345 \
  --datatype analysis \
  --tarname new.tar \
  --split-size-gb 250
```

## Stage Outside `/scratch`

If the project is too large for `/scratch/$USER`, stage on a larger filesystem:

```bash
projark deposit \
  --folder /data/CCBR/projects/CCBR-12345 \
  --projectnumber 12345 \
  --datatype Analysis \
  --staging-dir /data/$USER/staging
```

Or set `export PROJARK_STAGING_DIR=/data/$USER/staging` before running `projark`. The staging folder must not be inside the folder being archived.

## Keep Staging Artifacts

```bash
projark deposit ... --no-cleanup
```

## Outcome

- Free space and staging folder checked before anything is created in HPC-DME
- Collection paths created/validated
- Data staged in `<staging base>/CCBR-<projectnumber>/<datatype>/`
- Datatype folder transferred to HPC-DME
- Staging folder cleaned by default
