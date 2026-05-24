def search_in_file(filepath, keywords):
    print(f"=== Searching in {filepath} ===")
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        for kw in keywords:
            if kw.lower() in line.lower():
                print(f"Line {i+1}: {line.strip()[:100]}")

search_in_file("app.js", ["watchlist", "fcf-source", "dcf-years-source", "dcf-method-selector", "customWeights"])
