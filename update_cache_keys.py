import io
import re

with io.open('api/index.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Update CACHE_VERSION
text = text.replace('CACHE_VERSION = "v318"', 'CACHE_VERSION = "v319"')

# Update KV cache keys
text = text.replace('val_data_v34_', 'val_data_v35_')

with io.open('api/index.py', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Updated cache keys to v35 and v319")
