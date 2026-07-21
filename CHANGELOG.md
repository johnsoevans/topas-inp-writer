# Changelog

## 1.0.8 - 2026-07-21
- Changes to cif_to_str.py and symmetery_utils.py to fix a bug in trigonal/hexagonal space groups with x,2x type positions
- Fully updated documentation across the four relevant py scripts
- Also changed snap to special rules so that a 0.66667 y z type site remains general

## 1.0.7 - 2026-07-20
- Changes to skills.md
- Added 27-rietveld-workflow-conventions.md
- Changed my local directory to topas-inp-writer-master to avoid confusion

## 1.0.6 — 2026-07-19
- Added example_inp_files with z matrices, restrained organic molecules
- Added tio2 lab rietveld and pawley examples from tutorials
- Added a reference skill on bond distance and angle restraints and how to generate: restraints-and-penalties.md

## 1.0.5 — 2026-07-18
- Add references/space_group_symbols.html: browsable, searchable reference of
  every space group symbol TOPAS's space_group keyword accepts, click-to-copy.

## 1.0.4 — 2026-07-17
- Compressed skill.md significantly
- New example_inp_file readme
- New symmetrize_str.py for topas-editor use

## 1.0.3 — 2026-07-17
- Updates from Alan

## 1.0.2 — 2026-07-16
- Exclude README.md and CHANGELOG.md from the release zip — skill installs
no longer include repo-maintenance docs, only the actual skill payload.

## 1.0.1 — 2026-07-16
- Add automated release workflow (GitHub Actions tags + releases on VERSION bump).

## 1.0.0 — 2026-07-16
- Initial public release.
