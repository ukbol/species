#!/usr/bin/env python3
"""
UKBOL Gap Analysis Website Builder (Optimized)
==============================================
Converts TSV files into an interactive data portal with lazy data loading.

Usage:
    python build.py
    
Workflow:
    1. Copy TSV files to ./data/
    2. Run: python scripts/build.py
    3. Commit and push to GitHub
"""

import pandas as pd
import json
import os
import sys
import gzip
import shutil
from pathlib import Path
from datetime import datetime
import argparse
import re

STATUS_COLORS = {
    'GREEN': '#198754', 'AMBER': '#ffc107', 'RED': '#dc3545',
    'BLUE': '#0d6efd', 'BLACK': '#343a40',
}

# Shortened status labels for display (gene datasets)
STATUS_LABELS = {
    'GREEN': 'OK - Valid',
    'BLUE': 'OK - Synonym',
    'AMBER': 'OK - Valid + Synonym',
    'RED': 'ID Conflict',
    'BLACK': 'Missing',
}

# Status labels for DToL genome datasets
DTOL_STATUS_LABELS = {
    'GREEN': 'Completed',
    'BLUE': 'Assembled',
    'AMBER': 'Sequenced',
    'RED': 'Sampled',
    'BLACK': 'Missing',
}

# Status labels for ENA mitogenome datasets
MITOGENOME_STATUS_LABELS = {
    'GREEN': 'Has Mitogenome',
    'BLACK': 'Missing',
}

# Default taxonomy filters for specific gene regions
GENE_DEFAULT_FILTERS = {
    'coi': {'kingdom': 'Animalia'},
    'rbcl': {'kingdom': 'Plantae'},
    'its': {'kingdom': 'Fungi'},
    'unite': {'kingdom': 'Fungi'},
    '12s': {'phylum': 'Chordata'},
    'mitogenome': {},  # No default filter - spans all kingdoms
}

JNCC_PREFIXES = ['jncc_', 'pantheon_']

# Columns to display in the browser table (in order)
# Columns not present in the dataframe will be skipped automatically
DISPLAY_COLUMNS = [
    ('taxon_name', 'Species'),
    ('synonyms', 'Synonyms'),
    ('other_names', 'Other names'),
    ('order', 'Order'),
    ('family', 'Family'),
    ('species_status', 'Status'),
    ('bags_grade', 'Grade'),
    ('number_records', 'Records'),
    ('gb_records', 'UK Records'),
    ('mitogenome_count', 'Mitogenomes'),
    ('data_link', 'Data Link'),
]

# Columns that should be truncated with hover tooltip (long text fields)
TRUNCATE_COLUMNS = ['synonyms', 'other_names']


def get_gene_name(filepath):
    name = Path(filepath).stem
    name = re.sub(r'^\d{4}-\d{2}-\d{2}_', '', name)
    name = re.sub(r'_gap_analysis$', '', name)
    parts = name.split('_')
    if len(parts) >= 2:
        database = parts[0].upper()
        gene = '_'.join(parts[1:]).upper()
        return f"{gene} ({database})"
    return name.upper()


def get_jncc_columns(df):
    jncc_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if any(col_lower.startswith(prefix) for prefix in JNCC_PREFIXES):
            if df[col].notna().any() and (df[col] != '').any():
                jncc_cols.append(col)
    return jncc_cols


def compute_summary_stats(df):
    status_col = 'species_status'
    stats = {'total_species': len(df), 'status_counts': {}, 'by_order': {}, 'with_protection': 0}
    
    if status_col in df.columns:
        status_counts = df[status_col].value_counts().to_dict()
        stats['status_counts'] = {k: int(v) for k, v in status_counts.items()}
    
    if 'order' in df.columns and status_col in df.columns:
        order_status = df.groupby(['order', status_col]).size().unstack(fill_value=0)
        stats['by_order'] = order_status.to_dict('index')
    
    jncc_cols = get_jncc_columns(df)
    if jncc_cols:
        has_protection = df[jncc_cols].notna().any(axis=1) & (df[jncc_cols] != '').any(axis=1)
        stats['with_protection'] = int(has_protection.sum())
    
    return stats


def clean_column_name(col):
    col = re.sub(r'^jncc_[a-z]+:\s*', '', col, flags=re.IGNORECASE)
    return col.replace('_', ' ').title()


def prepare_data_json(df, jncc_columns, output_path):
    # Include ALL columns from input (for filtering and downloads)
    # Order: display columns first, then remaining columns in original input order
    display_col_names = [col for col, _ in DISPLAY_COLUMNS]
    
    selected_cols = []
    # Add display columns first (in order)
    for col in display_col_names:
        if col in df.columns:
            selected_cols.append(col)
    # Add all remaining columns in original input order
    for col in df.columns:
        if col not in selected_cols:
            selected_cols.append(col)
    
    table_df = df[selected_cols].copy()
    records = table_df.to_dict('records')
    
    with gzip.open(output_path, 'wt', encoding='utf-8') as f:
        json.dump(records, f)
    return len(records)


def get_filter_options(df):
    filter_options = {}
    for col in ['kingdom', 'phylum_division', 'class', 'order', 'family', 'species_status']:
        if col in df.columns:
            values = sorted(df[col].dropna().unique().tolist())
            values = [v for v in values if v != '']
            filter_options[col] = values
    # Extract unique PANTHEON assemblage type codes (comma-separated in data)
    if 'pantheon_specific_assemblage_type' in df.columns:
        all_codes = set()
        for val in df['pantheon_specific_assemblage_type'].dropna():
            if val:
                for code in str(val).split(','):
                    code = code.strip()
                    if code:
                        all_codes.add(code)
        filter_options['pantheon_assemblage'] = sorted(all_codes)
    return filter_options


def compute_cross_gene_stats(dataframes):
    """
    Compute summary statistics across all gene datasets.
    
    Returns dict with:
    - valid_species: count of unique species across all datasets
    - species_with_data: count of species with GREEN status in at least one gene
    - true_gaps: count of species with BLACK status across ALL genes
    """
    if not dataframes:
        return {'valid_species': 0, 'species_with_data': 0, 'true_gaps': 0}
    
    # Filter to only dataframes that have the required columns
    valid_dfs = [df for df in dataframes if 'taxon_name' in df.columns and 'species_status' in df.columns]
    
    if not valid_dfs:
        return {'valid_species': 0, 'species_with_data': 0, 'true_gaps': 0}
    
    # Start with first dataset as base (deduplicated)
    base_df = valid_dfs[0][['taxon_name']].drop_duplicates()
    
    # Merge status from each dataset
    for i, df in enumerate(valid_dfs):
        df_dedup = df[['taxon_name', 'species_status']].drop_duplicates(subset='taxon_name', keep='first')
        df_dedup = df_dedup.rename(columns={'species_status': f'status_{i}'})
        base_df = base_df.merge(df_dedup, on='taxon_name', how='inner')
    
    status_cols = [c for c in base_df.columns if c.startswith('status_')]
    
    # Species with at least one GREEN across all genes
    has_green = (base_df[status_cols] == 'GREEN').any(axis=1)
    species_with_data = int(has_green.sum())
    
    # Species with BLACK across ALL genes (no data anywhere)
    all_black = (base_df[status_cols] == 'BLACK').all(axis=1)
    true_gaps = int(all_black.sum())
    
    return {
        'valid_species': len(base_df),
        'species_with_data': species_with_data,
        'true_gaps': true_gaps
    }



