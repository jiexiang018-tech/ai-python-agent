"""AI Code Agent CLI - Local AI coding assistant powered by a fine-tuned Qwen3-4B model"""
import sys
import os
import re
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from code_executor import CodeExecutor

# ============================================================
# Config
# ============================================================
OLLAMA_BASE = "http://localhost:11434"
DEFAULT_MODEL = "qwen3-coder-v4"
FALLBACK_MODEL = "qwen3:4b"

SYSTEM_PROMPT = (
    "You are an expert Python programmer. "
    "Output ONLY valid Python code. "
    "Do NOT include any explanation, markdown formatting, or code fences. "
    "Do NOT include ``` markers. "
    "Just output the raw Python code that can be executed directly."
)


# ============================================================
# Colors
# ============================================================
class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"


# ============================================================
# LLM helpers (self-contained, no dependency on llm_backend.py)
# ============================================================
def get_model():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".model_config")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return f.read().strip()
    return DEFAULT_MODEL


def list_models():
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def strip_think(text):
    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)
    return text.strip()


def extract_code(text):
    text = strip_think(text)
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    cleaned = text.strip()
    if cleaned and ("def " in cleaned or "print(" in cleaned or "import " in cleaned
                     or "for " in cleaned or "class " in cleaned or "=" in cleaned):
        cleaned = re.sub(r"^```python\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        return cleaned.strip()
    return None


def chat(prompt, model, conversation=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation:
        messages.extend(conversation[-10:])
    messages.append({"role": "user", "content": prompt})
    try:
        r = requests.post(f"{OLLAMA_BASE}/api/chat", json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7, "top_p": 0.9}
        }, timeout=300)
        resp = r.json().get("message", {}).get("content", "")
        return True, resp
    except requests.ConnectionError:
        return False, "Cannot connect to Ollama. Run 'ollama serve' first."
    except Exception as e:
        return False, str(e)


# ============================================================
# UI helpers
# ============================================================
def print_banner(model):
    print(f"""{C.CYAN}{C.BOLD}
╔══════════════════════════════════════════╗
║         AI Code Agent  v4  CLI           ║
║   Local AI Coding Assistant (Offline)    ║
╚══════════════════════════════════════════╝{C.RESET}
{C.DIM}Model: {model} | Engine: Ollama{C.RESET}
{C.DIM}Type your request. Commands: /help for list{C.RESET}""")


def print_help():
    print(f"""{C.BOLD}Commands:{C.RESET}
  {C.CYAN}/run{C.RESET}            Re-run last code
  {C.CYAN}/save <path>{C.RESET}    Save last code to file
  {C.CYAN}/model{C.RESET}          Show/change model
  {C.CYAN}/auto on|off{C.RESET}    Toggle auto-execution (default: on)
  {C.CYAN}/max_fix <n>{C.RESET}    Set max auto-fix attempts (default: 3)
  {C.CYAN}/help{C.RESET}           Show this help
  {C.CYAN}/quit{C.RESET}           Exit

{C.BOLD}Usage:{C.RESET}
  Type a request in natural language.
  The AI generates Python code, executes it, and auto-fixes errors.""")


def print_code(code):
    lines = code.split("\n")
    w = len(str(len(lines)))
    for i, line in enumerate(lines, 1):
        print(f"  {C.DIM}{str(i).rjust(w)} |{C.RESET} {line}")


def print_result(success, stdout, stderr, elapsed):
    if success:
        print(f"\n{C.GREEN}{C.BOLD}[OK]{C.RESET} {C.DIM}({elapsed:.1f}s){C.RESET}")
        if stdout.strip():
            print(f"{C.GREEN}Output:{C.RESET}")
            for l in stdout.strip().split("\n"):
                print(f"  {l}")
    else:
        print(f"\n{C.RED}{C.BOLD}[ERROR]{C.RESET} {C.DIM}({elapsed:.1f}s){C.RESET}")
        if stderr.strip():
            print(f"{C.RED}Error:{C.RESET}")
            for l in stderr.strip().split("\n"):
                print(f"  {l}")
        if stdout.strip():
            print(f"{C.DIM}Output before error:{C.RESET}")
            for l in stdout.strip().split("\n"):
                print(f"  {l}")


def input_callback(prompt_text):
    try:
        return input(f"{C.YELLOW}[input] {prompt_text}{C.RESET}")
    except (EOFError, KeyboardInterrupt):
        return None


