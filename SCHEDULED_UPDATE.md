# Scheduled update task

This repository is configured for an automated paper update every 6 hours through GitHub Actions.

## What the scheduled task does

Workflow: `.github/workflows/update-papers.yml`

```yaml
schedule:
  - cron: '17 */6 * * *'
```

Each run:

1. queries public scholarly sources through `scripts/update_candidates.py`;
2. records newly discovered records in `data/candidates.json`;
3. runs `scripts/agent_audit.py` as an automatic curation agent;
4. resolves arXiv records to final journal/conference metadata when Crossref/DOI evidence confirms an accepted or published version;
5. promotes high-confidence records to `data/papers.json`;
6. keeps borderline records in `data/candidates.json` for transparency;
7. rebuilds the bilingual website through `scripts/build_site.py`;
8. tries to download open PDFs already listed in the verified library;
9. commits and pushes changes back to the repository if anything changed.

## Automatic audit policy

The workflow uses an automatic promotion step. The audit agent checks:

- venue/source priority;
- acoustic, sonar, ultrasound, photoacoustic, optoacoustic, or acousto-optic terms;
- imaging, reconstruction, tomography, holography, NLOS, synthetic aperture, or sensor-fusion terms;
- recency;
- DOI or reliable primary URL;
- final accepted/published version availability for arXiv records;
- duplicate status against existing verified records;
- negative filters for unrelated audio, astronomy, sports, or general signal-processing records.

High-confidence records are promoted automatically. Borderline records remain visible in `updates.html`.

## arXiv / final-version rule

arXiv is treated as a preprint source, not a final venue. If an arXiv paper has an accepted or published version, the tracker records the final journal or conference as `venue` and keeps the arXiv URL only as a preprint/open-PDF source when useful. If no accepted or published version can be verified, the record remains `arXiv preprint`.

## Public metadata policy

This is a public repository. Metadata must use neutral project language only. Do not include private research plans, private preferences, or notes tied to a specific user's unpublished project context.

The build and update scripts sanitize known private-context patterns before writing public metadata.

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
- Value: a contact email address
