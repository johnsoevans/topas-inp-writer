# topas-inp-writer

Source repo for the `topas-inp-writer` Claude Code skill (see [SKILL.md](SKILL.md) for
what the skill does). This repo exists to back up the skill and to serve versioned
`.zip` downloads for installing it on other machines.

## Repo layout

- `SKILL.md` — the skill definition Claude Code reads (name/description + instructions).
- `references/` — TOPAS Technical Reference Manual, split by chapter.
- `scripts/` — helper Python scripts the skill shells out to.
- `example_inp_files/` — curated worked examples.
- `VERSION` — single line, current version number (semver). Bumped on every release.
- `CHANGELOG.md` — human-readable log of what changed per version.

`instructions.txt` (maintainer scratch notes) and `__pycache__/` are excluded via
`.gitignore` and never uploaded.

## Cutting a new release

1. Make your changes, commit and push to `master` as normal.
2. Bump `VERSION` (semver: `MAJOR.MINOR.PATCH`) and add an entry at the top of
   `CHANGELOG.md` describing what changed. Commit that:
   ```
   git add VERSION CHANGELOG.md
   git commit -m "Bump version to X.Y.Z"
   git push
   ```
3. Tag the commit and push the tag:
   ```
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```
4. Go to `https://github.com/johnsoevans/topas-inp-writer/releases/new`, pick the
   tag you just pushed, title it `vX.Y.Z`, paste the CHANGELOG entry as the
   description, and click **Publish release**.

That's it — no build step, no CI. The `.zip` GitHub generates from the tag *is* the
release artifact.

## Access model

- **Repo is public**: anyone can read/clone/download releases.
- **Only the owner + explicitly invited collaborators can push.** Manage this at
  `Settings → Collaborators` on GitHub. Adding someone there is what "named
  collaborator" access means in practice — there's no extra tooling needed.
- Licensed under MIT (see `LICENSE`) — this affects reuse/redistribution rights,
  not who can push to the repo.

## Downloading a specific version programmatically

For the `topas-editor-extension` `.ts` installer:

- **Latest release metadata** (version + download URL), no auth needed for a public repo:
  ```
  GET https://api.github.com/repos/johnsoevans/topas-inp-writer/releases/latest
  ```
  Relevant fields in the JSON response:
  - `tag_name` — e.g. `"v1.0.0"` → this is your version string.
  - `zipball_url` — e.g.
    `"https://api.github.com/repos/johnsoevans/topas-inp-writer/zipball/v1.0.0"`
    — redirects to a downloadable zip of the repo at that tag.

- **A specific version's zip directly** (no API call needed if you already know the tag):
  ```
  https://github.com/johnsoevans/topas-inp-writer/archive/refs/tags/vX.Y.Z.zip
  ```

- GitHub API rate limits unauthenticated requests to 60/hour per IP, which is
  plenty for an occasional manual "check for updates" click. No token needed
  for a public repo.

### Suggested install behavior

When the `.ts` command downloads and installs into `.claude/skills/`:

1. Extract the zip (it will contain a single top-level folder like
   `topas-inp-writer-1.0.0/` — strip that prefix so contents land directly in
   the target `topas-inp-writer/` skill folder).
2. After extraction, write a `version.txt` file in the skill's top directory containing
   the version and the download date, e.g.:
   ```
   1.0.0
   Installed: 2026-07-16
   ```
   (Read the version from the release's `tag_name`, not from the bundled `VERSION`
   file, since they're guaranteed to match but `tag_name` is what the API hands you
   directly.)
3. `version.txt` should itself be listed in `.gitignore` if `.claude/skills/` is ever
   put under its own git tracking on the target machine, since it's install-local
   metadata, not source.
