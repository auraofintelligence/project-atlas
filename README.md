# Project Atlas

Project Atlas is a plain-language, magazine-style front door for the public Aura of Intelligence GitHub work. It is designed for people who want to explore projects without needing to understand GitHub.

It deliberately puts the **original substantive build date** beside every project. That is not GitHub's `Updated` date: a later licence, spelling correction or housekeeping change must not make an older project look newly built.

## Build history

- First substantive public build: 1 September 2026 (`8a65cb1`)
- Public site: <https://auraofintelligence.github.io/project-atlas/>

The Atlas records the first substantive build date for every included public project. It uses a separate current-release note where a meaningful rebuild has superseded an older public version, such as Global Group Marriages v2.

## What the Atlas includes

- 179 active public projects in the Atlas: 140 audit-derived projects from the 29 August 2026 organisation audit, plus thirty-nine confirmed public additions from later refresh files. Three archived duplicate i-C Infinity album-package copies remain excluded from active navigation.
- Direct links to live public pages where the audit verified one, plus GitHub links for every project
- All evidence-backed public neighbouring projects, not a small hand-picked sample. Three archived duplicate i-C Infinity album-package copies are deliberately excluded from active public navigation.
- Search, original-build year, project-family, public-page and relationship filters
- Visitor-facing orders for repository creation date, newly completed or meaningfully rebuilt work, public pages, connection count and A to Z
- Fourteen curated major projects on the home page, led by Open Record, Aura Genesis Protocol and 82 Claytons
- One complete directory on the Projects page, ordered by GitHub repository creation date, newest first by default
- A generated raster PNG Atlas favicon, with browser and Apple-touch sizes checked as PNG files
- A print-friendly directory with a scannable QR code for every public project. The page does not depend on a third-party QR service.

## Update the data

The browser reads `data/projects.json`. Rebuild it after a fresh audit or after adding a new public project:

```powershell
python scripts/build_atlas_data.py `
  --audit-csv ..\strange-but-true-field-library\data\github-organisation-audit-2026-08-29.csv `
  --relations ..\strange-but-true-field-library\data\github-project-relations-2026-08-29.json `
  --delta ..\strange-but-true-field-library\data\github-organisation-delta-2026-09-01.json `
  --delta data\github-organisation-delta-2026-09-08.json `
  --delta data\github-organisation-delta-2026-09-10.json `
  --delta data\github-organisation-delta-2026-09-15.json `
  --delta data\github-organisation-delta-2026-09-16.json `
  --delta data\github-organisation-delta-2026-09-18.json `
  --delta data\github-organisation-delta-2026-09-22.json `
  --delta data\github-organisation-delta-2026-09-23.json `
  --delta data\github-organisation-delta-2026-09-24.json `
  --delta data\github-organisation-delta-2026-09-30.json `
  --delta data\github-organisation-delta-2026-10-09.json `
  --delta data\github-organisation-delta-2026-10-19.json `
  --delta data\github-organisation-delta-2026-10-29.json `
  --manual data\manual-projects.json `
  --output data\projects.json
```

`data/manual-projects.json` holds editorial additions and overrides once their public destination, original build date and relationship evidence are confirmed. `freshlyCompleted` remains available for the recent-work sort. Its `excludedProjectNames` list prevents confirmed archived duplicates from returning to cards, search, QR or related-project links, while leaving the source audit intact. A dated public refresh file is useful when several new pages launch together.

`featuredProjectNames` sets the major-project order on the home page. The build regenerates those home links from this list. The Projects page has a single directory, ordered by repository creation date, newest first by default. `data/repository-creation-dates.json` records GitHub's `created_at` timestamps, independently of substantive build history and later updates; refresh this file when adding repositories. Card creation dates use Brisbane local time. Open Record links directly to its public GitHub record; it does not have a separate GitHub Pages site. 7-Mile uses its published planning-workbench address.

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

## Licence

Original Project Atlas code, editorial text and Atlas-specific artwork are available under the [Strange But True Public Source Licence](LICENCE.md). The licence applies to this Atlas, not to projects listed or linked here. Project thumbnails, logos and other material reused from those projects retain their existing rights. Third-party dependencies retain their own licences.

The text comes from the [30 June 2026 Strange But True revision](https://github.com/auraofintelligence/strange-but-true/blob/b953391fc5596c2e66b3535c45ef6cf6175baa23/LICENCE.md) (`b953391fc5596c2e66b3535c45ef6cf6175baa23`, licence blob `e548f72132c17b3a7b89f6413d620384d1bcdf6c`). Only the three project identifiers in the description and attribution have been changed to `project-atlas`; the licence terms are unchanged.
