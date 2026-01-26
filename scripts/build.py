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

JNCC_PREFIXES = ['jncc_', 'pantheon_']

CORE_COLUMNS = [
    'taxon_name', 'taxon_authority', 'kingdom', 'phylum_division', 
    'class', 'order', 'family', 'genus', 'species_status', 
    'bags_grade', 'number_records', 'marine_flag', 'freshwater',
    'terrestrial_freshwater_flag', 'non_native_flag'
]


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
    selected_cols = [c for c in CORE_COLUMNS if c in df.columns]
    selected_cols.extend([c for c in jncc_columns if c not in selected_cols])
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
    
    # Start with first dataset as base (deduplicated)
    base_df = dataframes[0][['taxon_name']].drop_duplicates()
    
    # Merge status from each dataset
    for i, df in enumerate(dataframes):
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



def generate_index_html(genes_data, zenodo_links, output_dir, build_date, cross_gene_stats=None):
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
<span class="status-badge status-GREEN">GREEN - Valid name with data</span>
<span class="status-badge status-AMBER">AMBER - Valid and synonyms with data</span>
<span class="status-badge status-RED">RED - Taxonomic conflict found in data</span>
<span class="status-badge status-BLACK">BLACK - No data (gaps)</span>
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
        
        badges = ''.join([f'<small class="status-badge status-{s}">{s}: {status_counts.get(s, 0):,}</small>' 
                         for s in ['GREEN', 'AMBER', 'RED', 'BLACK'] if status_counts.get(s, 0) > 0])
        
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

    html_parts.append(f'''</div>
<footer><div class="container text-center">
<p class="mb-2">UK Barcode of Life (UKBOL) Gap Analysis Portal</p>
<p class="small mb-0">Part of <a href="https://ibol.org/" target="_blank">International Barcode of Life</a> | Data generated {build_date}</p>
</div></footer>
</body></html>''')

    output_path = Path(output_dir) / 'index.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_parts))
    print(f"  - Generated index.html")