# ============================================================
# Main
# ============================================================
def main():
    model = get_model()
    executor = CodeExecutor(timeout=30)
    executor.set_input_callback(input_callback)
    conversation = []
    last_code = None
    auto_execute = True
    max_fix_attempts = 3

    print_banner(model)

    models = list_models()
    if not models:
        print(f"{C.RED}Error: Cannot connect to Ollama. Run 'ollama serve' first.{C.RESET}")
        return
    model_bases = [m.split(":")[0] for m in models]
    if model not in model_bases and model not in models:
        print(f"{C.YELLOW}Warning: Model '{model}' not found.{C.RESET}")
        print(f"{C.DIM}Available: {', '.join(models)}{C.RESET}")
        if FALLBACK_MODEL.split(":")[0] in model_bases or FALLBACK_MODEL in models:
            model = FALLBACK_MODEL
            print(f"{C.YELLOW}Using fallback: {model}{C.RESET}")

    while True:
        try:
            user_input = input(f"\n{C.GREEN}{C.BOLD}You > {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}Bye!{C.RESET}")
            break

        if not user_input:
            continue

        # Command handling
        if user_input.startswith("/"):
            cmd = user_input.lower().split()
            if cmd[0] == "/quit":
                print(f"{C.DIM}Bye!{C.RESET}")
                break
            if cmd[0] == "/help":
                print_help()
                continue
            if cmd[0] == "/run":
                if last_code:
                    print(f"\n{C.CYAN}Re-running last code...{C.RESET}")
                    s, o, e, t = executor.execute(last_code)
                    print_result(s, o, e, t)
                else:
                    print(f"{C.YELLOW}No code to run.{C.RESET}")
                continue
            if cmd[0] == "/save":
                if len(cmd) < 2:
                    print(f"{C.YELLOW}Usage: /save <filepath>{C.RESET}")
                elif last_code:
                    ok, msg = executor.save_code(last_code, cmd[1])
                    print(f"{C.GREEN if ok else C.RED}{msg}{C.RESET}")
                else:
                    print(f"{C.YELLOW}No code to save.{C.RESET}")
                continue
            if cmd[0] == "/model":
                if len(cmd) >= 2:
                    model = cmd[1]
                    print(f"{C.GREEN}Model set to: {model}{C.RESET}")
                else:
                    print(f"{C.CYAN}Current model: {model}{C.RESET}")
                    print(f"{C.DIM}Available: {', '.join(list_models())}{C.RESET}")
                continue
            if cmd[0] == "/auto":
                if len(cmd) >= 2 and cmd[1] in ("on", "off"):
                    auto_execute = cmd[1] == "on"
                    print(f"{C.GREEN}Auto-execution: {'ON' if auto_execute else 'OFF'}{C.RESET}")
                else:
                    print(f"{C.CYAN}Auto-execution: {'ON' if auto_execute else 'OFF'}{C.RESET}")
                continue
            if cmd[0] == "/max_fix":
                if len(cmd) >= 2 and cmd[1].isdigit():
                    max_fix_attempts = int(cmd[1])
                    print(f"{C.GREEN}Max fix attempts: {max_fix_attempts}{C.RESET}")
                else:
                    print(f"{C.CYAN}Max fix attempts: {max_fix_attempts}{C.RESET}")
                continue
            print(f"{C.YELLOW}Unknown command. Type /help{C.RESET}")
            continue

        # Send to LLM
        print(f"\n{C.MAGENTA}{C.BOLD}Agent >{C.RESET} {C.DIM}Thinking...{C.RESET}", end="\r", flush=True)
        ok, response = chat(user_input, model, conversation)

        if not ok:
            print(f"{C.RED}Error: {response}{C.RESET}")
            continue

        conversation.extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": response}
        ])
        if len(conversation) > 20:
            conversation = conversation[-20:]

        code = extract_code(response)

        if code:
            last_code = code
            print(f"{C.MAGENTA}{C.BOLD}Agent >{C.RESET} Here's the code:\n")
            print_code(code)

            if auto_execute:
                print(f"\n{C.CYAN}Executing...{C.RESET}")
                s, o, e, t = executor.execute(code)
                print_result(s, o, e, t)

                fix_attempt = 0
                while not s and fix_attempt < max_fix_attempts:
                    fix_attempt += 1
                    print(f"\n{C.YELLOW}Auto-fixing (attempt {fix_attempt}/{max_fix_attempts})...{C.RESET}")
                    fix_prompt = (
                        f"The code produced an error:\n```\n{e[:500]}\n```\n\n"
                        f"Original code:\n```python\n{code}\n```\n\n"
                        f"Fix the error. Output the complete corrected Python code only."
                    )
                    fix_ok, fix_resp = chat(fix_prompt, model, conversation)
                    if fix_ok:
                        fix_code = extract_code(fix_resp)
                        if fix_code:
                            code = fix_code
                            last_code = code
                            conversation.extend([
                                {"role": "user", "content": fix_prompt},
                                {"role": "assistant", "content": fix_resp}
                            ])
                            print(f"\n{C.MAGENTA}{C.BOLD}Agent >{C.RESET} Fixed code:\n")
                            print_code(code)
                            print(f"\n{C.CYAN}Re-executing...{C.RESET}")
                            s, o, e, t = executor.execute(code)
                            print_result(s, o, e, t)
                        else:
                            print(f"{C.RED}Could not extract code from fix.{C.RESET}")
                            break
                    else:
                        print(f"{C.RED}Could not generate fix.{C.RESET}")
                        break

                if not s and fix_attempt >= max_fix_attempts:
                    print(f"{C.RED}Max fix attempts reached.{C.RESET}")
        else:
            clean = strip_think(response)
            print(f"{C.MAGENTA}{C.BOLD}Agent >{C.RESET} {clean}")

    executor.cleanup()


if __name__ == "__main__":
    main()