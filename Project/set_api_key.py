import os
import platform
import sys

def set_env_variable(var_value):
    system = platform.system()

    if os.getenv('GEMINI_API_KEY'):
        print("GEMINI_API_KEY is already set!")
        return

    if system == "Windows":
        command = f"setx GEMINI_API_KEY \"{var_value}\""
        os.system(command)
        print("GEMINI_API_KEY has been set successfully!")
        print("Note: Please restart your terminal or application to apply the changes.")

    elif system in ["Linux", "Darwin"]:
        escaped_value = var_value.replace("'", "'\\''")

        shell_config = os.path.expanduser("~/.bashrc" if os.getenv("SHELL", "").endswith("bash") else "~/.zshrc")

        with open(shell_config, "a") as f:
            f.write(f"\nexport GEMINI_API_KEY='{escaped_value}'\n")

        print(f"GEMINI_API_KEY has been set successfully on {system}!")
        print(f"Note: Please run 'source {shell_config}' or restart your terminal to apply the changes.")

    else:
        print(f"Unsupported operating system: {system}")
        return

def main():
    api_key = input("Please enter your Gemini API key: ").strip()
    if not api_key:
        print("API key cannot be empty!")
        return

    set_env_variable(api_key)

if __name__ == "__main__":
    main()
