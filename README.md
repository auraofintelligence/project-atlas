# Project Atlas

Project Atlas is a plain-language, magazine-style front door for the public Aura of Intelligence GitHub work. It is designed for people who want to explore projects without needing to understand GitHub.

It deliberately puts the **original substantive build date** beside every project. That is not GitHub's `Updated` date: a later licence, spelling correction or housekeeping change must not make an older project look newly built.

## Build history

- First substantive public build: 1 September 2026 (`8a65cb1`)
- Public site: <https://auraofintelligence.github.io/project-atlas/>

The Atlas records the first substantive build date for every included public project. It uses a separate current-release note where a meaningful rebuild has superseded an older public version, such as Global Group Marriages v2.

## What the first edition includes

- 143 audited public projects from the 29 August 2026 organisation audit, plus confirmed public additions from later refresh files
- Direct links to live public pages where the audit verified one, plus GitHub links for every project
- All evidence-backed public neighbouring projects, not a small hand-picked sample
- Search, year, public-page and relationship filters
- A recent-builds area that can later be editorially curated
- A print-friendly directory with a scannable QR code for every public project. The page does not depend on a third-party QR service.

## Update the data

The browser reads `data/projects.json`. Rebuild it after a fresh audit or after adding a new public project:

```powershell
python scripts/build_atlas_data.py `
  --audit-csv ..\strange-but-true-field-library\data\github-organisation-audit-2026-08-29.csv `
  --relations ..\strange-but-true-field-library\data\github-project-relations-2026-08-29.json `
  --delta ..\strange-but-true-field-library\data\github-organisation-delta-2026-09-01.json `
  --manual data\manual-projects.json `
  --output data\projects.json
```

`data/manual-projects.json` is intentionally small. It is the place to add genuinely new completed projects once their public page, original build date and relationship evidence are confirmed. It can also mark a project as `freshlyCompleted` so it appears in the feature area. A dated public refresh file is useful when several new pages launch together.

The generator rejects non-public repository links and invalid build dates. It does not copy local paths, unpublished source material or private notes into the public dataset.

## Check it

```powershell
python scripts/validate_atlas.py
```

For a local preview:

```powershell
python -m http.server 8000
```

Then open `http://localhost:8000`. The site is static and can later be published with GitHub Pages without a build service.

## Regenerate the QR codes

The printable directory uses local SVG QR codes. Each code targets the project's public page when one exists, otherwise its public GitHub repository. They are generated locally, so no visitor address or project URL is sent to a QR-code service.

```powershell
npm install
npm run build:qr
```

Run the normal check afterwards. It confirms that every included project has a matching QR SVG with the intended public target.
