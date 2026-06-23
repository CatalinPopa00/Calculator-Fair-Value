with open('api/macro_routes.py', 'r', encoding='utf-8') as f:
    backend = f.read()

# Replace the wrong route definition
backend = backend.replace(
    '@router.get("/api/read-article")',
    '@router.get("/read-article")'
)

with open('api/macro_routes.py', 'w', encoding='utf-8') as f:
    f.write(backend)

print("Route fixed")
