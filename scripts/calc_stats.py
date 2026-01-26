import pandas as pd
import os

os.chdir(r'C:\GitHub\species\data')
files = sorted([f for f in os.listdir('.') if f.endswith('.tsv')])

# Load all datasets, deduplicate by taxon_name (keep first occurrence)
dfs = {}
for f in files:
    name = f.replace('2026-01-26_', '').replace('_gap_analysis.tsv', '')
    df = pd.read_csv(f, sep='\t', usecols=['taxon_name', 'species_status'])
    df = df.drop_duplicates(subset='taxon_name', keep='first')
    dfs[name] = df
    print(f"{name}: {len(df)} unique species")

# Use the first dataset as base
base_df = list(dfs.values())[0][['taxon_name']].copy()

# Add status from each dataset
for name, df in dfs.items():
    base_df = base_df.merge(
        df.rename(columns={'species_status': f'status_{name}'}),
        on='taxon_name',
        how='inner'
    )

print(f"\nSpecies in common across all datasets: {len(base_df)}")

# Get status columns
status_cols = [c for c in base_df.columns if c.startswith('status_')]

# Species with at least one GREEN across all genes
has_green = (base_df[status_cols] == 'GREEN').any(axis=1)
green_count = has_green.sum()
print(f"Species with at least one GREEN: {green_count}")

# Species with BLACK across ALL genes (no data at all)
all_black = (base_df[status_cols] == 'BLACK').all(axis=1)
black_count = all_black.sum()
print(f"Species with BLACK across all genes (true gaps): {black_count}")

print(f"\n=== VALUES FOR WEBSITE ===")
print(f"Valid Species Assessed: {len(base_df)}")
print(f"Species with Data (at least one GREEN): {green_count}")
print(f"True Gaps (BLACK everywhere): {black_count}")