def generate_index_html(genes_data, zenodo_links, output_dir, build_date, cross_gene_stats=None, dataset_metadata=None):
    # Use cross-gene stats if provided, otherwise fall back to simple calculation
    if cross_gene_stats:
        valid_species = cross_gene_stats['valid_species']
        species_with_data = cross_gene_stats['species_with_data']
        true_gaps = cross_gene_stats['true_gaps']
    else:
        valid_species = genes_data[0]['stats']['total_species'] if genes_data else 0
        species_with_data = sum(g['stats']['status_counts'].get('GREEN', 0) for g in genes_data)
        true_gaps = sum(g['stats']['status_counts'].get('BLACK', 0) for g in genes_data)

    html_parts = []
    html_parts.append(f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UKBOL Gap Analysis Data Portal</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
:root{{--ukbol-green:#198754;--ukbol-amber:#ffc107;--ukbol-red:#dc3545;--ukbol-blue:#0d6efd;--ukbol-black:#343a40;}}
body{{font-family:system-ui,-apple-system,sans-serif;background:linear-gradient(135deg,#f5f7fa 0%,#e4e8ec 100%);min-height:100vh;}}
.hero{{background:linear-gradient(135deg,#1a365d 0%,#2d5a87 100%);color:#fff;padding:3rem 0;margin-bottom:2rem;}}
.hero h1{{font-weight:700;}}
.stat-card{{background:#fff;border-radius:12px;padding:1.5rem;box-shadow:0 2px 12px rgba(0,0,0,.08);transition:transform .2s;height:100%;}}
.stat-card:hover{{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,0,0,.12);}}
.stat-number{{font-size:2.5rem;font-weight:700;color:#1a365d;}}
.gene-card{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);transition:transform .2s;}}
.gene-card:hover{{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,0,0,.12);}}
.gene-card .card-header{{background:linear-gradient(135deg,#1a365d 0%,#2d5a87 100%);color:#fff;font-weight:600;padding:1rem 1.25rem;}}
.status-badge{{display:inline-block;padding:.25em .6em;font-size:.75rem;font-weight:600;border-radius:4px;color:#fff;}}
.status-GREEN{{background:var(--ukbol-green);}}.status-AMBER{{background:var(--ukbol-amber);color:#000;}}.status-RED{{background:var(--ukbol-red);}}.status-BLUE{{background:var(--ukbol-blue);}}.status-BLACK{{background:var(--ukbol-black);}}
.mini-bar{{height:8px;border-radius:4px;background:#e9ecef;overflow:hidden;display:flex;}}
.mini-bar-segment{{height:100%;}}
.zenodo-card{{border-left:4px solid #0d6efd;}}
footer{{background:#1a365d;color:rgba(255,255,255,.8);padding:2rem 0;margin-top:4rem;}}
footer a{{color:rgba(255,255,255,.9);}}
</style>
</head>
<body>
<div class="hero">
<div class="container">
<div class="row align-items-center">
<div class="col-lg-8"><h1>UKBOL Gap Analysis</h1><p class="lead mb-0">Tracking DNA barcode coverage for UK biodiversity</p></div>
<div class="col-lg-4 text-lg-end mt-3 mt-lg-0"><span class="badge bg-light text-dark px-3 py-2">Updated: {build_date}</span></div>
</div></div></div>
<div class="container">
<div class="row g-4 mb-5">
<div class="col-md-3"><div class="stat-card text-center"><div class="stat-number">{valid_species:,}</div><div class="text-muted">Valid Species Assessed</div></div></div>
<div class="col-md-3"><div class="stat-card text-center"><div class="stat-number">{len(genes_data)}</div><div class="text-muted">Gene Regions</div></div></div>
<div class="col-md-3"><div class="stat-card text-center"><div class="stat-number text-success">{species_with_data:,}</div><div class="text-muted">Species with Data</div></div></div>
<div class="col-md-3"><div class="stat-card text-center"><div class="stat-number" style="color:#343a40">{true_gaps:,}</div><div class="text-muted">True Gaps (No Data)</div></div></div>
</div>
<div class="stat-card mb-5">
<h4 class="mb-3">How to Use This Portal</h4>
<div class="row">
<div class="col-md-6">
<p><strong>1. Select a Gene Region</strong> - Click any card below to explore gap analysis data.</p>
<p><strong>2. Filter &amp; Search</strong> - Use filters to find species by taxonomy, habitat, or conservation status.</p>
<p><strong>3. Share &amp; Download</strong> - Share filtered views via URL or download as CSV.</p>
</div>
<div class="col-md-6">
<p><strong>Traffic Light System:</strong></p>
<div class="d-flex flex-wrap gap-2">
<span class="status-badge status-GREEN">OK - Valid</span>
<span class="status-badge status-BLUE">OK - Synonym</span>
<span class="status-badge status-AMBER">OK - Valid + Synonym</span>
<span class="status-badge status-RED">ID Conflict</span>
<span class="status-badge status-BLACK">Missing</span>
</div></div></div></div>
<h3 class="mb-4">Available Datasets</h3>
<div class="row g-4 mb-5">''')

    for gene in genes_data:
        stats = gene['stats']
        status_counts = stats['status_counts']
        total = stats['total_species']
        bar_segments = []
        for status in ['GREEN', 'AMBER', 'RED', 'BLUE', 'BLACK']:
            count = status_counts.get(status, 0)
            if count > 0:
                pct = (count / total) * 100
                color = STATUS_COLORS.get(status, '#6c757d')
                bar_segments.append(f'<div class="mini-bar-segment" style="width:{pct:.1f}%;background:{color}"></div>')
        bar_html = ''.join(bar_segments)
        
        gene_labels = gene.get('status_labels', STATUS_LABELS)
        badges = ''.join([f'<small class="status-badge status-{s}">{gene_labels.get(s, s)}: {status_counts.get(s, 0):,}</small>'
                         for s in ['GREEN', 'BLUE', 'AMBER', 'RED', 'BLACK'] if status_counts.get(s, 0) > 0])
        
        html_parts.append(f'''<div class="col-md-6 col-lg-4">
<a href="{gene['filename']}" class="text-decoration-none">
<div class="gene-card h-100">
<div class="card-header">{gene['display_name']}</div>
<div class="card-body">
<div class="d-flex justify-content-between mb-2"><span class="text-muted">{total:,} species</span><span class="text-success fw-bold">{status_counts.get('GREEN', 0):,} covered</span></div>
<div class="mini-bar mb-3">{bar_html}</div>
<div class="d-flex flex-wrap gap-1">{badges}</div>
</div></div></a></div>''')

    html_parts.append('</div>')

    if zenodo_links:
        html_parts.append('<h3 class="mb-4">Related Datasets (Zenodo)</h3><div class="row g-4 mb-5">')
        for link in zenodo_links:
            html_parts.append(f'''<div class="col-md-6"><div class="stat-card zenodo-card">
<h5>{link.get('title', 'Dataset')}</h5>
<p class="text-muted mb-2">{link.get('description', '')}</p>
<div class="d-flex justify-content-between align-items-center">
<small class="text-muted">DOI: {link.get('doi', 'N/A')}</small>
<a href="{link.get('url', '#')}" target="_blank" class="btn btn-sm btn-outline-primary">View on Zenodo</a>
</div></div></div>''')
        html_parts.append('</div>')

    # Build dataset metadata table if available
    metadata_html = ''
    if dataset_metadata is not None and len(dataset_metadata) > 0:
        metadata_rows = ''.join([
            f'<tr><td>{row.get("Gene", "")}</td><td>{row.get("Database", "")}</td><td>{row.get("Version", "")}</td><td><a href="{row.get("Link", "#")}" target="_blank">Source</a></td></tr>'
            for _, row in dataset_metadata.iterrows()
        ])
        metadata_html = f'''<div class="mt-4">
<h6 class="text-light mb-2">Reference Database Versions</h6>
<table class="table table-sm table-dark table-striped" style="max-width:600px;margin:0 auto;font-size:.85rem;">
<thead><tr><th>Gene</th><th>Database</th><th>Version</th><th>Link</th></tr></thead>
<tbody>{metadata_rows}</tbody>
</table></div>'''

    html_parts.append(f'''</div>
<footer><div class="container text-center">
<p class="mb-2">UK Barcode of Life (UKBOL) Gap Analysis Portal</p>
<p class="small mb-0">Part of <a href="https://ibol.org/" target="_blank">International Barcode of Life</a> | Data generated {build_date}</p>
{metadata_html}
</div></footer>
</body></html>''')

    output_path = Path(output_dir) / 'index.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))
    print(f"  - Generated index.html")



def get_default_filter_for_gene(gene_name):
    """Determine default taxonomy filter based on gene name."""
    gene_lower = gene_name.lower()
    for gene_key, filters in GENE_DEFAULT_FILTERS.items():
        if gene_key in gene_lower:
            return filters
    return {}


def generate_report_html(gene_name, display_name, df, stats, jncc_columns, filter_options, output_dir, build_date, has_gb_records=False, status_labels=None):
    if status_labels is None:
        status_labels = STATUS_LABELS
    jncc_info = [{'original': col, 'display': clean_column_name(col)} for col in jncc_columns]
    default_filters = get_default_filter_for_gene(gene_name)

    # Build status filter buttons from labels
    btn_classes = {'GREEN': 'btn-outline-success', 'BLUE': 'btn-outline-primary', 'AMBER': 'btn-outline-warning', 'RED': 'btn-outline-danger', 'BLACK': 'btn-outline-dark'}
    status_buttons = '\n'.join([
        f'<button class="btn btn-sm {btn_classes[s]} status-btn active" data-status="{s}">{status_labels[s]}</button>'
        for s in ['GREEN', 'BLUE', 'AMBER', 'RED', 'BLACK'] if s in status_labels
    ])

    # Build table column definitions based on columns present in the dataframe
    # Special renderers: 'truncate' for long text, 'status' for colored badges, 'data_link' for external links
    COLUMN_RENDERERS = {'synonyms': 'truncate', 'other_names': 'truncate', 'species_status': 'status'}
    table_columns = []
    for col_name, col_title in DISPLAY_COLUMNS:
        if col_name == 'data_link':
            table_columns.append({'data': None, 'title': 'Data Link', 'render': 'data_link', 'orderable': False})
        elif col_name in df.columns:
            col_def = {'data': col_name, 'title': col_title}
            if col_name in COLUMN_RENDERERS:
                col_def['render'] = COLUMN_RENDERERS[col_name]
            table_columns.append(col_def)

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>''' + display_name + ''' - UKBOL Gap Analysis</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.datatables.net/1.13.8/css/dataTables.bootstrap5.min.css" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
:root{--ukbol-green:#198754;--ukbol-amber:#ffc107;--ukbol-red:#dc3545;--ukbol-blue:#0d6efd;--ukbol-black:#343a40;}
body{font-family:system-ui,-apple-system,sans-serif;background:#f5f7fa;}
.navbar{background:linear-gradient(135deg,#1a365d 0%,#2d5a87 100%)!important;}
.stat-card,.filter-panel,.chart-container,.table-container{background:#fff;border-radius:12px;padding:1.25rem;box-shadow:0 2px 12px rgba(0,0,0,.08);}
.chart-container,.table-container,.filter-panel{margin-bottom:1.5rem;}
.chart-container{overflow:hidden;}
.filter-panel h5{margin-bottom:1rem;padding-bottom:.5rem;border-bottom:1px solid #e9ecef;}
.status-badge{display:inline-block;padding:.15em .45em;font-size:.7rem;font-weight:600;border-radius:4px;color:#fff;white-space:nowrap;}
.status-GREEN{background:var(--ukbol-green);}.status-AMBER{background:var(--ukbol-amber);color:#000;}.status-RED{background:var(--ukbol-red);}.status-BLUE{background:var(--ukbol-blue);}.status-BLACK{background:var(--ukbol-black);}
.filter-tag{display:inline-flex;align-items:center;gap:.25rem;background:#e7f1ff;color:#0d6efd;padding:.25rem .75rem;border-radius:20px;font-size:.85rem;margin:.25rem;}
.filter-tag button{background:none;border:none;color:inherit;padding:0;font-size:1rem;cursor:pointer;}
#activeFilters:empty::before{content:"No filters active";color:#6c757d;font-style:italic;}
.loading{text-align:center;padding:3rem;}
.loading-spinner{display:inline-block;width:3rem;height:3rem;border:3px solid #f3f3f3;border-top:3px solid #3498db;border-radius:50%;animation:spin 1s linear infinite;}
@keyframes spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
.url-indicator{position:fixed;bottom:20px;right:20px;background:#fff;padding:.75rem 1rem;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,.15);font-size:.85rem;z-index:1000;display:none;}
.url-indicator.show{display:block;}
table.dataTable tbody tr:hover{background-color:#f8f9fa!important;}
/* Compact table styling */
table.dataTable{font-size:.8rem;}
table.dataTable th,table.dataTable td{padding:.35rem .4rem;white-space:nowrap;}
table.dataTable th{font-size:.75rem;}
/* Truncated cells for long text */
.truncate-cell{max-width:140px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;}
/* Data link icons */
.data-link a{text-decoration:none;margin-right:0.25rem;font-size:.85rem;}
.data-link a:hover{opacity:0.7;}
/* Mobile support */
.status-btn{touch-action:manipulation;-webkit-tap-highlight-color:transparent;cursor:pointer;user-select:none;}
@media(hover:none){.status-btn:hover{color:inherit;background-color:inherit;border-color:inherit;}}
.filter-panel select,.filter-panel input,.filter-panel button{font-size:16px;}
@media(max-width:991px){.filter-panel{margin-bottom:1rem;}.status-btn{padding:.5rem .75rem;margin:.25rem;}}
</style>
</head>
<body>
<nav class="navbar navbar-dark mb-4">
<div class="container-fluid">
<a class="navbar-brand" href="index.html"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="me-2" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M15 8a.5.5 0 0 0-.5-.5H2.707l3.147-3.146a.5.5 0 1 0-.708-.708l-4 4a.5.5 0 0 0 0 .708l4 4a.5.5 0 0 0 .708-.708L2.707 8.5H14.5A.5.5 0 0 0 15 8z"/></svg>Back to Portal</a>
<span class="navbar-text fw-bold">''' + display_name + '''</span>
<span class="navbar-text text-light opacity-75">''' + f"{stats['total_species']:,}" + ''' species | Updated ''' + build_date + '''</span>
</div></nav>
<div class="container-fluid px-4">
<div class="row">
<div class="col-lg-3">
<div class="filter-panel">
<h5>Filters</h5>
<div class="mb-3">
<label class="form-label fw-bold">Taxonomy</label>
<select id="filterKingdom" class="form-select form-select-sm mb-2"><option value="">All Kingdoms</option></select>
<select id="filterPhylum" class="form-select form-select-sm mb-2"><option value="">All Phyla</option></select>
<select id="filterClass" class="form-select form-select-sm mb-2"><option value="">All Classes</option></select>
<select id="filterOrder" class="form-select form-select-sm mb-2"><option value="">All Orders</option></select>
<select id="filterFamily" class="form-select form-select-sm"><option value="">All Families</option></select>
</div>
<div class="mb-3">
<label class="form-label fw-bold">Coverage Status</label>
<div class="d-flex flex-wrap gap-1">
''' + status_buttons + '''
</div></div>
<div class="mb-3">
<label class="form-label fw-bold">Habitat</label>
<div class="form-check"><input class="form-check-input habitat-filter" type="checkbox" value="freshwater_ukceh" id="habitatFreshwaterUkceh"><label class="form-check-label" for="habitatFreshwaterUkceh">Freshwater (UKCEH)</label></div>
<div class="form-check"><input class="form-check-input habitat-filter" type="checkbox" value="freshwater" id="habitatFreshwater"><label class="form-check-label" for="habitatFreshwater">Freshwater (UKSI)</label></div>
<div class="form-check"><input class="form-check-input habitat-filter" type="checkbox" value="marine" id="habitatMarine"><label class="form-check-label" for="habitatMarine">Marine (UKSI)</label></div>
<div class="form-check"><input class="form-check-input habitat-filter" type="checkbox" value="terrestrial" id="habitatTerrestrial"><label class="form-check-label" for="habitatTerrestrial">Terrestrial (UKSI)</label></div>
</div>
<div class="mb-3">
<label class="form-label fw-bold">Assemblage</label>
<div class="form-check"><input class="form-check-input assemblage-filter" type="checkbox" value="freshbase" id="assemblageFreshbase"><label class="form-check-label" for="assemblageFreshbase">Freshwater macroinverts</label></div>
<select id="filterPantheonAssemblage" class="form-select form-select-sm mt-2"><option value="">All PANTHEON assemblages</option></select>
</div>
<div class="mb-3">
<label class="form-label fw-bold">Conservation Designations</label>
<div class="form-check"><input class="form-check-input" type="checkbox" id="filterProtected"><label class="form-check-label" for="filterProtected">Taxa with conservation designations</label></div>
</div>
''' + ('''<div class="mb-3">
<label class="form-label fw-bold">UK Records</label>
<select id="filterGbRecords" class="form-select form-select-sm"><option value="">All species</option><option value="with">With UK records</option><option value="without">Without UK records</option></select>
</div>
''' if has_gb_records else '') + '''<div class="d-grid gap-2">
<button id="applyFilters" class="btn btn-primary">Apply Filters</button>
<button id="resetFilters" class="btn btn-outline-secondary">Reset All</button>
<button id="shareUrl" class="btn btn-outline-info">Share Filtered View</button>
</div></div>
<div class="filter-panel">
<h5>Active Filters</h5>
<div id="activeFilters"></div>
<div class="mt-2 text-muted small"><span id="filteredCount">''' + f"{stats['total_species']:,}" + '''</span> of ''' + f"{stats['total_species']:,}" + ''' species shown</div>
</div></div>
<div class="col-lg-9">
<div class="row mb-4">
<div class="col-md-4"><div class="chart-container h-100"><h6 class="text-muted text-uppercase small mb-2">Coverage Overview</h6><div id="pieChart" style="height:280px;"></div></div></div>
<div class="col-md-8"><div class="chart-container h-100"><h6 class="text-muted text-uppercase small mb-2">Gap Analysis by Order (Top 20)</h6><div id="barChart" style="height:280px;"></div></div></div>
</div>
<div class="table-container">
<div class="d-flex justify-content-between align-items-center mb-3">
<h5 class="mb-0">Species Data</h5>
<div class="btn-group">
<button id="downloadFiltered" class="btn btn-sm btn-outline-success">Download Filtered (CSV)</button>
<button id="downloadAll" class="btn btn-sm btn-outline-primary">Download All (TSV)</button>
</div></div>
<div id="loadingIndicator" class="loading"><div class="loading-spinner"></div><p class="mt-3">Loading data...</p></div>
<div id="tableWrapper" style="display:none;">
<div class="table-responsive"><table id="dataTable" class="table table-striped table-hover" style="width:100%"><thead></thead><tbody></tbody></table></div>
</div></div></div></div></div>
<div id="urlIndicator" class="url-indicator">URL copied to clipboard!</div>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/dataTables.bootstrap5.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js"></script>
<script>
const FILTER_OPTIONS = ''' + json.dumps(filter_options) + ''';
const JNCC_COLUMNS = ''' + json.dumps(jncc_info) + ''';
const STATUS_COLORS = {"GREEN":"#198754","AMBER":"#ffc107","RED":"#dc3545","BLUE":"#0d6efd","BLACK":"#343a40"};
const STATUS_LABELS = ''' + json.dumps(status_labels) + ''';
const DEFAULT_FILTERS = ''' + json.dumps(default_filters) + ''';
const TABLE_COLUMNS = ''' + json.dumps(table_columns) + ''';
const DATA_FILE = 'data/''' + gene_name + '''.json.gz';
const TSV_FILE = 'data/''' + gene_name + '''.tsv';
let DATA = [], filteredData = [], table = null;

async function loadData() {
    try {
        const response = await fetch(DATA_FILE);
        const buffer = await response.arrayBuffer();
        const decompressed = pako.ungzip(new Uint8Array(buffer), { to: 'string' });
        DATA = JSON.parse(decompressed);
        filteredData = [...DATA];
        document.getElementById('loadingIndicator').style.display = 'none';
        document.getElementById('tableWrapper').style.display = 'block';
        initializeTable();
        updateCharts();
        loadFiltersFromUrl();
    } catch (e) {
        console.error('Error loading data:', e);
        document.getElementById('loadingIndicator').innerHTML = '<p class="text-danger">Error loading data. Please try refreshing.</p>';
    }
}

// Cascading dropdown helper functions
function getUniqueValues(data, column) {
    return [...new Set(data.map(r => r[column]).filter(Boolean))].sort();
}

function rebuildSelect(selectId, values, placeholder) {
    const select = document.getElementById(selectId);
    const currentValue = select.value;
    select.innerHTML = '<option value="">' + placeholder + '</option>';
    values.forEach(value => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    });
    if (values.includes(currentValue)) {
        select.value = currentValue;
    }
}

function updateCascadingDropdowns(changedLevel) {
    const levels = ['kingdom', 'phylum', 'class', 'order', 'family'];
    const changedIndex = levels.indexOf(changedLevel);
    const selectIds = ['filterKingdom', 'filterPhylum', 'filterClass', 'filterOrder', 'filterFamily'];
    
    // Clear selections below the changed level
    for (let i = changedIndex + 1; i < levels.length; i++) {
        document.getElementById(selectIds[i]).value = '';
    }
    
    // Rebuild dropdowns below the changed level
    let filtered = DATA;
    
    const kingdom = document.getElementById('filterKingdom').value;
    if (kingdom) filtered = filtered.filter(r => r.kingdom === kingdom);
    
    if (changedIndex < 1) {
        rebuildSelect('filterPhylum', getUniqueValues(filtered, 'phylum_division'), 'All Phyla');
    }
    
    const phylum = document.getElementById('filterPhylum').value;
    if (phylum) filtered = filtered.filter(r => r.phylum_division === phylum);
    
    if (changedIndex < 2) {
        rebuildSelect('filterClass', getUniqueValues(filtered, 'class'), 'All Classes');
    }
    
    const cls = document.getElementById('filterClass').value;
    if (cls) filtered = filtered.filter(r => r.class === cls);
    
    if (changedIndex < 3) {
        rebuildSelect('filterOrder', getUniqueValues(filtered, 'order'), 'All Orders');
    }
    
    const order = document.getElementById('filterOrder').value;
    if (order) filtered = filtered.filter(r => r.order === order);
    
    if (changedIndex < 4) {
        rebuildSelect('filterFamily', getUniqueValues(filtered, 'family'), 'All Families');
    }
}

function initializeFilters() {
    const taxonomyFilters = {
        'filterKingdom': ['kingdom', 'All Kingdoms'],
        'filterPhylum': ['phylum_division', 'All Phyla'],
        'filterClass': ['class', 'All Classes'],
        'filterOrder': ['order', 'All Orders'],
        'filterFamily': ['family', 'All Families']
    };
    
    for (const [selectId, [column, placeholder]] of Object.entries(taxonomyFilters)) {
        const select = document.getElementById(selectId);
        if (FILTER_OPTIONS[column]) {
            FILTER_OPTIONS[column].forEach(value => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = value;
                select.appendChild(option);
            });
        }
    }
    
    // Populate PANTHEON assemblage dropdown
    if (FILTER_OPTIONS.pantheon_assemblage) {
        const paSelect = document.getElementById('filterPantheonAssemblage');
        FILTER_OPTIONS.pantheon_assemblage.forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            paSelect.appendChild(option);
        });
    }
    // Add cascade listeners
    document.getElementById('filterKingdom').addEventListener('change', () => updateCascadingDropdowns('kingdom'));
    document.getElementById('filterPhylum').addEventListener('change', () => updateCascadingDropdowns('phylum'));
    document.getElementById('filterClass').addEventListener('change', () => updateCascadingDropdowns('class'));
    document.getElementById('filterOrder').addEventListener('change', () => updateCascadingDropdowns('order'));
}
function initializeTable() {
    const escapeHtml = (str) => {
        if (!str) return '';
        return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    };
    const truncateRender = (data) => data ? `<span class="truncate-cell" title="${escapeHtml(data)}">${escapeHtml(data)}</span>` : '';
    const dataLinkRender = (data, type, row) => {
        // Check for BOLD BIN URIs first
        if (row.bin_uris && row.bin_uris.trim()) {
            const bins = row.bin_uris.split(';').map(b => b.trim()).filter(b => b);
            if (bins.length > 0) {
                const query = bins.map(b => b + '[bin]').join(',');
                const url = 'https://portal.boldsystems.org/result?query=' + query;
                return '<span class="data-link"><a href="' + url + '" target="_blank" rel="noopener">&#128279;</a></span>';
            }
        }
        // Check for UNITE Species Hypothesis IDs (SH*.FU pattern)
        if (row.otu_ids && row.otu_ids.trim()) {
            const ids = row.otu_ids.split(';').map(id => id.trim()).filter(id => id);
            const shIds = ids.filter(id => /^SH\\d+\\.\\d+FU$/.test(id));
            if (shIds.length > 0) {
                const links = shIds.map(sh => {
                    const url = 'https://dx.doi.org/10.15156/BIO/' + sh;
                    return '<a href="' + url + '" target="_blank" rel="noopener">&#128279;</a>';
                }).join(' ');
                return '<span class="data-link">' + links + '</span>';
            }
        }
        // Check for DToL INSDC project IDs (PRJ* pattern)
        if (row.dtol_insdc_ids && row.dtol_insdc_ids.trim()) {
            const ids = row.dtol_insdc_ids.split(';').map(id => id.trim()).filter(id => id);
            if (ids.length > 0) {
                const links = ids.map(id => {
                    const url = 'https://www.ebi.ac.uk/ena/browser/view/' + id;
                    return '<a href="' + url + '" target="_blank" rel="noopener">&#128279;</a>';
                }).join(' ');
                return '<span class="data-link">' + links + '</span>';
            }
        }
        // Check for ENA mitogenome accessions
        if (row.mitogenome_accessions && row.mitogenome_accessions.trim()) {
            const ids = row.mitogenome_accessions.split(';').map(id => id.trim()).filter(id => id);
            if (ids.length > 0) {
                const links = ids.map(id => {
                    const url = 'https://www.ebi.ac.uk/ena/browser/view/' + id;
                    return '<a href="' + url + '" target="_blank" rel="noopener">&#128279;</a>';
                }).join(' ');
                return '<span class="data-link">' + links + '</span>';
            }
        }
        return '—';
    };
    const RENDERERS = {
        'truncate': truncateRender,
        'status': (data)=>data?`<span class="status-badge status-${data}">${STATUS_LABELS[data]||data}</span>`:'',
        'data_link': dataLinkRender
    };
    const columns = TABLE_COLUMNS.map(col => {
        const def = {data:col.data,title:col.title};
        if (col.render && RENDERERS[col.render]) def.render = RENDERERS[col.render];
        if (col.orderable === false) def.orderable = false;
        return def;
    });
    table = $('#dataTable').DataTable({data:filteredData,columns:columns,pageLength:25,order:[[0,'asc']],dom:'<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>rtip',deferRender:true,autoWidth:false});
}
function applyFilters() {
    const filters = collectFilters();
    filteredData = DATA.filter(row => {
        if (filters.kingdom && row.kingdom !== filters.kingdom) return false;
        if (filters.phylum && row.phylum_division !== filters.phylum) return false;
        if (filters.class && row.class !== filters.class) return false;
        if (filters.order && row.order !== filters.order) return false;
        if (filters.family && row.family !== filters.family) return false;
        if (filters.statuses.length > 0 && !filters.statuses.includes(row.species_status)) return false;
        if (filters.habitats.length > 0) {
            const hasHabitat = (filters.habitats.includes('marine') && row.marine_flag === 'Y') || (filters.habitats.includes('freshwater') && row.freshwater === 'Y') || (filters.habitats.includes('terrestrial') && row.terrestrial_freshwater_flag === 'Y') || (filters.habitats.includes('freshwater_ukceh') && row.ukceh_freshwater_list === 'Y');
            if (!hasHabitat) return false;
        }
        if (filters.assemblages.length > 0) {
            const hasAssemblage = (filters.assemblages.includes('freshbase') && row.freshbase === 'Y');
            if (!hasAssemblage) return false;
        }
        if (filters.pantheonAssemblage) {
            const sat = row.pantheon_specific_assemblage_type || '';
            const codes = sat.split(',').map(c => c.trim());
            if (!codes.includes(filters.pantheonAssemblage)) return false;
        }
        if (filters.protected) {
            const hasAnyProtection = JNCC_COLUMNS.some(col => row[col.original] && row[col.original] !== '');
            if (!hasAnyProtection) return false;
        }
        if (filters.gbRecords === 'with' && !(Number(row.gb_records) > 0)) return false;
        if (filters.gbRecords === 'without' && Number(row.gb_records) > 0) return false;
        return true;
    });
    table.clear().rows.add(filteredData).draw();
    document.getElementById('filteredCount').textContent = filteredData.length.toLocaleString();
    updateActiveFiltersDisplay(filters);
    updateCharts();
    updateUrl(filters);
}
function collectFilters() {
    const activeStatuses = [], activeHabitats = [], activeAssemblages = [];
    document.querySelectorAll('.status-btn.active').forEach(btn => activeStatuses.push(btn.dataset.status));
    document.querySelectorAll('.habitat-filter:checked').forEach(cb => activeHabitats.push(cb.value));
    document.querySelectorAll('.assemblage-filter:checked').forEach(cb => activeAssemblages.push(cb.value));
    return {
        kingdom:document.getElementById('filterKingdom').value,
        phylum:document.getElementById('filterPhylum').value,
        class:document.getElementById('filterClass').value,
        order:document.getElementById('filterOrder').value,
        family:document.getElementById('filterFamily').value,
        statuses:activeStatuses,
        habitats:activeHabitats,
        assemblages:activeAssemblages,
        pantheonAssemblage:document.getElementById('filterPantheonAssemblage').value,
        protected:document.getElementById('filterProtected').checked,
        gbRecords:document.getElementById('filterGbRecords')?document.getElementById('filterGbRecords').value:''
    };
}
function updateActiveFiltersDisplay(filters) {
    const container = document.getElementById('activeFilters');
    container.innerHTML = '';
    const addTag = (label, value, clearFn) => {const tag = document.createElement('div');tag.className='filter-tag';tag.innerHTML=`${label}: ${value} <button onclick="${clearFn}">×</button>`;container.appendChild(tag);};
    if (filters.kingdom) addTag('Kingdom',filters.kingdom,"document.getElementById('filterKingdom').value='';applyFilters()");
    if (filters.phylum) addTag('Phylum',filters.phylum,"document.getElementById('filterPhylum').value='';applyFilters()");
    if (filters.class) addTag('Class',filters.class,"document.getElementById('filterClass').value='';applyFilters()");
    if (filters.order) addTag('Order',filters.order,"document.getElementById('filterOrder').value='';applyFilters()");
    if (filters.family) addTag('Family',filters.family,"document.getElementById('filterFamily').value='';applyFilters()");
    // Show status filters when not all are selected
    const allStatuses = ['GREEN','BLUE','AMBER','RED','BLACK'];
    if (filters.statuses.length > 0 && filters.statuses.length < 5) {
        const excludedStatuses = allStatuses.filter(s => !filters.statuses.includes(s));
        excludedStatuses.forEach(status => {
            addTag('Hiding', STATUS_LABELS[status] || status, `document.querySelector('.status-btn[data-status="${status}"]').classList.add('active');applyFilters()`);
        });
    }
    const habitatLabels = {'marine':'Marine (UKSI)','freshwater':'Freshwater (UKSI)','terrestrial':'Terrestrial (UKSI)','freshwater_ukceh':'Freshwater (UKCEH)'};
    const habitatIds = {'marine':'habitatMarine','freshwater':'habitatFreshwater','terrestrial':'habitatTerrestrial','freshwater_ukceh':'habitatFreshwaterUkceh'};
    filters.habitats.forEach(h => addTag('Habitat',habitatLabels[h]||h,`document.getElementById('${habitatIds[h]}').checked=false;applyFilters()`));
    const assemblageLabels = {'freshbase':'Freshwater macroinverts'};
    const assemblageIds = {'freshbase':'assemblageFreshbase'};
    filters.assemblages.forEach(a => addTag('Assemblage',assemblageLabels[a]||a,`document.getElementById('${assemblageIds[a]}').checked=false;applyFilters()`));
    if (filters.pantheonAssemblage) addTag('PANTHEON',filters.pantheonAssemblage,"document.getElementById('filterPantheonAssemblage').value='';applyFilters()");
    if (filters.protected) addTag('Filter','Conservation designations',"document.getElementById('filterProtected').checked=false;applyFilters()");
    if (filters.gbRecords) {const label=filters.gbRecords==='with'?'With UK records':'Without UK records';addTag('UK Records',label,"document.getElementById('filterGbRecords').value='';applyFilters()");}
}
function updateCharts() {
    const statusCounts = {};
    filteredData.forEach(row => {const status = row.species_status || 'Unknown';statusCounts[status] = (statusCounts[status] || 0) + 1;});
    const pieLabels = Object.keys(statusCounts).map(s => STATUS_LABELS[s] || s);
    Plotly.newPlot('pieChart',[{values:Object.values(statusCounts),labels:pieLabels,type:'pie',hole:0.4,marker:{colors:Object.keys(statusCounts).map(s=>STATUS_COLORS[s]||'#6c757d')},textinfo:'label+percent',textposition:'outside',automargin:true,textfont:{size:11}}],{margin:{t:40,b:40,l:40,r:40},showlegend:false},{responsive:true});
    const orderData = {};
    filteredData.forEach(row => {const order = row.order || 'Unknown';const status = row.species_status || 'Unknown';if(!orderData[order])orderData[order]={};orderData[order][status]=(orderData[order][status]||0)+1;});
    const sortedOrders = Object.entries(orderData).map(([order,counts])=>({order,total:Object.values(counts).reduce((a,b)=>a+b,0),counts})).sort((a,b)=>b.total-a.total).slice(0,20);
    const barTraces = ['GREEN','BLUE','AMBER','RED','BLACK'].map(status=>({x:sortedOrders.map(o=>o.order),y:sortedOrders.map(o=>o.counts[status]||0),name:STATUS_LABELS[status]||status,type:'bar',marker:{color:STATUS_COLORS[status]}}));
    Plotly.newPlot('barChart',barTraces,{barmode:'stack',margin:{t:20,b:100,l:50,r:20},legend:{orientation:'h',y:1.1},xaxis:{tickangle:-45}},{responsive:true});
}
function updateUrl(filters) {
    const params = new URLSearchParams();
    if(filters.kingdom)params.set('kingdom',filters.kingdom);
    if(filters.phylum)params.set('phylum',filters.phylum);
    if(filters.class)params.set('class',filters.class);
    if(filters.order)params.set('order',filters.order);
    if(filters.family)params.set('family',filters.family);
    if(filters.statuses.length<5)params.set('status',filters.statuses.join(','));
    if(filters.habitats.length>0)params.set('habitat',filters.habitats.join(','));
    if(filters.assemblages.length>0)params.set('assemblage',filters.assemblages.join(','));
    if(filters.pantheonAssemblage)params.set('pantheon_assemblage',filters.pantheonAssemblage);
    if(filters.protected)params.set('protected','1');
    if(filters.gbRecords)params.set('gb_records',filters.gbRecords);
    window.history.replaceState({},'',window.location.pathname+(params.toString()?'?'+params.toString():''));
}
function loadFiltersFromUrl() {
    const params = new URLSearchParams(window.location.search);
    let hasUrlFilters = params.toString().length > 0;

    // Apply taxonomy filters in order, rebuilding cascades as we go
    if(params.get('kingdom')){
        document.getElementById('filterKingdom').value=params.get('kingdom');
        updateCascadingDropdowns('kingdom');
    }
    if(params.get('phylum')){
        document.getElementById('filterPhylum').value=params.get('phylum');
        updateCascadingDropdowns('phylum');
    }
    if(params.get('class')){
        document.getElementById('filterClass').value=params.get('class');
        updateCascadingDropdowns('class');
    }
    if(params.get('order')){
        document.getElementById('filterOrder').value=params.get('order');
        updateCascadingDropdowns('order');
    }
    if(params.get('family'))document.getElementById('filterFamily').value=params.get('family');
    if(params.get('status')){const statuses=params.get('status').split(',');document.querySelectorAll('.status-btn').forEach(btn=>btn.classList.toggle('active',statuses.includes(btn.dataset.status)));}
    if(params.get('habitat')){const habitatIdMap={'marine':'habitatMarine','freshwater':'habitatFreshwater','terrestrial':'habitatTerrestrial','freshwater_ukceh':'habitatFreshwaterUkceh'};params.get('habitat').split(',').forEach(h=>{const id=habitatIdMap[h];if(id){const cb=document.getElementById(id);if(cb)cb.checked=true;}});}
    if(params.get('assemblage')){const assemblageIdMap={'freshbase':'assemblageFreshbase'};params.get('assemblage').split(',').forEach(a=>{const id=assemblageIdMap[a];if(id){const cb=document.getElementById(id);if(cb)cb.checked=true;}});}
    if(params.get('pantheon_assemblage'))document.getElementById('filterPantheonAssemblage').value=params.get('pantheon_assemblage');
    if(params.get('protected'))document.getElementById('filterProtected').checked=true;
    if(params.get('gb_records')){const el=document.getElementById('filterGbRecords');if(el)el.value=params.get('gb_records');}

    // Apply default filters if no URL filters present
    if(!hasUrlFilters && Object.keys(DEFAULT_FILTERS).length > 0) {
        if(DEFAULT_FILTERS.kingdom){
            document.getElementById('filterKingdom').value=DEFAULT_FILTERS.kingdom;
            updateCascadingDropdowns('kingdom');
        }
        if(DEFAULT_FILTERS.phylum){
            document.getElementById('filterPhylum').value=DEFAULT_FILTERS.phylum;
            updateCascadingDropdowns('phylum');
        }
        applyFilters();
    } else if(hasUrlFilters) {
        applyFilters();
    }
}
function downloadCSV(data,filename) {
    if(data.length===0)return;
    const headers=Object.keys(data[0]);
    const quoteField=(val)=>{val=String(val||'');if(val.includes(',')||val.includes('"')||val.includes('\\n'))return '"'+val.replace(/"/g,'""')+'"';return val;};
    const csv=[headers.map(quoteField).join(','),...data.map(row=>headers.map(h=>quoteField(row[h])).join(','))].join('\\n');
    const blob=new Blob([csv],{type:'text/csv'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(url);
}
$(document).ready(function() {
    initializeFilters();
    loadData();
    document.getElementById('applyFilters').addEventListener('click',applyFilters);
    document.getElementById('resetFilters').addEventListener('click',()=>{
        document.querySelectorAll('select').forEach(s=>s.value='');
        // Rebuild all dropdowns with full options from DATA
        rebuildSelect('filterKingdom', getUniqueValues(DATA, 'kingdom'), 'All Kingdoms');
        rebuildSelect('filterPhylum', getUniqueValues(DATA, 'phylum_division'), 'All Phyla');
        rebuildSelect('filterClass', getUniqueValues(DATA, 'class'), 'All Classes');
        rebuildSelect('filterOrder', getUniqueValues(DATA, 'order'), 'All Orders');
        rebuildSelect('filterFamily', getUniqueValues(DATA, 'family'), 'All Families');
        document.querySelectorAll('.status-btn').forEach(btn=>btn.classList.add('active'));
        document.querySelectorAll('.habitat-filter').forEach(cb=>cb.checked=false);
        document.querySelectorAll('.assemblage-filter').forEach(cb=>cb.checked=false);
        document.getElementById('filterPantheonAssemblage').value='';
        document.getElementById('filterProtected').checked=false;
        applyFilters();
    });
    // Status button handlers - using both click and touchend for mobile support
    document.querySelectorAll('.status-btn').forEach(btn=>{
        const toggleStatus = (e) => {
            e.preventDefault();
            btn.classList.toggle('active');
            applyFilters();
        };
        btn.addEventListener('click', toggleStatus);
    });
    // Habitat and protection filters - auto-apply on change
    document.querySelectorAll('.habitat-filter').forEach(cb=>cb.addEventListener('change', applyFilters));
    document.querySelectorAll('.assemblage-filter').forEach(cb=>cb.addEventListener('change', applyFilters));
    document.getElementById('filterPantheonAssemblage').addEventListener('change', applyFilters);
    document.getElementById('filterProtected').addEventListener('change', applyFilters);
    if (document.getElementById('filterGbRecords')) document.getElementById('filterGbRecords').addEventListener('change', applyFilters);
    // Taxonomy dropdowns - auto-apply on change
    ['filterKingdom','filterPhylum','filterClass','filterOrder','filterFamily'].forEach(id=>{
        document.getElementById(id).addEventListener('change', applyFilters);
    });
    document.getElementById('shareUrl').addEventListener('click',()=>{navigator.clipboard.writeText(window.location.href).then(()=>{const indicator=document.getElementById('urlIndicator');indicator.classList.add('show');setTimeout(()=>indicator.classList.remove('show'),2000);});});
    document.getElementById('downloadFiltered').addEventListener('click',()=>downloadCSV(filteredData,'filtered_gap_analysis.csv'));
    document.getElementById('downloadAll').addEventListener('click',()=>{window.location.href=TSV_FILE;});
});
</script>
</body></html>'''

    output_path = Path(output_dir) / f"{gene_name}.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  - Generated {gene_name}.html")



def main():
    parser = argparse.ArgumentParser(description='Build UKBOL Gap Analysis website')
    parser.add_argument('--data', default='data', help='Path to data directory')
    parser.add_argument('--output', default='docs', help='Output directory')
    parser.add_argument('--zenodo', default=None, help='Path to zenodo_links.csv')
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.parent
    data_dir = Path(args.data) if Path(args.data).is_absolute() else script_dir / args.data
    output_dir = Path(args.output) if Path(args.output).is_absolute() else script_dir / args.output
    
    print(f"UKBOL Gap Analysis Website Builder")
    print(f"=" * 40)
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {output_dir}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'data').mkdir(parents=True, exist_ok=True)
    
    tsv_files = list(data_dir.glob('*.tsv'))
    if not tsv_files:
        print(f"\n[ERROR] No TSV files found in {data_dir}")
        sys.exit(1)
    
    print(f"\nFound {len(tsv_files)} TSV files")
    build_date = datetime.now().strftime('%Y-%m-%d')
    genes_data = []
    all_dataframes = []  # Collect for cross-gene stats
    
    for tsv_path in sorted(tsv_files):
        filename = tsv_path.name
        # Strip date prefix and _gap_analysis suffix for stable output filenames
        gene_name = re.sub(r'^\d{4}-\d{2}-\d{2}_', '', tsv_path.stem)
        gene_name = re.sub(r'_gap_analysis$', '', gene_name)
        display_name = get_gene_name(str(tsv_path))
        
        print(f"\nProcessing: {filename}")
        print(f"  Display name: {display_name}")
        
        try:
            df = pd.read_csv(tsv_path, sep='\t', encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(tsv_path, sep='\t', encoding='latin-1', low_memory=False)
        
        df = df.fillna('')

        # Detect dataset type
        is_dtol = 'dtol_status' in df.columns
        is_mitogenome = 'mitogenome_count' in df.columns

        if is_dtol:
            status_labels = DTOL_STATUS_LABELS
        elif is_mitogenome:
            status_labels = MITOGENOME_STATUS_LABELS
        else:
            status_labels = STATUS_LABELS

        # Keep reference for cross-gene stats (exclude DToL and mitogenome - different coverage concepts)
        if not is_dtol and not is_mitogenome:
            all_dataframes.append(df)

        dataset_type = 'DToL genome' if is_dtol else ('ENA mitogenome' if is_mitogenome else 'gene')
        print(f"  Rows: {len(df):,}")
        print(f"  Dataset type: {dataset_type}")
        
        jncc_columns = get_jncc_columns(df)
        print(f"  JNCC columns with data: {len(jncc_columns)}")
        
        stats = compute_summary_stats(df)
        print(f"  Status breakdown: {stats['status_counts']}")
        
        filter_options = get_filter_options(df)

        # Check if gb_records column has any non-zero values
        has_gb_records = bool('gb_records' in df.columns and
                         pd.to_numeric(df['gb_records'], errors='coerce').fillna(0).astype(int).gt(0).any())
        print(f"  UK records column active: {has_gb_records}")

        # Save compressed JSON data
        json_path = output_dir / 'data' / f'{gene_name}.json.gz'
        row_count = prepare_data_json(df, jncc_columns, json_path)
        json_size = json_path.stat().st_size / (1024 * 1024)
        print(f"  - Generated {gene_name}.json.gz ({json_size:.1f} MB)")
        
        # Copy original TSV (skip if same file)
        tsv_dest = output_dir / 'data' / f'{gene_name}.tsv'
        if tsv_path.resolve() != tsv_dest.resolve():
            shutil.copy(tsv_path, tsv_dest)
            print(f"  - Copied {gene_name}.tsv")
        else:
            print(f"  - TSV already in output directory")
        
        # Generate HTML
        generate_report_html(gene_name, display_name, df, stats, jncc_columns, filter_options, output_dir, build_date, has_gb_records, status_labels)
        
        genes_data.append({
            'filename': f"{gene_name}.html",
            'display_name': display_name,
            'stats': stats,
            'status_labels': status_labels,
        })
    
    # Zenodo links
    zenodo_links = []
    zenodo_path = args.zenodo or (data_dir / 'zenodo_links.csv')
    if Path(zenodo_path).exists():
        try:
            zenodo_df = pd.read_csv(zenodo_path)
            zenodo_links = zenodo_df.to_dict('records')
            print(f"\nLoaded {len(zenodo_links)} Zenodo links")
        except Exception as e:
            print(f"\nWarning: Could not read Zenodo links: {e}")
    
    print("\nGenerating index page...")
    
    # Compute cross-gene summary statistics
    cross_gene_stats = compute_cross_gene_stats(all_dataframes)
    print(f"  Cross-gene stats: {cross_gene_stats}")
    
    # Load dataset metadata if available
    dataset_metadata = None
    metadata_path = script_dir / 'metadata' / 'dataset_metadata.tsv'
    if metadata_path.exists():
        try:
            dataset_metadata = pd.read_csv(metadata_path, sep='\t', encoding='utf-8')
            print(f"  Loaded dataset metadata: {len(dataset_metadata)} entries")
        except Exception as e:
            print(f"  Warning: Could not read dataset metadata: {e}")
    
    generate_index_html(genes_data, zenodo_links, output_dir, build_date, cross_gene_stats, dataset_metadata)
    
    print(f"\n[OK] Build complete!")
    print(f"   Output: {output_dir}")
    print(f"   Open index.html to view the portal")


if __name__ == '__main__':
    main()
