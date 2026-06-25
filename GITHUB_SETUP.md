# GitHub setup / permission guide

## Recommended setup: GitHub Actions updates the repository itself

This package includes `.github/workflows/update-papers.yml`, which runs every 6 hours and pushes candidate updates back to the same repository.

For this mode, you usually do **not** need to create a personal token for the scheduled job. The job uses GitHub's built-in `GITHUB_TOKEN` plus this workflow-level permission:

```yaml
permissions:
  contents: write
```

Check this repository setting after pushing:

`Settings` → `Actions` → `General` → `Workflow permissions` → **Read and write permissions**.

Then test manually:

`Actions` → `Update paper candidates` → `Run workflow`.

## Initial push from your computer

```bash
git clone https://github.com/ruixv/acoustic-optics-imaging.git
cd acoustic-optics-imaging
cp -R /path/to/acoustic-optics-imaging_site/. .
git add .
git commit -m "Add scheduled acoustic-optics paper tracker"
git push origin main
```

If the repository is empty or private and you need HTTPS token auth, use a fine-grained Personal Access Token.

## Fine-grained Personal Access Token for first push

Create a fine-grained token in GitHub:

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token.
2. Resource owner: `ruixv`.
3. Repository access: **Only selected repositories** → choose `acoustic-optics-imaging`.
4. Permissions:
   - **Contents: Read and write** — push normal files.
   - **Workflows: Read and write** — required if pushing `.github/workflows/update-papers.yml`.
   - **Metadata: Read-only** — required/default.
5. Expiration: 30-90 days is safer than no expiration.
6. Do not paste the token into public places or commit it.

Use it through the GitHub CLI:

```bash
gh auth login
# choose GitHub.com → HTTPS → Paste token
```

or as a temporary env var for one push:

```bash
export GITHUB_TOKEN=github_pat_xxx   # do not commit this
git push https://x-access-token:${GITHUB_TOKEN}@github.com/ruixv/acoustic-optics-imaging.git main
unset GITHUB_TOKEN
```

## Optional secret: CROSSREF_MAILTO

For better Crossref API etiquette, add this optional secret:

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

- Name: `CROSSREF_MAILTO`
- Value: your email, e.g. `raygeng@hku.hk`

## GitHub Pages

To publish the HTML site:

`Settings` → `Pages` → `Build and deployment` → `Deploy from a branch` → `main` → `/ (root)` → Save.
