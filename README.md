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

git clone https://github.com/jiexiang018-tech/ai-python-agent.git

cd ai-python-agent

pip install -r requirements.txt

python setup.py

python agent.py

```　

