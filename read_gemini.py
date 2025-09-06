import subprocess

process = subprocess.Popen(
    ["C:/Users/matth/AppData/Roaming/npm/gemini.cmd"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=0  # unbuffered
)

def send_command(cmd):
    process.stdin.write(cmd + "\n")
    process.stdin.flush()

    output = []
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        output.append(line)
        if line.endswith(">"):  # adjust to Gemini's prompt
            break
    return "\n".join(output)

print(send_command("help"))

process.stdin.write("exit\n")
process.stdin.flush()
process.terminate()
