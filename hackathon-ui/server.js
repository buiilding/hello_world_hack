import express from 'express';
import { spawn } from 'child_process';
import path from 'path';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';

// Store active connections for real-time updates
const activeConnections = new Map();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

// Enable CORS
app.use(cors());
app.use(express.json());

// SSE endpoint for real-time updates
app.get('/api/stream/:taskId', (req, res) => {
  const { taskId } = req.params;

  // Set SSE headers
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Cache-Control',
  });

  // Send initial connection message
  res.write(`data: ${JSON.stringify({ type: 'connected', taskId })}\n\n`);

  // Store the connection
  activeConnections.set(taskId, res);

  // Handle client disconnect
  req.on('close', () => {
    activeConnections.delete(taskId);
  });
});

// Helper function to send SSE updates
function sendSSEUpdate(taskId, data) {
  const connection = activeConnections.get(taskId);
  if (connection) {
    connection.write(`data: ${JSON.stringify(data)}\n\n`);
  }
}

// API endpoint to run CoAct-1 script
app.post('/api/run-coact', (req, res) => {
  const { message } = req.body;

  if (!message) {
    return res.status(400).json({ error: 'Message is required' });
  }

  // Generate unique task ID
  const taskId = Date.now().toString() + Math.random().toString(36).substr(2, 9);
  console.log(`🔄 Running CoAct-1 with message: "${message}" (Task ID: ${taskId})`);

  // Send task started update
  sendSSEUpdate(taskId, {
    type: 'started',
    message: `Starting CoAct-1 execution: "${message}"`,
    timestamp: new Date().toISOString()
  });

  // Open browser to localhost:8006
  exec('xdg-open http://localhost:8006', (error) => {
    if (error) {
      console.log('Could not open browser automatically:', error.message);
      sendSSEUpdate(taskId, {
        type: 'info',
        message: 'Could not open browser automatically',
        timestamp: new Date().toISOString()
      });
    } else {
      console.log('✅ Opened browser to localhost:8006');
      sendSSEUpdate(taskId, {
        type: 'info',
        message: 'Browser opened to localhost:8006',
        timestamp: new Date().toISOString()
      });
    }
  });

  // Path to the Python script (assuming it's in the parent directory)
  const scriptPath = path.join(__dirname, '..', 'coact_1_example.py');

  // Use the full path to python in the cua-env environment
  const pythonExecutable = '/home/peter/miniconda3/envs/cua-env/bin/python';

  // Spawn Python process directly with the cua-env python
  const pythonProcess = spawn(pythonExecutable, [scriptPath, '-m', message], {
    cwd: path.join(__dirname, '..'), // Run from project root
    stdio: ['pipe', 'pipe', 'pipe']
  });

  let output = '';
  let errorOutput = '';

  // Collect stdout and send real-time updates
  pythonProcess.stdout.on('data', (data) => {
    const chunk = data.toString();
    console.log('STDOUT:', chunk);
    output += chunk;

    // Send stdout to client in real-time
    sendSSEUpdate(taskId, {
      type: 'stdout',
      data: chunk,
      timestamp: new Date().toISOString()
    });
  });

  // Collect stderr and send real-time updates
  pythonProcess.stderr.on('data', (data) => {
    const chunk = data.toString();
    console.error('STDERR:', chunk);
    errorOutput += chunk;

    // Send stderr to client in real-time
    sendSSEUpdate(taskId, {
      type: 'stderr',
      data: chunk,
      timestamp: new Date().toISOString()
    });
  });

  // Handle process completion
  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);

    // Send completion update
    sendSSEUpdate(taskId, {
      type: 'completed',
      code: code,
      success: code === 0,
      timestamp: new Date().toISOString()
    });

    // Close the SSE connection after a delay
    setTimeout(() => {
      const connection = activeConnections.get(taskId);
      if (connection) {
        connection.end();
        activeConnections.delete(taskId);
      }
    }, 1000);

    if (code === 0) {
      res.json({
        success: true,
        taskId: taskId,
        output: output,
        message: 'CoAct-1 script completed successfully'
      });
    } else {
      res.status(500).json({
        success: false,
        taskId: taskId,
        error: errorOutput || 'Script execution failed',
        output: output
      });
    }
  });

  // Handle process errors
  pythonProcess.on('error', (error) => {
    console.error('Failed to start Python process:', error);
    sendSSEUpdate(taskId, {
      type: 'error',
      message: `Failed to start Python process: ${error.message}`,
      timestamp: new Date().toISOString()
    });

    res.status(500).json({
      success: false,
      taskId: taskId,
      error: `Failed to start Python process: ${error.message}`
    });
  });
});

app.listen(PORT, () => {
  console.log(`🚀 CoAct-1 API server running on port ${PORT}`);
});
