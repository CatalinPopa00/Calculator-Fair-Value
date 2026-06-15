import io

with io.open('api/index.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Update CACHE_VERSION
text = text.replace('CACHE_VERSION = "v319"', 'CACHE_VERSION = "v320"')

# Update KV cache keys
text = text.replace('val_data_v35_', 'val_data_v36_')

with io.open('api/index.py', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Updated cache keys to v36 and v320")
