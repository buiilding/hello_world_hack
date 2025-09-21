# CoAct-1 Example: Multi-Agent Computer Automation

This repo contains a runnable example of the CoAct-1 multi-agent system (Orchestrator, Programmer, GUI Operator) that automates tasks on a virtual Linux desktop via Docker.

## Prerequisites (all OSes)
- Install Miniconda (or Anaconda)
- Install Docker and ensure it is running
  - Windows/macOS: Docker Desktop
  - Linux: Docker Engine
- Have a Google API key for Gemini models
  - Set environment variable: `GOOGLE_API_KEY`

## Quick Start

### 1) Create a Conda environment (Python 3.12)
```bash
conda create -n cua python==3.12 -y
conda activate cua
```

### 2) Install dependencies
Use pip to install from `requirements.txt`:
```bash
pip install -r requirements.txt
```

- If there is a build error on Windows, install "Visual Studio Build Tools (C++)" and retry.
- On Linux, it generally works well.

Optional: If you want GPU acceleration for local vision models (e.g., InternVL), install a CUDA-enabled PyTorch build. For CPU-only you can skip this.
- CPU-only (works everywhere, slower):
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```
- Example CUDA 12.1 build (if you have an NVIDIA GPU with CUDA setup):
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3) Set your environment variables
Make sure your Google API key is available to the process.
- macOS/Linux (bash/zsh):
```bash
export GOOGLE_API_KEY="YOUR_KEY_HERE"
```
- Windows (PowerShell):
```powershell
setx GOOGLE_API_KEY "YOUR_KEY_HERE"
# Then open a new terminal so the change takes effect
```

- Windows (CMD):
```bat
setx GOOGLE_API_KEY "YOUR_KEY_HERE"
rem Close this window and open a new terminal so the change takes effect
```

Verify that the variable is set before running the script:
- macOS/Linux (bash/zsh):
```bash
echo $GOOGLE_API_KEY | sed 's/.\{6\}$/******/'
```
- Windows (PowerShell):
```powershell
echo $Env:GOOGLE_API_KEY.Substring(0, [Math]::Min(6, $Env:GOOGLE_API_KEY.Length)) + "******"
```
- Windows (CMD):
```bat
echo %GOOGLE_API_KEY%
```

### 4) Run the example
From the repo root (this directory):
```bash
python coact_1_example.py
```
The script will:
- Start a Docker-based Linux desktop VM (`trycua/cua-ubuntu:latest`)
- Initialize CoAct-1 agents (Orchestrator, Programmer, GUI Operator)
- Execute the example task

## Notes and Troubleshooting
- Docker must be installed and running before you start the script.
  - Windows users: Ensure WSL 2 backend is enabled for Docker Desktop.
- If `GOOGLE_API_KEY` is missing, the script will exit early.
- If you see errors regarding InternVL dependencies and you intend to use the local InternVL-based GUI Operator, ensure the extra dependencies are installed:
```bash
pip install "cua-agent[internvl-hf]"
```
- To avoid using InternVL locally, you can switch the GUI Operator model in `coact_1_example.py` to a Gemini-only configuration.
- Windows build errors during `pip install`: install "Visual Studio Build Tools (C++)" and retry.

## Development
- Create a new branch for changes:
```bash
git checkout -b my-feature-branch
```
- Commit and push:
```bash
git add .
git commit -m "Describe your change"
git push -u origin my-feature-branch
```

## License
This repository is for demo and hackathon use.
