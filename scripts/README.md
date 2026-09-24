# Scripts

Python scripts for building and analysing the UKBOL Gap Analysis Data Portal.

## Requirements

- Python 3.8+
- pandas (`pip install pandas`)

## build.py

Main build script that converts DNA barcode gap analysis TSV files into an interactive web portal.

### Usage

```bash
python scripts/build.py [--data DATA_DIR] [--output OUTPUT_DIR] [--zenodo ZENODO_CSV]
```

| Argument    | Default | Description                                   |
|-------------|---------|-----------------------------------------------|
| `--data`    | `data`  | Path to directory containing input TSV files  |
| `--output`  | `docs`  | Output directory for the generated website    |
| `--zenodo`  | `None`  | Path to a `zenodo_links.csv` file (optional)  |

### What it does

1. **Reads** all `*.tsv` files from the data directory (gap analysis exports from the `mind-the-gap` repository).
2. **Compresses** each dataset into gzipped JSON (`docs/data/<gene>.json.gz`) for efficient browser loading.
3. **Copies** the original TSV files to `docs/data/` so users can download the raw data.
4. **Generates individual HTML report pages** for each gene/dataset with:
   - Cascading taxonomy filters (kingdom, phylum, class, order, family).
   - Status toggle buttons with a "What do the statuses mean?" key.
   - Record issue filter buttons (gene datasets with an `issues` column).
   - Habitat, assemblage, and conservation designation filters.
   - UK records filter (when data is available).
   - Interactive pie chart (coverage overview) and bar chart (gap analysis by order).
   - Searchable, sortable data table using DataTables with deferred rendering.
   - CSV download for filtered results and TSV download for complete data.
   - Shareable URLs with filter state encoded as query parameters.
5. **Generates the landing page** (`docs/index.html`) with:
   - Cross-gene summary statistics (species assessed, species with data, true gaps).
   - Dataset cards linking to each gene report.
   - Database version metadata table (from `metadata/dataset_metadata.tsv`).
   - Optional Zenodo dataset links.
6. **Detects dataset type** (from `metadata/datasets.tsv`, or by column sniffing) and uses the matching status definitions in `STATUS_DEFS`: gene, DToL genome or ENA mitogenome.

### Status codes

`species_status` values are descriptive codes produced by `mind-the-gap`. Colours are applied only at display time (`STATUS_DEFS` in `build.py`).

**Gene datasets**

| Code | Label | Colour | Meaning |
|------|-------|--------|---------|
| `valid_name` | Valid name | Green | Records only under the valid name, no BIN/OTU sharing |
| `synonym_only` | Synonym only | Blue | Records only under synonym(s); valid name absent |
| `valid_and_synonym` | Valid + synonym | Amber | Records under both valid name and synonym(s) |
| `shared_bin_interim` | Shared BIN (interim) | Orange | BIN/OTU shared only with interim/placeholder names |
| `shared_bin_species` | Shared BIN (species) | Red | BIN/OTU shared with another formally named species |
| `no_records` | No records | Dark | No records under any name |

Gene datasets also carry an `issues` column (`;`-separated flags: `shared_bin_species`, `shared_bin_interim`, `synonym_records`, `valid_name_absent`, `split_bins`, `no_cluster`, `few_records`), shown in the table and available as a filter.

**DToL genome datasets**: `annotation_complete` (Annotated), `assembly_submitted` (Assembled), `raw_data_submitted` (Sequenced), `biosample_submitted` (Sampled), `not_in_dtol` (Not in DToL).

**ENA mitogenome datasets**: `mitogenome_present` (Has mitogenome), `no_mitogenome` (No mitogenome).

Older TSVs with colour values (GREEN, BLUE, AMBER, ORANGE, RED, BLACK) still build: `build.py` maps them to the codes above. To upgrade the files themselves, run `python <mind-the-gap>/gap_analysis/convert_legacy_status.py data/*.tsv`.

### Default taxonomy filters

Some gene regions automatically apply a default taxonomy filter when no URL parameters are present:

| Gene region | Default filter       |
|-------------|----------------------|
| COI         | Kingdom = Animalia   |
| RBCL        | Kingdom = Plantae    |
| ITS / UNITE | Kingdom = Fungi      |
| 12S         | Phylum = Chordata    |
| 16S         | No default filter    |

### Key functions

| Function                  | Description                                                        |
|---------------------------|--------------------------------------------------------------------|
| `get_gene_name()`         | Extracts a standardised display name from the TSV filename         |
| `compute_summary_stats()` | Calculates status counts and order-level breakdowns                |
| `prepare_data_json()`     | Converts a dataframe to gzipped JSON with all columns              |
| `get_filter_options()`    | Extracts unique values for each filter dropdown                    |
| `compute_cross_gene_stats()` | Computes species-level stats across all gene datasets           |
| `generate_index_html()`   | Builds the landing page with cross-gene overview                   |
| `generate_report_html()`  | Builds an individual gene report page with filters and charts      |

### Example

```bash
# Standard build (reads data/, writes to docs/)
python scripts/build.py

# Custom directories
python scripts/build.py --data /path/to/tsv_files --output /path/to/website

# With Zenodo links
python scripts/build.py --zenodo data/zenodo_links.csv
```

---

## calc_stats.py

Standalone utility script that calculates cross-gene coverage statistics from the raw TSV files. Useful for quick command-line checks without rebuilding the website.

### Usage

```bash
cd data
python ../scripts/calc_stats.py
```

**Note:** This script uses a hardcoded working directory (`C:\GitHub\species\data`) and is designed for local Windows use. Modify the `os.chdir()` path if running on a different machine.

### What it does

1. Loads all `*.tsv` files from the data directory.
2. Deduplicates species by `taxon_name` (keeps first occurrence per dataset).
3. Performs an inner merge across all datasets on `taxon_name`.
4. Reports:
   - **Species in common** across all datasets.
   - **Species with at least one `valid_name`** status (has barcode data in at least one gene region).
   - **True gaps** -- species with `no_records` status across every gene (no data anywhere).

### Example output

```
bold_coi: 74123 unique species
midori_12s: 72456 unique species
...

Species in common across all datasets: 70234
Species with at least one valid_name: 45678
Species with no_records across all genes (true gaps): 12345

=== VALUES FOR WEBSITE ===
Valid Species Assessed: 70234
Species with Data (at least one valid_name): 45678
True Gaps (no_records everywhere): 12345
```
