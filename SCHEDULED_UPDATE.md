# Scheduled update task

This repository is configured for an automated paper-candidate update every 6 hours through GitHub Actions.

## What the scheduled task does

Workflow: `.github/workflows/update-papers.yml`

Cron:

```yaml
schedule:
  - cron: "17 */6 * * *"
```

This means the workflow runs at 00:17, 06:17, 12:17, and 18:17 UTC every day.

Each run:

1. queries public scholarly sources through `scripts/update_candidates.py`;
2. writes newly discovered, high-scoring candidates to `data/candidates.json`;
3. records the run status in `data/last_update.json`;
4. rebuilds `index.html`, `updates.html`, and per-paper HTML pages;
5. tries to download open PDFs already listed in verified `data/papers.json`;
6. commits and pushes changes back to the repository if anything changed.

## Accuracy policy

To avoid false positives, the workflow does **not** automatically add candidates to the verified library in `data/papers.json`.

- `data/papers.json`: manually verified, clean paper library.
- `data/candidates.json`: automatically discovered papers that still need verification.
- `updates.html`: browser-friendly view of the auto candidates.

When a candidate is genuinely relevant, copy it into `data/papers.json`, add a Chinese summary and verified links, then run:

```bash
python scripts/build_site.py
git add data/papers.json index.html papers/*.html
git commit -m "Promote verified paper"
git push
```

## GitHub permissions

For scheduled updates inside the same repository, no personal token is needed by default. The workflow uses GitHub's built-in `GITHUB_TOKEN` with:

```yaml
permissions:
  contents: write
```

Repository setting to check:

`Settings` → `Actions` → `General` → `Workflow permissions` → enable **Read and write permissions**.

## Optional Crossref email secret

Crossref recommends a polite user agent / mailto for API use. Add this optional repository secret:

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

- Name: `CROSSREF_MAILTO`
- Value: your email, e.g. `raygeng@hku.hk`

## First-time push permission

To push `.github/workflows/update-papers.yml` into the repository for the first time from your own computer, your GitHub login/token must have permission to write workflow files.

For a fine-grained Personal Access Token:

- Repository access: only `ruixv/acoustic-optics-imaging`
- Contents: Read and write
- Workflows: Read and write
- Metadata: Read-only/default

After the workflow file is in the default branch, future scheduled pushes can use the built-in `GITHUB_TOKEN`.
