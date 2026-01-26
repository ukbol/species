# UKBOL Gap Analysis Data Portal

Interactive web portal for exploring DNA barcode coverage gaps in UK biodiversity.

## Quick Start

### 1. Update Data (Monthly)

Copy your updated TSV files from the private repo to the `data` folder:

```powershell
# From PowerShell or Command Prompt
copy "C:\GitHub\mind-the-gap\final_result\*.tsv" "C:\GitHub\species\data\"
```

### 2. Build the Website

```powershell
cd C:\GitHub\species
python scripts\build.py
```

### 3. Deploy to GitHub Pages

```powershell
cd C:\GitHub\species
git add .
git commit -m "Update gap analysis data - $(Get-Date -Format 'yyyy-MM-dd')"
git push
```

That's it! The website will update automatically via GitHub Pages.

## Project Structure

```
species/
├── data/                    # Input TSV files (copy from mind-the-gap)
│   ├── *.tsv               # Gap analysis TSVs
│   └── zenodo_links.csv    # Optional: links to Zenodo datasets
├── docs/                    # Generated website (GitHub Pages serves from here)
│   ├── index.html          # Landing page
│   ├── *.html              # Gene report pages
│   └── *.json.gz           # Compressed data files
├── scripts/
│   └── build.py            # Build script
└── README.md
```

## Features

- **Interactive Filtering**: Filter by taxonomy, habitat, conservation status
- **Shareable URLs**: Filtered views can be shared via URL parameters
- **Dynamic Charts**: Pie and bar charts update with filters
- **CSV Download**: Download filtered or complete datasets
- **Mobile Responsive**: Works on tablets and phones
- **Fast Loading**: Data is gzipped and loaded asynchronously

## Adding Zenodo Links

Create `data/zenodo_links.csv` with columns:
- `title`: Display title
- `description`: Brief description
- `url`: Link to Zenodo
- `doi`: DOI identifier

Example:
```csv
title,description,url,doi
"UKBOL COI Raw Reads","Complete FASTQ files for COI sequencing","https://zenodo.org/record/12345","10.5281/zenodo.12345"
```


The site is available at: `https://ukbol.github.io/species/index.html`

## Requirements

- Python 3.8+
- pandas (`pip install pandas`)

## Technical Notes

- Data files are gzipped for efficient transfer
- Client-side decompression using the browser's native DecompressionStream API
- DataTables with deferred rendering for smooth scrolling through 74k+ rows
- URL state management for sharing filtered views
