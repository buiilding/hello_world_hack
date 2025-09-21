# CoAct-1 Hackathon UI

A React-based UI for the CoAct-1 Multi-Agent Computer Automation System.

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment variables:**
   Make sure `GOOGLE_API_KEY` is set in your environment for the CoAct-1 system to work.

3. **Run the full system:**
   ```bash
   npm run dev:full
   ```

   This will start both the backend API server (port 3001) and the frontend React app (port 8006).

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

## Requirements

- Node.js and npm
- Python 3.x with required dependencies (see main project README)
- GOOGLE_API_KEY environment variable set
- Docker (for the CoAct-1 system)
- cua-env conda environment activated for the backend server
