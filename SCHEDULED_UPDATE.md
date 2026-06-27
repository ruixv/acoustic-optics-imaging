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
2. expands discovery through citation-graph search for papers that cite records already labeled as Core;
3. records newly discovered records in `data/candidates.json`;
4. runs `scripts/agent_audit.py` as an automatic curation agent;
5. resolves arXiv records to final journal/conference metadata when Crossref/DOI evidence confirms an accepted or published version;
6. promotes high-confidence records to `data/papers.json`;
7. keeps borderline records in `data/candidates.json` for transparency;
8. rebuilds the bilingual website through `scripts/build_site.py`;
9. tries to download open PDFs already listed in the verified library;
10. commits and pushes changes back to the repository if anything changed.

## Automatic audit policy

The workflow uses an automatic promotion step. The audit agent checks:

- venue/source priority;
- acoustic, sonar, ultrasound, photoacoustic, optoacoustic, or acousto-optic terms;
- imaging, reconstruction, tomography, holography, NLOS, synthetic aperture, or sensor-fusion terms;
- recency;
- DOI or reliable primary URL;
- final accepted/published version availability for arXiv records;
- citation-of-Core evidence when available;
- duplicate status against existing verified records;
- negative filters for unrelated audio, astronomy, sports, or general signal-processing records.

High-confidence records are promoted automatically. Borderline records remain visible in `updates.html`.

## Core-citation expansion rule

In addition to keyword-, venue-, Crossref-, and arXiv-based discovery, every update pass should search for newly published or newly indexed papers that cite records already labeled as Core.

Procedure:

1. maintain a seed set of Core papers with DOI, title, venue, and primary URL;
2. query a citation graph database, currently OpenAlex cited-by records, for recent works that cite each Core seed;
3. treat citation-of-Core as a strong relevance signal during candidate scoring;
4. verify metadata from DOI, publisher, OpenAlex, Crossref, arXiv, ACM, IEEE, Nature, Science, CVF, DBLP, or other primary sources when available;
5. record citation evidence on candidates using fields such as `cites_core`, `cited_core_paper`, `citation_source`, and `metadata_verified_from`;
6. keep candidates as watchlist entries unless the final venue and topical relevance meet the curated-library promotion criteria.

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
