import os
import sys

try:
    os.system(f"{sys.executable} {os.path.join(os.getcwd(), 'run.py')} {' '.join(sys.argv[1:])}")
except KeyboardInterrupt:
    sys.exit(0)
except Exception as e:
    raise e
