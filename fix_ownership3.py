with open('app.js', 'r') as f:
    js = f.read()

js = js.replace("""// Only attempt to render chart if we have data to prevent errors
                    if (data.length === 0) return;
const labels = sortedRoster.map(r => r.name);
                    const data = sortedRoster.map(r => r.shares / 1000); // in thousands""", """const labels = sortedRoster.map(r => r.name);
                    const data = sortedRoster.map(r => r.shares / 1000); // in thousands
                    // Only attempt to render chart if we have data to prevent errors
                    if (data.length === 0) return;""")

with open('app.js', 'w') as f:
    f.write(js)
