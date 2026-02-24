"""
AI Code Agent - Setup Script
Downloads the fine-tuned model from HuggingFace and registers it with Ollama.
"""
import os
import sys
import subprocess
import urllib.request
import shutil
import tempfile

MODEL_NAME = "qwen3-coder-v4"
HF_REPO = "08210821iy/Qwen3-4B-Coder"
GGUF_FILE = "model-q4_k_m.gguf"
GGUF_URL = f"https://huggingface.co/{HF_REPO}/resolve/main/{GGUF_FILE}"
FALLBACK_MODEL = "qwen3:4b"

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
GGUF_PATH = os.path.join(MODEL_DIR, GGUF_FILE)

MODELFILE_CONTENT = """FROM {gguf_path}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop <|im_end|>
PARAMETER num_ctx 2048

TEMPLATE \"\"\"<|im_start|>system
{{{{ .System }}}}<|im_end|>
<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
<|im_start|>assistant
\"\"\"
"""


class C:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def check_ollama():
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


def check_model_exists():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        return MODEL_NAME in result.stdout
    except Exception:
        return False


def download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded / total_size * 100, 100)
        mb_done = downloaded / 1024 / 1024
        mb_total = total_size / 1024 / 1024
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  {C.CYAN}[{bar}] {pct:.1f}% ({mb_done:.0f}/{mb_total:.0f} MB){C.RESET}", end="", flush=True)


def download_gguf():
    os.makedirs(MODEL_DIR, exist_ok=True)
    if os.path.exists(GGUF_PATH):
        size_gb = os.path.getsize(GGUF_PATH) / 1024 / 1024 / 1024
        print(f"  {C.GREEN}Model already downloaded ({size_gb:.2f} GB){C.RESET}")
        return True
    print(f"  {C.CYAN}Downloading model from HuggingFace...{C.RESET}")
    print(f"  {C.DIM}{GGUF_URL}{C.RESET}")
    print(f"  {C.DIM}Size: ~2.33 GB (may take 5-10 minutes){C.RESET}")
    try:
        urllib.request.urlretrieve(GGUF_URL, GGUF_PATH, reporthook=download_progress)
        print()
        size_gb = os.path.getsize(GGUF_PATH) / 1024 / 1024 / 1024
        print(f"  {C.GREEN}Download complete ({size_gb:.2f} GB){C.RESET}")
        return True
    except Exception as e:
        print(f"\n  {C.RED}Download failed: {e}{C.RESET}")
        if os.path.exists(GGUF_PATH):
            os.remove(GGUF_PATH)
        return False


def register_model():
    if check_model_exists():
        print(f"  {C.GREEN}Model '{MODEL_NAME}' already registered in Ollama{C.RESET}")
        return True
    print(f"  {C.CYAN}Registering model with Ollama...{C.RESET}")
    content = MODELFILE_CONTENT.format(gguf_path=GGUF_PATH.replace("\\", "/"))
    modelfile_path = os.path.join(MODEL_DIR, "Modelfile")
    with open(modelfile_path, "w", encoding="utf-8") as f:
        f.write(content)
    try:
        result = subprocess.run(
            ["ollama", "create", MODEL_NAME, "-f", modelfile_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print(f"  {C.GREEN}Model '{MODEL_NAME}' registered successfully{C.RESET}")
            return True
        else:
            print(f"  {C.RED}Registration failed: {result.stderr}{C.RESET}")
            return False
    except Exception as e:
        print(f"  {C.RED}Registration failed: {e}{C.RESET}")
        return False


def setup_fallback():
    print(f"  {C.YELLOW}Falling back to official model: {FALLBACK_MODEL}{C.RESET}")
    print(f"  {C.CYAN}Pulling {FALLBACK_MODEL}...{C.RESET}")
    try:
        result = subprocess.run(
            ["ollama", "pull", FALLBACK_MODEL],
            timeout=600
        )
        if result.returncode == 0:
            print(f"  {C.GREEN}Fallback model ready{C.RESET}")
            return FALLBACK_MODEL
        return None
    except Exception:
        return None


def main():
    print(f"\n{C.BOLD}{C.CYAN}╔══════════════════════════════════════╗")
    print(f"║     AI Code Agent - Setup            ║")
    print(f"╚══════════════════════════════════════╝{C.RESET}\n")

    # Step 1: Check Ollama
    print(f"{C.BOLD}[1/3] Checking Ollama...{C.RESET}")
    if not check_ollama():
        print(f"  {C.RED}Ollama not found!{C.RESET}")
        print(f"  {C.YELLOW}Install Ollama from: https://ollama.com/download{C.RESET}")
        print(f"  {C.YELLOW}Then run 'ollama serve' and try setup again.{C.RESET}")
        sys.exit(1)
    print(f"  {C.GREEN}Ollama is installed{C.RESET}")

    # Step 2: Download model
    print(f"\n{C.BOLD}[2/3] Downloading model...{C.RESET}")
    model_name = MODEL_NAME
    if not download_gguf():
        print(f"  {C.YELLOW}Custom model download failed.{C.RESET}")
        fallback = setup_fallback()
        if fallback:
            model_name = fallback
        else:
            print(f"  {C.RED}No model available. Check your internet connection.{C.RESET}")
            sys.exit(1)
    else:
        # Step 3: Register with Ollama
        print(f"\n{C.BOLD}[3/3] Registering model...{C.RESET}")
        if not register_model():
            print(f"  {C.YELLOW}Registration failed. Trying fallback...{C.RESET}")
            fallback = setup_fallback()
            if fallback:
                model_name = fallback
            else:
                print(f"  {C.RED}Setup failed.{C.RESET}")
                sys.exit(1)

    # Save config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".model_config")
    with open(config_path, "w") as f:
        f.write(model_name)

    print(f"\n{C.GREEN}{C.BOLD}Setup complete!{C.RESET}")
    print(f"  Model: {C.CYAN}{model_name}{C.RESET}")
    print(f"\n  Run the agent with:")
    print(f"  {C.BOLD}python agent.py{C.RESET}\n")


if __name__ == "__main__":
    main()