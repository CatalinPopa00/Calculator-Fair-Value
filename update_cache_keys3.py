import io

with io.open('api/index.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Update CACHE_VERSION
text = text.replace('CACHE_VERSION = "v320"', 'CACHE_VERSION = "v321"')

# Update KV cache keys
text = text.replace('val_data_v36', 'val_data_v37')
text = text.replace('synth_v36', 'synth_v37')
text = text.replace('info_v36', 'info_v37')

with io.open('api/index.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated cache keys to v37 and v321")
