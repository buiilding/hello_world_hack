import React, { useState, useEffect, useRef } from 'react';
import { Zap, Brain } from 'lucide-react';
import TaskInput from './components/TaskInput';

function App() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentTask, setCurrentTask] = useState('');
  const [result, setResult] = useState<string>('');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  // Execute CoAct-1 automation workflow
  const runCoActAutomation = async (task: string) => {
    setIsRunning(true);
    setCurrentTask(task);
    setResult('Starting CoAct-1 execution...\n');

    // Close any existing event source
    if (eventSource) {
      eventSource.close();
    }

    try {
      // Call the CoAct-1 API
      const response = await fetch('http://localhost:3001/api/run-coact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: task }),
      });

      const apiResult = await response.json();

      if (!apiResult.success) {
        throw new Error(apiResult.error || 'CoAct-1 execution failed');
      }

      // Store the task ID and establish SSE connection
      const currentTaskId = apiResult.taskId;
      setTaskId(currentTaskId);

      // Connect to SSE stream
      const newEventSource = new EventSource(`http://localhost:3001/api/stream/${currentTaskId}`);
      setEventSource(newEventSource);

      newEventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'connected':
              setResult(prev => prev + `🔗 Connected to execution stream\n`);
              break;
            case 'started':
              setResult(prev => prev + `🚀 ${data.message}\n`);
              break;
            case 'info':
              setResult(prev => prev + `ℹ️  ${data.message}\n`);
              break;
            case 'stdout':
              setResult(prev => prev + data.data);
              break;
            case 'stderr':
              setResult(prev => prev + `[STDERR] ${data.data}`);
              break;
            case 'error':
              setResult(prev => prev + `❌ ${data.message}\n`);
              break;
            case 'completed':
              const completionMsg = data.success
                ? `✅ Task completed successfully!\n`
                : `❌ Task failed with exit code ${data.code}\n`;
              setResult(prev => prev + completionMsg);
              newEventSource.close();
              setEventSource(null);
              setTaskId(null);
              break;
          }
        } catch (error) {
          console.error('Error parsing SSE data:', error);
        }
      };

      newEventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        setResult(prev => prev + `⚠️  Connection lost\n`);
        newEventSource.close();
        setEventSource(null);
        setTaskId(null);
      };

    } catch (error) {
      console.error('CoAct-1 execution error:', error);
      setResult(prev => prev + `❌ Error executing task: ${error.message}\n\nPlease check that:\n1. The backend server is running (npm run server)\n2. Python and required dependencies are installed\n3. GOOGLE_API_KEY environment variable is set\n`);
      setIsRunning(false);
    }
  };

  // Auto-scroll to bottom when result updates
  useEffect(() => {
    if (resultRef.current) {
      resultRef.current.scrollTop = resultRef.current.scrollHeight;
    }
  }, [result]);

  // Cleanup effect for EventSource
  useEffect(() => {
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [eventSource]);

  const handleTaskSubmit = (task: string) => {
    runCoActAutomation(task);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      <div className="relative z-10">
        {/* Hero Section */}
        <div className="text-center py-8 px-4">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg">
              <Brain className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-5xl font-bold text-white">
              CoAct-1
              <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent ml-2">
                Multi-Agent System
              </span>
            </h1>
            <div className="p-3 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-lg">
              <Zap className="w-8 h-8 text-white" />
            </div>
          </div>

          <p className="text-xl text-white/80 mb-8 max-w-2xl mx-auto leading-relaxed">
            Computer automation with multi-agent coordination
          </p>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto px-4 pb-16">
          {/* Task Input Section */}
          <div className="mb-8">
            <TaskInput onSubmit={handleTaskSubmit} isRunning={isRunning} />
          </div>

          {/* Result Display */}
          {result && (
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-6">
              <h2 className="text-white text-lg font-semibold mb-4 flex items-center justify-between">
                <span>Live Execution Output</span>
                {isRunning && (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-400 border-t-transparent"></div>
                    <span className="text-blue-400 text-sm">Running...</span>
                  </div>
                )}
              </h2>
              <div
                ref={resultRef}
                className="bg-black/30 rounded-lg p-4 max-h-96 overflow-y-auto"
              >
                <pre className="text-white/90 text-sm whitespace-pre-wrap font-mono leading-relaxed">
                  {result}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;