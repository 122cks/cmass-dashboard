import pandas as pd

# Sample distributor_market with official names
distributor_market = pd.DataFrame({
    '총판명(공식)': ['통영)이문당', '이문당', 'ABC총판', 'XYZ(지사)'],
    '시장규모': [1000, 800, 500, 300]
})

# Sample order_df with various distributor display names
order_df = pd.DataFrame({
    '총판': ['통영)이문당', '통영) 이문당', '이문당', 'ABC총판', 'XYZ'],
    '부수': [100, 50, 80, 40, 20]
})

patterns = ['통영)이문당', '통영) 이문당', '이문당', 'XYZ']

for dist in patterns:
    pattern = dist.split(')')[-1] if ')' in dist else dist
    # using literal match (regex=False)
    matches = distributor_market[distributor_market['총판명(공식)'].str.contains(pattern, na=False, regex=False)]
    print(f"Dist: {dist!r} -> pattern: {pattern!r} -> matches:\n{matches}\n")

# Also test when using regex (should behave similar for simple strings)
for dist in patterns:
    pattern = dist.split(')')[-1] if ')' in dist else dist
    matches_re = distributor_market[distributor_market['총판명(공식)'].str.contains(pattern, na=False, regex=True)]
    print(f"(regex) Dist: {dist!r} -> pattern: {pattern!r} -> matches:\n{matches_re}\n")
