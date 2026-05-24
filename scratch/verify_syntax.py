import py_compile
import sys

try:
    py_compile.compile('index.py', doraise=True)
    print("SUCCESS: index.py compiled successfully with no syntax errors!")
except Exception as e:
    print("FAILED: syntax error detected in index.py:")
    print(e)
    sys.exit(1)
