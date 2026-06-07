import re

with open('scraper/yahoo.py', 'r') as f:
    content = f.read()

# 1. Initialize gaap_eps_fy at the start of get_company_data to prevent UnboundLocalError
content = content.replace("gaap_eps = (net_inc * fx_rate) / shares_outstanding", "gaap_eps = (net_inc * fx_rate) / shares_outstanding\n                            gaap_eps_fy = gaap_eps")

# Look where trailing_eps is defined
content = content.replace(
    "adjusted_eps = 0\n    forward_eps = 0",
    "adjusted_eps = 0\n    gaap_eps_fy = None\n    forward_eps = 0"
)

# 2. Fix the regex. To avoid the issue where 'low' is inside 'avg', we can match the literal structure more tightly.
# Instead of `re.search(r'low(?:\"|\\"):\{[^{}]*?raw(?:\"|\\"):([\d\.\-]+)', sub_chunk)`, we can specify we want the 'earningsEstimate' block by splitting the sub_chunk if needed, but since it's regex we can write:
# We know the JSON has `"earningsEstimate":{"avg":{"raw":32.20799,"fmt":"32.21"},"low":{"raw":27.76,"fmt":"27.76"},"high":{"raw":38.62,"fmt":"38.62"}}`
# So we can match `earningsEstimate` followed by anything, then `low`... but not going past the `}` of earningsEstimate.
# However, python regex with `.*?` could go past.
# Let's extract the `earningsEstimate` dictionary string first.

# We will just rewrite the python code doing the regex in `get_yahoo_analysis_normalized`.
