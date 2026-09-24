import pandas as pd
import os

os.chdir(r'C:\GitHub\species\data')
files = sorted([f for f in os.listdir('.') if f.endswith('.tsv')])

# Load all datasets, deduplicate by taxon_name (keep first occurrence)
dfs = {}
for f in files:
    name = f.replace('2026-01-26_', '').replace('_gap_analysis.tsv', '')
    df = pd.read_csv(f, sep='\t', usecols=['taxon_name', 'species_status'])
    # Older outputs use colours; map the two this script needs to status codes
    df['species_status'] = df['species_status'].replace({'GREEN': 'valid_name', 'BLACK': 'no_records'})
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

# Species with at least one valid_name status across all genes
has_data = (base_df[status_cols] == 'valid_name').any(axis=1)
data_count = has_data.sum()
print(f"Species with at least one valid_name: {data_count}")

# Species with no_records across ALL genes (no data at all)
no_records_everywhere = (base_df[status_cols] == 'no_records').all(axis=1)
gap_count = no_records_everywhere.sum()
print(f"Species with no_records across all genes (true gaps): {gap_count}")

print(f"\n=== VALUES FOR WEBSITE ===")
print(f"Valid Species Assessed: {len(base_df)}")
print(f"Species with Data (at least one valid_name): {data_count}")
print(f"True Gaps (no_records everywhere): {gap_count}")
