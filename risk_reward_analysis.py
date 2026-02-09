import pandas as pd
import numpy as np

def decode_result(val):
    try:
        packed = int(val)
        C = packed % 100
        B = (packed // 100) % 10000
        A = packed // 1000000
        return pd.Series({'Duration': A / 10.0, 'DrawdownVal': B / 10.0, 'ReEntries': C})
    except:
        return pd.Series({'Duration': 0.0, 'DrawdownVal': 0.0, 'ReEntries': 0.0})

# Load the data
df = pd.read_csv('ZMarti_ReEntry_PT_BE_Optimizations.csv')
all_pairs = sorted(df['Pair'].unique())

results = []

for pair in all_pairs:
    df_pair = df[df['Pair'] == pair].copy()
    
    # Decode columns
    decoded = df_pair['Result'].apply(decode_result)
    df_pair = pd.concat([df_pair.reset_index(drop=True), decoded.reset_index(drop=True)], axis=1)
    
    # Analyse by BE setting
    for be in [2, 5]:
        be_subset = df_pair[df_pair['CloseBreakEvenAfter'] == be].copy()
        if be_subset.empty: continue
        
        total_combos = len(be_subset)
        blown_combos = len(be_subset[be_subset['PercentDD'] >= 100])
        survival_rate = ((total_combos - blown_combos) / total_combos) * 100
        
        safe_combos = be_subset[be_subset['PercentDD'] < 100]
        avg_eff = safe_combos['Profit'].mean() / safe_combos['PercentDD'].mean() if not safe_combos.empty else 0
        
        results.append({
            'Pair': pair,
            'BE': be,
            'Survival_%': survival_rate,
            'Efficiency': avg_eff
        })

# Format for comparison
res_df = pd.DataFrame(results)
pivot_df = res_df.pivot(index='Pair', columns='BE', values=['Survival_%', 'Efficiency'])
pivot_df.columns = [f'{c[0]}_{c[1]}' for c in pivot_df.columns]

# Calculate "Danger" as the drop in survival rate
pivot_df['Survival_Drop_%'] = pivot_df['Survival_%_2'] - pivot_df['Survival_%_5']
pivot_df['Efficiency_Gain_%'] = ((pivot_df['Efficiency_5'] - pivot_df['Efficiency_2']) / pivot_df['Efficiency_2'] * 100)

pivot_df = pivot_df.reset_index()

print("Risk vs Reward: Staying in (BE=5) vs Exiting Early (BE=2)")
print("==========================================================")
print("Survival_Drop: How many 'safe' configurations we lose when staying until 5.")
print("Efficiency_Gain: How much more profit we get per unit of risk.")
print("----------------------------------------------------------")

# Categorize
def categorize(row):
    if row['Survival_Drop_%'] > 20: return "EXTREMELY DANGEROUS"
    if row['Survival_Drop_%'] > 5: return "RISKY"
    if row['Efficiency_Gain_%'] < 0: return "POINTLESS (Lower Eff)"
    return "RELATIVELY STABLE"

pivot_df['Risk_Category'] = pivot_df.apply(categorize, axis=1)

cols_to_show = ['Pair', 'Survival_%_2', 'Survival_%_5', 'Survival_Drop_%', 'Efficiency_Gain_%', 'Risk_Category']
print(pivot_df[cols_to_show].sort_values('Survival_Drop_%', ascending=False).to_string(index=False))

print("\n--- Summary of Findings ---")
print(f"Total Pairs: {len(pivot_df)}")
print(f"Extremely Dangerous Pairs (Survival drops > 20%): {len(pivot_df[pivot_df['Risk_Category'] == 'EXTREMELY DANGEROUS'])}")
print(f"Pointless Pairs (Efficiency actually drops): {len(pivot_df[pivot_df['Risk_Category'] == 'POINTLESS (Lower Eff)'])}")
print(f"Sweet Spot Pairs (High Gain, Low Survival Drop): {len(pivot_df[(pivot_df['Efficiency_Gain_%'] > 20) & (pivot_df['Survival_Drop_%'] < 5)])}")
