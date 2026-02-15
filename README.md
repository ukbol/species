[![DOI](https://zenodo.org/badge/1142112416.svg)](https://doi.org/10.5281/zenodo.18378765)
# UKBOL Species Data Portal

Interactive web portal for exploring DNA barcode coverage gaps in UK biodiversity.

**Live site:** [https://ukbol.github.io/species/index.html](https://ukbol.github.io/species/index.html)

## Quick Start

### 1. Update Data (Monthly)

Copy your updated TSV files from the analysis repo to the `data` folder:

```powershell
# From PowerShell or Command Prompt
copy "C:\GitHub\mind-the-gap\final_result\*.tsv" "C:\GitHub\species\data\"
```

Or use the automated update script on Windows:

```powershell
update.bat
```

### 2. Build the Website

```bash
python scripts/build.py
```

The build script accepts optional arguments:

| Argument    | Default | Description                                   |
|-------------|---------|-----------------------------------------------|
| `--data`    | `data`  | Path to directory containing input TSV files  |
| `--output`  | `docs`  | Output directory for the generated website    |
| `--zenodo`  | `None`  | Path to a `zenodo_links.csv` file (optional)  |

### 3. Test Locally

```bash
cd docs
python -m http.server 8000
```

Then open [http://localhost:8000](http://localhost:8000) in a web browser.

### 4. Deploy to GitHub Pages

```powershell
git add .
git commit -m "Update gap analysis data - $(Get-Date -Format 'yyyy-MM-dd')"
git push
```

The website will update automatically via GitHub Pages.

## Project Structure

```
species/
├── README.md                # This file
├── LICENSE                  # MIT licence
├── update.bat               # Windows batch script for automated updates
├── data/                    # Input TSV files (copy from mind-the-gap)
│   ├── *_gap_analysis.tsv   # Gap analysis datasets (one per gene region)
│   └── zenodo_links.csv     # Optional: links to related Zenodo datasets
├── docs/                    # Generated website (GitHub Pages serves from here)
│   ├── index.html           # Landing page with cross-gene overview
│   ├── bold_coi.html        # COI barcode report
│   ├── midori_12s.html      # 12S rRNA report
│   ├── midori_16s.html      # 16S rRNA report
│   ├── ncbi_rbcl.html       # RBCL gene report
│   ├── unite_its.html       # ITS region report
│   ├── dtol_genome.html     # DToL genome report
│   └── data/                # Compressed data and downloadable TSVs
│       ├── *.json.gz        # Gzipped JSON for browser loading
│       └── *.tsv            # Raw TSV copies for download
├── metadata/
│   └── dataset_metadata.tsv # Reference database names, versions, and links
└── scripts/
    ├── README.md            # Detailed script documentation
    ├── build.py             # Main build script (TSV → interactive website)
    └── calc_stats.py        # Quick cross-gene coverage statistics
```

## Scripts

### `scripts/build.py`

Main build script that converts gap analysis TSV files into the interactive web portal. Reads data from `data/`, generates compressed JSON and HTML pages in `docs/`. See [`scripts/README.md`](scripts/README.md) for full details including arguments, functions, and status colour schemes.

### `scripts/calc_stats.py`

Standalone utility that calculates cross-gene coverage statistics from the raw TSV files. Reports the number of species in common across all datasets, species with at least one GREEN status, and true gaps (BLACK across all genes). See [`scripts/README.md`](scripts/README.md) for usage.

### `update.bat`

Windows batch script that automates the monthly update workflow:
1. Copies TSV files from `C:\GitHub\mind-the-gap\final_result\` to `data/`.
2. Runs `scripts/build.py` to regenerate the website.
3. Prompts whether to commit and push to GitHub.

## Features

- **Interactive Filtering**: Filter by taxonomy (cascading dropdowns), habitat, assemblage, and conservation status
- **Coverage Status**: Traffic-light system -- GREEN (valid), BLUE (synonym), AMBER (valid + synonym), RED (ID conflict), BLACK (missing)
- **Shareable URLs**: Filtered views can be shared via URL parameters
- **Dynamic Charts**: Pie chart (coverage overview) and bar chart (top 20 orders) update with filters
- **CSV/TSV Download**: Download filtered results as CSV or the complete dataset as TSV
- **Mobile Responsive**: Works on tablets and phones (Bootstrap 5)
- **Fast Loading**: Data is gzipped and decompressed client-side; DataTables with deferred rendering handles 74k+ rows

## Data Sources

| Gene   | Database | Version                            | Link                                |
|--------|----------|------------------------------------|-------------------------------------|
| COI    | BOLD     | 2026-01-09                         | [boldsystems.org](https://boldsystems.org/data/data-packages/) |
| 12S    | MIDORI2  | MIDORI2_TOTAL_NUC_GB269            | [reference-midori.info](https://www.reference-midori.info/) |
| 16S    | MIDORI2  | MIDORI2_TOTAL_NUC_GB269            | [reference-midori.info](https://www.reference-midori.info/) |
| RBCL   | NCBI     | 2026-01-23                         | [ncbi.nlm.nih.gov](https://www.ncbi.nlm.nih.gov/genbank/) |
| ITS    | UNITE    | sh_general_release_s_all_19.02.2025 | [doi.org/10.15156](https://doi.org/10.15156/BIO/3301232) |
| Genome | DToL     | 2026-02-14                         | [darwintreeoflife.org](https://www.darwintreeoflife.org/) |

## Adding Zenodo Links

Create `data/zenodo_links.csv` with columns:
- `title`: Display title
- `description`: Brief description
- `url`: Link to Zenodo
- `doi`: DOI identifier

These will appear as cards on the landing page.

## Requirements

- Python 3.8+
- pandas (`pip install pandas`)

## Technical Notes

- Data files are gzipped for efficient transfer (~5-6 MB per gene vs ~20 MB raw)
- Client-side decompression using pako (with DecompressionStream API fallback)
- DataTables with deferred rendering for smooth scrolling through 74k+ rows
- URL state management for sharing filtered views
- Plotly.js for interactive charts
- Bootstrap 5.3.3 for responsive layout

## Licence

MIT -- see [LICENSE](LICENSE).
