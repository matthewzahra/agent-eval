import wexpect
import warnings

# Ignore harmless wexpect warnings
warnings.filterwarnings("ignore", category=UserWarning, module="wexpect")

# Path to your Gemini CLI
GEMINI_PATH = r"C:/Users/matth/AppData/Roaming/npm/gemini"

# Start Gemini
child = wexpect.spawn(GEMINI_PATH)

print("GEMINI CLI started. Type your commands. Type 'exit' to quit.\n")

try:
    # Print initial output from Gemini (welcome message)
    while True:
        index = child.expect([r">", wexpect.EOF], timeout=1)
        print(child.before, end="")  # print everything up to the prompt
        if index == 0:  # prompt detected
            break
        elif index == 1:  # EOF
            break

    while True:
        # Read user input
        cmd = input()
        if cmd.strip().lower() == "exit":
            child.sendline("exit")
            break

        # Send command to Gemini
        child.sendline(cmd)

        # Print Gemini output until next prompt or EOF
        while True:
            index = child.expect([r">", wexpect.EOF])
            print(child.before, end="")
            if index == 0:  # prompt detected
                break
            elif index == 1:  # EOF
                break

finally:
    child.expect(wexpect.EOF)  # ensure Gemini exits cleanly
    child.close()
    print("\nGEMINI CLI session ended.")
