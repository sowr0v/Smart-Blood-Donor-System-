import subprocess
import sys
import os

def main():
    print("Setting up Git hooks...")
    try:
        subprocess.check_call(["git", "config", "core.hooksPath", ".githooks"])
        print(" Successfully configured Git hooks path to '.githooks'")
        print(" Local commit-msg and pre-push hooks are now ACTIVE.")
        print(" Any commit or push with 'copilot' in author or message will be blocked automatically.")
    except Exception as e:
        print(f" Failed to configure Git hooks: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
