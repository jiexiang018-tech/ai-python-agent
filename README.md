\# AI Code Agent



A local AI coding assistant that generates, executes, and auto-fixes Python code.

Powered by \[Qwen3-4B-Coder](https://huggingface.co/08210821iy/Qwen3-4B-Coder), a fine-tuned model trained by an elementary school student.



\## Features



\- Natural language to Python code generation

\- Automatic code execution with timeout protection

\- Auto-fix: detects errors and regenerates corrected code (up to N retries)

\- Fully offline after setup (no internet required)

\- Interactive CLI with command support



\## Requirements



\- Python 3.8+

\- \[Ollama](https://ollama.com/download) installed and running (`ollama serve`)



\## Quick Start



```bash

\# 1. Clone this repository

git clone https://github.com/jiexiang018-tech/ai-python-agent.git

cd ai-python-agent



\# 2. Install dependencies

pip install -r requirements.txt



\# 3. Run setup (downloads model ~2.3 GB)

python setup.py



\# 4. Start the agent

python agent.py



