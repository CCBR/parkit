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

## Keep Scratch Artifacts

```bash
projark deposit ... --no-cleanup
```

## Outcome

- Data staged in scratch
- Collection paths created/validated
- Directory transferred to HPC-DME
- Scratch cleaned by default
