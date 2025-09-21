# CoAct-1 Hackathon UI

> **⚠️ DEVELOPMENT NOTICE**: This is a work-in-progress prototype developed during a hackathon. Features may be unstable, incomplete, or subject to change. Use at your own risk!

A React-based web interface for the CoAct-1 Multi-Agent Computer Automation System. Watch AI agents coordinate in real-time to execute complex computer tasks through a live-streaming CLI interface.

## Prerequisites

Before running the UI, ensure you have:

- **Node.js 18+** and npm
- **Python 3.8+** with conda/miniconda installed
- **Docker** (for the CoAct-1 computer automation backend)
- **GOOGLE_API_KEY** environment variable set (for Gemini API access)
- **cua-env conda environment** (see main project setup)

### Environment Setup

1. **Clone the main repository:**
   ```bash
   git clone https://github.com/buiilding/hello_world_hack
   cd hello_world_hack
   ```

2. **Set up the cua-env conda environment:**
   ```bash
   # Follow the main project README for conda environment setup
   conda activate cua-env
   ```

3. **Set your Google API key:**
   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key-here"
   ```

## Quick Start

1. **Navigate to the UI directory:**
   ```bash
   cd hackathon-ui
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development servers:**
   ```bash
   npm run dev:full
   ```

   This starts both:
   - Backend API server (port 3001)
   - Frontend React app (port 8006)

## Running the Example

1. **Open your browser** to `http://localhost:8006`
2. **Enter a task** in the input field (e.g., "Go to Amazon and find the cheapest laptop")
3. **Watch the agent in action** - the CoAct-1 multi-agent system will execute your task with real-time CLI output streaming directly in the browser!

The system will automatically open the browser when you submit a task, showing you the live execution of the CoAct-1 agents as they coordinate to complete your request.

## Alternative: Run separately

**Backend API (for CoAct-1 execution):**
```bash
npm run server
```

**Frontend React App:**
```bash
npm run dev
```

## How it works

When you submit a task in the UI:

1. The frontend sends a POST request to `/api/run-coact` with your message
2. The backend automatically opens a browser to `localhost:8006` to show progress
3. The backend executes `python coact_1_example.py -m "your message"` with cua-env activated
4. **Real-time streaming**: All stdout/stderr output is streamed live to the browser via Server-Sent Events
5. The CoAct-1 multi-agent system runs with your specified task
6. Results are displayed in real-time in the browser window with live CLI output

## Troubleshooting

### Common Issues

**Port 8006 already in use:**
- The frontend may default to port 8007 if 8006 is busy
- Check the terminal output for the actual port being used

**"CondaError: Run 'conda init' before 'conda activate'"**
- Make sure you've properly initialized conda in your shell
- Try: `conda init bash` and restart your terminal

**"GOOGLE_API_KEY not set"**
- Ensure the environment variable is exported: `export GOOGLE_API_KEY="your-key"`
- Add it to your shell profile for persistence

**Python process fails to start:**
- Verify you're in the cua-env conda environment
- Check that all Python dependencies are installed in cua-env
- Ensure Docker is running (needed for CoAct-1)

**Browser doesn't open automatically:**
- Check if `xdg-open` is available on your system
- Manually navigate to `http://localhost:8006`

**Real-time output not updating:**
- Check browser console for SSE connection errors
- Ensure both backend (3001) and frontend (8006) are running
- Try refreshing the page

### Development Commands

**Run only the backend:**
```bash
npm run server
```

**Run only the frontend:**
```bash
npm run dev
```

**Run both servers concurrently:**
```bash
npm run dev:full
```

**Check if ports are available:**
```bash
lsof -i :3001  # Backend
lsof -i :8006  # Frontend
```

## Architecture

- **Frontend (React + TypeScript)**: Web interface with real-time display
- **Backend (Node.js + Express)**: API server with Server-Sent Events for streaming
- **CoAct-1 System (Python)**: Multi-agent computer automation framework
- **Docker**: Isolated computer environment for safe automation

## Contributing

This is a hackathon prototype - contributions welcome! Please check the main repository for CoAct-1 system contributions.

## License

See main project LICENSE file.
