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

`__pycache__/` is excluded via
`.gitignore` and never uploaded.


## Cutting a new release

Releases are automated by `.github/workflows/release.yml`. It runs on every push
to `master` that touches `VERSION`:

1. For most day-to-day edits, just commit and push (or hit **Sync** in VS Code)
   as normal — nothing gets released, since `VERSION` didn't change.
2. When you want to cut a new version: bump `VERSION` (semver:
   `MAJOR.MINOR.PATCH`) and add an entry at the top of `CHANGELOG.md` describing
   what changed, then commit and push both files together (in VS Code: stage
   both, commit, Sync):
   ```
   ## X.Y.Z — YYYY-MM-DD
   Summary of what changed.
   ```
3. That's it. The push triggers the workflow, which reads `VERSION`, tags the
   commit `vX.Y.Z`, creates a GitHub Release using the top `CHANGELOG.md` entry
   as the release notes, and GitHub auto-attaches the `.zip`. No web UI visit
   needed.

If you forget to bump `VERSION` on a given push, the workflow finds the tag
already exists and silently does nothing — safe to push freely without
worrying about accidentally re-releasing.

The workflow also builds the release `.zip` itself from a filtered copy of the repo
(see `.github/release-exclude.txt`) rather than using GitHub's automatic full-repo
zipball — so `README.md`, `CHANGELOG.md`, `LICENSE`, `VERSION`, `.gitignore`, and
`.github/` are left out. The zip only contains the actual skill payload
(`SKILL.md`, `references/`, `scripts/`, `example_inp_files/`), wrapped in a single
top-level `topas-inp-writer/` folder. To change what's excluded from future
releases, edit `.github/release-exclude.txt`.

## Access model

- **Repo is public**: anyone can read/clone/download releases.
- **Only the owner + explicitly invited collaborators can push.** Manage this at
  `Settings → Collaborators` on GitHub. Adding someone there is what "named
  collaborator" access means in practice — there's no extra tooling needed.
- Licensed under MIT (see `LICENSE`) — this affects reuse/redistribution rights,
  not who can push to the repo.

## Downloading a specific version programmatically

For the `topas-editor-extension` `TopasAisetup.ts` installer:

- **Latest release metadata** (version + download URL), no auth needed for a public repo:
  ```
  GET https://api.github.com/repos/johnsoevans/topas-inp-writer/releases/latest
  ```
  Relevant fields in the JSON response:
  - `tag_name` — e.g. `"v1.0.2"` → this is your version string.
  - `published_at` — e.g. `"2026-07-16T13:00:00Z"` → the release date.
  - `assets[].name` / `assets[].browser_download_url` — find the asset named
    `topas-inp-writer.zip` and use its `browser_download_url`. This is the
    filtered skill-only zip built by the release workflow (see above), *not*
    GitHub's auto-generated `zipball_url` (which would include the whole repo,
    README/CHANGELOG included).

- GitHub API rate limits unauthenticated requests to 60/hour per IP, which is
  plenty for an occasional manual "check for updates" click. No token needed
  for a public repo.

### Actual install behavior (implemented in topas-editor's `TopasAiSetup.ts`)

1. Fetch `releases/latest`, read `tag_name`, `published_at`, and the
   `topas-inp-writer.zip` asset's `browser_download_url`.
2. Download and extract that zip (it contains a single top-level
   `topas-inp-writer/` folder — strip that prefix so contents land directly in
   the target `.claude/skills/topas-inp-writer/` folder).
3. Write a `version.txt` file in the skill's top directory:
   ```
   v1.0.2
   Released: 2026-07-16
   Installed: 2026-07-16
   ```
   (`Released` comes from `published_at`, `Installed` is today's date at
   install time.)
