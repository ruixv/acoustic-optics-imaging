# Acoustic-Optics Imaging Paper Tracker

Static paper tracker for acoustic-optics imaging, acoustic coded imaging, acoustic imaging, acoustic holography, camera-sonar fusion, and photoacoustic/acousto-optic imaging.

- Last manually verified: **2026-06-25**
- Main page: `index.html`
- Scheduled update page: `updates.html`
- Verified metadata: `data/papers.json`
- Auto candidates: `data/candidates.json`
- Per-paper pages: `papers/*.html`
- Open PDF downloader: `scripts/download_pdfs.py`
- Scheduled updater: `.github/workflows/update-papers.yml`

## Curation rules

1. Prioritize top venues: Nature / Nature Portfolio journals, Science / Science Advances, ACM TOG / SIGGRAPH / SIGGRAPH Asia, IEEE TPAMI / TIP, CVPR / ICCV / ECCV, ICLR / NeurIPS.
2. Include only papers directly related to at least one of:
   - acoustic-optical / camera-sonar fusion;
   - acoustic imaging, sonar, synthetic aperture sonar, acoustic NLOS;
   - acoustic coded imaging / acoustic holography / phased-array sound-field computation;
   - photoacoustic / acousto-optic imaging where acoustic and optical physics are both essential.
3. Use only legal/open PDF sources: publisher open-access PDFs, arXiv, PMC, CVF, institutional repositories, or author pages.
4. Do not include paywall-bypass or unofficial scraped PDFs.

## Run locally

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Download open PDFs

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_pdfs.py
```

Downloaded files will be saved to `pdfs/`. Some publisher URLs may reject automated downloads; in that case use the DOI/publisher link manually.

## Scheduled update every 6 hours

The repository includes `.github/workflows/update-papers.yml`:

```yaml
schedule:
  - cron: "17 */6 * * *"
permissions:
  contents: write
```

Each scheduled run updates `data/candidates.json`, rebuilds `updates.html`, and commits changes if new candidates are found.

See `SCHEDULED_UPDATE.md` for the permission setup.

## Manual candidate promotion

The automated task prioritizes accuracy over blind insertion. New discoveries first appear in `updates.html` / `data/candidates.json`. After checking title, venue, DOI, PDF/source links, and topical relevance, copy the paper into `data/papers.json`, add `summary_cn`, `why_include_cn`, `sources`, and `last_verified`, then run:

```bash
python scripts/build_site.py
git add data/papers.json index.html papers/*.html
git commit -m "Promote verified paper"
git push
```

## GitHub Pages

After pushing to GitHub, enable Pages:

`Settings` → `Pages` → `Build and deployment` → `Deploy from a branch` → branch `main` → folder `/ (root)` → `Save`.

## Minimal GitHub permissions

For GitHub Actions scheduled updates inside this same repository, use the built-in `GITHUB_TOKEN` with `contents: write`.

For the first local push of workflow files, a fine-grained Personal Access Token should be limited to:

- Repository access: **Only selected repositories** → `ruixv/acoustic-optics-imaging`
- Repository permissions: **Contents: Read and write**
- Repository permissions: **Workflows: Read and write** only for pushing/editing `.github/workflows/*`
- Metadata: read-only is mandatory/default

Never commit or paste tokens into the repository.
