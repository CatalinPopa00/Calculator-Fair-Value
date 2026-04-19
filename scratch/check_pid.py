import psutil
try:
    p = psutil.Process(8560)
    print(f"CWD: {p.cwd()}")
except Exception as e:
    print(f"Error: {e}")
