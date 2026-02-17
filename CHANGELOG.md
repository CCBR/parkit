## v2.2.0

- Feature: Automatic object name resolution (fix #30)
 - Added logic to detect and resolve naming conflicts by appending _002, _003, etc. to object names during deposit.
 - Metadata .json and .filelist files are updated accordingly to reflect new names.

- Enhancement: Java version management (fix #31)
 - Introduced support for setting HPC_DM_JAVA_VERSION dynamically with a default fallback to 23.0.2 on Biowulf/Helix

- Fixed ccr partition issue (fix #32)

- Documentation: Improved code example readability in README
 - Removed shell prompts (`%>`) from all code examples to enable direct copy-paste
 - Separated bash commands from their output into distinct code blocks

## v2.1.3

- fix scontrol issue on HELIX

## v2.1.1

## Features/BugFixes

- fix loading `parkit_dev` conda env (#26)

## v2.1.0

## Features/BugFixes

- adding `collectiontype` to `createmetadata` command
- excluding `*.tar.filelist` from `--cleanup` as it may need be put alongside README
- create readme with `--makereadme` argument
- `projark` subcommand for easy CCBR project backup

## v2.0.1

## Features/BugFixes

- package renamed from `parkit_pkg` to `parkit`
- reorganized package by recreating `src` folder

## v2.0.0

### Features/BugFixes

- converted to python package (fix #4)

## v1.0.1

### Features/BugFixes

- `parkit_tarball2hpcdme` added to start with tarballs
- `update_collection_metadata.py` added to add more information from AMP dump

## v1.0

### Features/BugFixes

- `parkit` added... built using python
- `parkit_e2e` added ... uses `parkit` and "slurm"
