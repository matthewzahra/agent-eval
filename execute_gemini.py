import subprocess
import sys

import subprocess
import sys
import time

# Start gemini with stdin/stdout/stderr attached to the terminal
proc = subprocess.Popen(['gemini'], stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)

# Meanwhile, Python writes to stdout
for i in range(5):
    print(f'Python says hello {i}')
    sys.stdout.flush()  # make sure it actually appears
    time.sleep(1)

# Wait for gemini to finish
proc.wait()
