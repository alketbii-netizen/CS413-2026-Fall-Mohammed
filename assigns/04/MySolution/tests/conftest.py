import os
import sys

# Make sure `import lambdaweb` works regardless of the directory pytest is
# invoked from, without requiring the package to be pip-installed.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