def generate_report_html(gene_name, display_name, df, stats, jncc_columns, filter_options, output_dir, build_date):
    jncc_info = [{'original': col, 'display': clean_column_name(col)} for col in jncc_columns]
    
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
.filter-panel h5{margin-bottom:1rem;padding-bottom:.5rem;border-bottom:1px solid #e9ecef;}
.status-badge{display:inline-block;padding:.25em .6em;font-size:.8rem;font-weight:600;border-radius:4px;color:#fff;}
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
<button class="btn btn-sm btn-outline-success status-btn active" data-status="GREEN">GREEN</button>
<button class="btn btn-sm btn-outline-warning status-btn active" data-status="AMBER">AMBER</button>
<button class="btn btn-sm btn-outline-danger status-btn active" data-status="RED">RED</button>
<button class="btn btn-sm btn-outline-primary status-btn active" data-status="BLUE">BLUE</button>
<button class="btn btn-sm btn-outline-dark status-btn active" data-status="BLACK">BLACK</button>
</div></div>
<div class="mb-3">
<label class="form-label fw-bold">Habitat</label>
<div class="form-check"><input class="form-check-input habitat-filter" type="checkbox" value="marine" id="habitatMarine"><label class="form-check-label" for="habitatMarine">Marine</label></div>
<div class="form-check"><input class="form-check-input habitat-filter" type="checkbox" value="freshwater" id="habitatFreshwater"><label class="form-check-label" for="habitatFreshwater">Freshwater</label></div>
<div class="form-check"><input class="form-check-input habitat-filter" type="checkbox" value="terrestrial" id="habitatTerrestrial"><label class="form-check-label" for="habitatTerrestrial">Terrestrial</label></div>
</div>
<div class="mb-3">
<label class="form-label fw-bold">Protection Status</label>
<div class="form-check"><input class="form-check-input" type="checkbox" id="filterProtected"><label class="form-check-label" for="filterProtected">Show only protected species</label></div>
</div>
<div class="d-grid gap-2">
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
<div class="col-md-4"><div class="chart-container"><h6 class="text-muted text-uppercase small mb-2">Coverage Overview</h6><div id="pieChart" style="height:280px;"></div></div></div>
<div class="col-md-8"><div class="chart-container"><h6 class="text-muted text-uppercase small mb-2">Gap Analysis by Order (Top 20)</h6><div id="barChart" style="height:280px;"></div></div></div>
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
    
    // Add cascade listeners
    document.getElementById('filterKingdom').addEventListener('change', () => updateCascadingDropdowns('kingdom'));
    document.getElementById('filterPhylum').addEventListener('change', () => updateCascadingDropdowns('phylum'));
    document.getElementById('filterClass').addEventListener('change', () => updateCascadingDropdowns('class'));
    document.getElementById('filterOrder').addEventListener('change', () => updateCascadingDropdowns('order'));
}
function initializeTable() {
    const columns = [
        {data:'taxon_name',title:'Species'},
        {data:'taxon_authority',title:'Authority'},
        {data:'order',title:'Order'},
        {data:'family',title:'Family'},
        {data:'species_status',title:'Status',render:(data)=>data?`<span class="status-badge status-${data}">${data}</span>`:''},
        {data:'bags_grade',title:'Grade'},
        {data:'number_records',title:'Records'}
    ];
    table = $('#dataTable').DataTable({data:filteredData,columns:columns,pageLength:25,order:[[0,'asc']],dom:'<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>rtip',deferRender:true});
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
            const hasHabitat = (filters.habitats.includes('marine') && row.marine_flag === 'Y') || (filters.habitats.includes('freshwater') && row.freshwater === 'Y') || (filters.habitats.includes('terrestrial') && row.terrestrial_freshwater_flag === 'Y');
            if (!hasHabitat) return false;
        }
        if (filters.protected) {
            const hasAnyProtection = JNCC_COLUMNS.some(col => row[col.original] && row[col.original] !== '');
            if (!hasAnyProtection) return false;
        }
        return true;
    });
    table.clear().rows.add(filteredData).draw();
    document.getElementById('filteredCount').textContent = filteredData.length.toLocaleString();
    updateActiveFiltersDisplay(filters);
    updateCharts();
    updateUrl(filters);
}
function collectFilters() {
    const activeStatuses = [], activeHabitats = [];
    document.querySelectorAll('.status-btn.active').forEach(btn => activeStatuses.push(btn.dataset.status));
    document.querySelectorAll('.habitat-filter:checked').forEach(cb => activeHabitats.push(cb.value));
    return {
        kingdom:document.getElementById('filterKingdom').value,
        phylum:document.getElementById('filterPhylum').value,
        class:document.getElementById('filterClass').value,
        order:document.getElementById('filterOrder').value,
        family:document.getElementById('filterFamily').value,
        statuses:activeStatuses,
        habitats:activeHabitats,
        protected:document.getElementById('filterProtected').checked
    };
}
function updateActiveFiltersDisplay(filters) {
    const container = document.getElementById('activeFilters');
    container.innerHTML = '';
    const addTag = (label, value, clearFn) => {const tag = document.createElement('div');tag.className='filter-tag';tag.innerHTML=`${label}: ${value} <button onclick="${clearFn}">x</button>`;container.appendChild(tag);};
    if (filters.kingdom) addTag('Kingdom',filters.kingdom,"document.getElementById('filterKingdom').value='';applyFilters()");
    if (filters.phylum) addTag('Phylum',filters.phylum,"document.getElementById('filterPhylum').value='';applyFilters()");
    if (filters.class) addTag('Class',filters.class,"document.getElementById('filterClass').value='';applyFilters()");
    if (filters.order) addTag('Order',filters.order,"document.getElementById('filterOrder').value='';applyFilters()");
    if (filters.family) addTag('Family',filters.family,"document.getElementById('filterFamily').value='';applyFilters()");
    filters.habitats.forEach(h => addTag('Habitat',h,`document.getElementById('habitat${h.charAt(0).toUpperCase()+h.slice(1)}').checked=false;applyFilters()`));
    if (filters.protected) addTag('Filter','Protected only',"document.getElementById('filterProtected').checked=false;applyFilters()");
}
function updateCharts() {
    const statusCounts = {};
    filteredData.forEach(row => {const status = row.species_status || 'Unknown';statusCounts[status] = (statusCounts[status] || 0) + 1;});
    Plotly.newPlot('pieChart',[{values:Object.values(statusCounts),labels:Object.keys(statusCounts),type:'pie',hole:0.4,marker:{colors:Object.keys(statusCounts).map(s=>STATUS_COLORS[s]||'#6c757d')},textinfo:'label+percent',textposition:'outside'}],{margin:{t:20,b:20,l:20,r:20},showlegend:false},{responsive:true});
    const orderData = {};
    filteredData.forEach(row => {const order = row.order || 'Unknown';const status = row.species_status || 'Unknown';if(!orderData[order])orderData[order]={};orderData[order][status]=(orderData[order][status]||0)+1;});
    const sortedOrders = Object.entries(orderData).map(([order,counts])=>({order,total:Object.values(counts).reduce((a,b)=>a+b,0),counts})).sort((a,b)=>b.total-a.total).slice(0,20);
    const barTraces = ['GREEN','AMBER','RED','BLUE','BLACK'].map(status=>({x:sortedOrders.map(o=>o.order),y:sortedOrders.map(o=>o.counts[status]||0),name:status,type:'bar',marker:{color:STATUS_COLORS[status]}}));
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
    if(filters.protected)params.set('protected','1');
    window.history.replaceState({},'',window.location.pathname+(params.toString()?'?'+params.toString():''));
}
function loadFiltersFromUrl() {
    const params = new URLSearchParams(window.location.search);
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
    if(params.get('habitat')){params.get('habitat').split(',').forEach(h=>{const cb=document.getElementById(`habitat${h.charAt(0).toUpperCase()+h.slice(1)}`);if(cb)cb.checked=true;});}
    if(params.get('protected'))document.getElementById('filterProtected').checked=true;
    if(params.toString())applyFilters();
}
function downloadCSV(data,filename) {
    if(data.length===0)return;
    const headers=Object.keys(data[0]);
    const csv=[headers.join(','),...data.map(row=>headers.map(h=>{let val=row[h]||'';if(typeof val==='string'&&(val.includes(',')||val.includes('"')))val='"'+val.replace(/"/g,'""')+'"';return val;}).join(','))].join('\\n');
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
        document.getElementById('filterProtected').checked=false;
        applyFilters();
    });
    document.querySelectorAll('.status-btn').forEach(btn=>btn.addEventListener('click',()=>btn.classList.toggle('active')));
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
        gene_name = tsv_path.stem
        display_name = get_gene_name(str(tsv_path))
        
        print(f"\nProcessing: {filename}")
        print(f"  Display name: {display_name}")
        
        try:
            df = pd.read_csv(tsv_path, sep='\t', encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(tsv_path, sep='\t', encoding='latin-1', low_memory=False)
        
        df = df.fillna('')
        
        # Keep reference for cross-gene stats
        all_dataframes.append(df)
        
        print(f"  Rows: {len(df):,}")
        
        jncc_columns = get_jncc_columns(df)
        print(f"  JNCC columns with data: {len(jncc_columns)}")
        
        stats = compute_summary_stats(df)
        print(f"  Status breakdown: {stats['status_counts']}")
        
        filter_options = get_filter_options(df)
        
        # Save compressed JSON data
        json_path = output_dir / 'data' / f'{gene_name}.json.gz'
        row_count = prepare_data_json(df, jncc_columns, json_path)
        json_size = json_path.stat().st_size / (1024 * 1024)
        print(f"  - Generated {gene_name}.json.gz ({json_size:.1f} MB)")
        
        # Copy original TSV
        tsv_dest = output_dir / 'data' / f'{gene_name}.tsv'
        shutil.copy(tsv_path, tsv_dest)
        print(f"  - Copied {gene_name}.tsv")
        
        # Generate HTML
        generate_report_html(gene_name, display_name, df, stats, jncc_columns, filter_options, output_dir, build_date)
        
        genes_data.append({
            'filename': f"{gene_name}.html",
            'display_name': display_name,
            'stats': stats
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
    
    generate_index_html(genes_data, zenodo_links, output_dir, build_date, cross_gene_stats)
    
    print(f"\n[OK] Build complete!")
    print(f"   Output: {output_dir}")
    print(f"   Open index.html to view the portal")


if __name__ == '__main__':
    main()
