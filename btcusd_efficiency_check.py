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
    
    # Filter out blown accounts (PercentDD >= 100)
    df_safe = df_pair[df_pair['PercentDD'] < 100].copy()
    
    if df_safe.empty:
        results.append({'Pair': pair, 'Trend': 'UNSAFE', 'Corr': 0, 'BE_2_Eff': 0, 'BE_5_Eff': 0})
        continue

    # Calculate Efficiency (Profit per 1% DD)
    df_safe['Efficiency'] = df_safe['Profit'] / df_safe['PercentDD']
    
    # Group by CloseBreakEvenAfter (BE)
    be_analysis = df_safe.groupby('CloseBreakEvenAfter').agg({'Efficiency': 'mean'}).reset_index()
    
    if len(be_analysis) > 1:
        corr = be_analysis['CloseBreakEvenAfter'].corr(be_analysis['Efficiency'])
        eff_2 = be_analysis[be_analysis['CloseBreakEvenAfter'] == 2]['Efficiency'].values[0] if 2 in be_analysis['CloseBreakEvenAfter'].values else 0
        eff_5 = be_analysis[be_analysis['CloseBreakEvenAfter'] == 5]['Efficiency'].values[0] if 5 in be_analysis['CloseBreakEvenAfter'].values else 0
        
        trend = "LATE BE" if corr > 0.2 else ("EARLY BE" if corr < -0.2 else "NEUTRAL")
        results.append({
            'Pair': pair, 
            'Trend': trend, 
            'Corr': corr, 
            'BE_2_Eff': eff_2, 
            'BE_5_Eff': eff_5,
            'Diff_%': ((eff_5 - eff_2) / eff_2 * 100) if eff_2 != 0 else 0
        })

summary_df = pd.DataFrame(results)
print("\nGlobal Efficiency Analysis: Late vs Early Break-Even")
print("======================================================")
print(summary_df.sort_values('Diff_%', ascending=False).to_string(index=False))

print("\n--- Summary ---")
print(f"Pairs benefitting from LATE BE (Stay in): {len(summary_df[summary_df['Trend'] == 'LATE BE'])}")
print(f"Pairs benefitting from EARLY BE (Exit quick): {len(summary_df[summary_df['Trend'] == 'EARLY BE'])}")
print(f"Neutral Pairs: {len(summary_df[summary_df['Trend'] == 'NEUTRAL'])}")
