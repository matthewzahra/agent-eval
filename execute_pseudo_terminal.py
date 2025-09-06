import os
import pty
import subprocess
import time
import select

# Create a pseudo-terminal
master_fd, slave_fd = pty.openpty()

# Start gemini with the slave end of the pty
proc = subprocess.Popen(
    ['gemini'],
    stdin=slave_fd,
    stdout=slave_fd,
    stderr=slave_fd,
    text=True
)

# Close the slave FD in the parent
os.close(slave_fd)

# Function to write to gemini
def write_to_gemini(cmd):
    os.write(master_fd, (cmd + '\r').encode())

# Function to read gemini output (non-blocking)
def read_from_gemini(timeout=1):
    output = b''
    end_time = time.time() + timeout
    while time.time() < end_time:
        rlist, _, _ = select.select([master_fd], [], [], 0.1)
        if master_fd in rlist:
            chunk = os.read(master_fd, 1024)
            if not chunk:
                break
            output += chunk
    return output.decode()

# Example usage
time.sleep(5)  # give gemini a moment to start
write_to_gemini('tell me a joke')
output = read_from_gemini()
print('Gemini output:\n', output)

# You can continue writing and reading commands like this:
write_to_gemini('version')
time.sleep(0.5)
print(read_from_gemini())

# When done, terminate gemini
proc.terminate()
proc.wait()
