import React, { useState, useEffect } from 'react';
import { Zap, Sparkles, Brain } from 'lucide-react';
import ThinkingOutput from './components/ThinkingOutput';
import TaskInput from './components/TaskInput';
import BrowserView from './components/BrowserView';
import ActivityFeed from './components/ActivityFeed';
import ProgressTracker from './components/ProgressTracker';

interface Activity {
  id: string;
  agent: 'orchestrator' | 'programmer' | 'gui-operator';
  action: string;
  details: string;
  status: 'pending' | 'in-progress' | 'completed' | 'error';
  timestamp: Date;
}

interface ProgressStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in-progress' | 'completed';
}

interface ThinkingStep {
  id: string;
  type: 'thinking' | 'planning' | 'coding' | 'executing' | 'observing' | 'completed' | 'error';
  content: string;
  timestamp: Date;
  status: 'active' | 'completed' | 'error';
}

function App() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentTask, setCurrentTask] = useState('');
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [progressSteps, setProgressSteps] = useState<ProgressStep[]>([]);
  const [overallProgress, setOverallProgress] = useState(0);

  // Simulate automation workflow
  const simulateAutomation = async (task: string) => {
    setIsRunning(true);
    setCurrentTask(task);
    setThinkingSteps([]);
    setActivities([]);
    setOverallProgress(0);

    // Define steps based on task
    const steps: ProgressStep[] = [
      {
        id: '1',
        title: 'Task Analysis',
        description: 'Orchestrator breaking down the task into subtasks',
        status: 'pending'
      },
      {
        id: '2',
        title: 'Code Generation',
        description: 'Programmer writing automation scripts',
        status: 'pending'
      },
      {
        id: '3',
        title: 'Browser Navigation',
        description: 'GUI Operator executing browser interactions',
        status: 'pending'
      },
      {
        id: '4',
        title: 'Task Completion',
        description: 'Verifying successful completion',
        status: 'pending'
      }
    ];

    setProgressSteps(steps);

    // Simulate thinking process
    const addThinkingStep = (type: ThinkingStep['type'], content: string, status: ThinkingStep['status'] = 'active') => {
      const step: ThinkingStep = {
        id: Date.now().toString() + Math.random(),
        type,
        content,
        timestamp: new Date(),
        status
      };
      setThinkingSteps(prev => [...prev, step]);
      return step.id;
    };

    const updateThinkingStep = (id: string, status: ThinkingStep['status']) => {
      setThinkingSteps(prev => prev.map(step => 
        step.id === id ? { ...step, status } : step
      ));
    };

    // Step 1: Initial thinking
    const thinkingId = addThinkingStep('thinking', `Analyzing the task: "${task}"\n\nI need to break this down into actionable steps:\n1. Navigate to the target website\n2. Search for the specified item\n3. Interact with the interface to complete the task`);

    setActivities(prev => [...prev, {
      id: Date.now().toString(),
      agent: 'orchestrator',
      action: 'Task Analysis Started',
      details: `Breaking down the task: "${task}" into actionable subtasks`,
      status: 'in-progress',
      timestamp: new Date()
    }]);

    setProgressSteps(prev => prev.map(step => 
      step.id === '1' ? { ...step, status: 'in-progress' } : step
    ));

    await new Promise(resolve => setTimeout(resolve, 2000));
    updateThinkingStep(thinkingId, 'completed');
    setOverallProgress(25);

    // Step 2: Planning
    const planningId = addThinkingStep('planning', `Creating execution plan:\n\n1. Open browser and navigate to target site\n2. Locate search functionality\n3. Input search criteria\n4. Parse results and identify target\n5. Execute required actions\n\nEstimated completion time: 30-45 seconds`);

    setActivities(prev => prev.map(activity => 
      activity.agent === 'orchestrator' && activity.status === 'in-progress'
        ? { ...activity, status: 'completed', details: 'Successfully identified 3 subtasks: navigate, search, and interact' }
        : activity
    ));

    setProgressSteps(prev => prev.map(step => 
      step.id === '1' ? { ...step, status: 'completed' } : step
    ));

    await new Promise(resolve => setTimeout(resolve, 1500));
    updateThinkingStep(planningId, 'completed');
    setOverallProgress(50);

    // Step 3: Coding
    const codingId = addThinkingStep('coding', `from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Initialize browser
driver = webdriver.Chrome()
driver.get("https://amazon.com")

# Search for laptops
search_box = driver.find_element(By.ID, "twotabsearchtextbox")
search_box.send_keys("laptop")
search_box.submit()

# Wait for results and find cheapest option
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-component-type='s-search-result']"))
)`);

    setActivities(prev => [...prev, {
      id: (Date.now() + 1).toString(),
      agent: 'programmer',
      action: 'Script Generation',
      details: 'Writing Selenium WebDriver scripts for browser automation',
      status: 'in-progress',
      timestamp: new Date()
    }]);

    setProgressSteps(prev => prev.map(step => 
      step.id === '2' ? { ...step, status: 'in-progress' } : step
    ));

    await new Promise(resolve => setTimeout(resolve, 2500));
    updateThinkingStep(codingId, 'completed');
    setOverallProgress(75);

    // Step 4: Executing
    const executingId = addThinkingStep('executing', `Executing automation script...\n\n✓ Browser launched successfully\n✓ Navigated to Amazon.com\n✓ Located search box\n✓ Entered search term "laptop"\n✓ Submitted search query\n✓ Waiting for results to load...`);

    setActivities(prev => prev.map(activity => 
      activity.agent === 'programmer' && activity.status === 'in-progress'
        ? { ...activity, status: 'completed', details: 'Generated 3 Python scripts with error handling and logging' }
        : activity
    ));

    setProgressSteps(prev => prev.map(step => 
      step.id === '2' ? { ...step, status: 'completed' } : step
    ));

    await new Promise(resolve => setTimeout(resolve, 2000));
    updateThinkingStep(executingId, 'completed');

    // Step 5: Observing
    const observingId = addThinkingStep('observing', `Analyzing search results...\n\nFound 16 laptop listings on current page\nPrice range: $299 - $2,499\nCheapest option identified: "Refurbished HP Laptop 14" - $299.99"\n\nPreparing to click on the cheapest option...`);

    setActivities(prev => [...prev, {
      id: (Date.now() + 2).toString(),
      agent: 'gui-operator',
      action: 'Browser Automation',
      details: 'Launching browser and executing automated interactions',
      status: 'in-progress',
      timestamp: new Date()
    }]);

    setProgressSteps(prev => prev.map(step => 
      step.id === '3' ? { ...step, status: 'in-progress' } : step
    ));

    await new Promise(resolve => setTimeout(resolve, 1800));
    updateThinkingStep(observingId, 'completed');
    setOverallProgress(90);

    // Step 6: Completion
    const completedId = addThinkingStep('completed', `Task completed successfully! 🎉\n\nSummary:\n✓ Navigated to Amazon.com\n✓ Searched for "laptop"\n✓ Identified cheapest option: HP Laptop 14" for $299.99\n✓ Product page loaded and ready for user review\n\nTotal execution time: 8.3 seconds`, 'completed');

    setActivities(prev => prev.map(activity => 
      activity.agent === 'gui-operator' && activity.status === 'in-progress'
        ? { ...activity, status: 'completed', details: 'Successfully completed all browser interactions and data extraction' }
        : activity
    ));

    setProgressSteps(prev => prev.map(step => 
      step.id === '3' ? { ...step, status: 'completed' } : step
    ));

    // Final completion
    await new Promise(resolve => setTimeout(resolve, 500));

    setProgressSteps(prev => prev.map(step => 
      step.id === '4' ? { ...step, status: 'in-progress' } : step
    ));

    setActivities(prev => [...prev, {
      id: (Date.now() + 3).toString(),
      agent: 'orchestrator',
      action: 'Task Verification',
      details: 'Verifying task completion and generating summary report',
      status: 'in-progress',
      timestamp: new Date()
    }]);

    await new Promise(resolve => setTimeout(resolve, 1000));

    setOverallProgress(100);
    setProgressSteps(prev => prev.map(step => 
      step.id === '4' ? { ...step, status: 'completed' } : step
    ));

    setActivities(prev => prev.map(activity => 
      activity.status === 'in-progress'
        ? { ...activity, status: 'completed', details: 'Task completed successfully with full verification' }
        : activity
    ));

    setIsRunning(false);
  };

  const handleTaskSubmit = (task: string) => {
    simulateAutomation(task);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-br from-blue-500/10 to-transparent rounded-full animate-pulse" />
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-tl from-purple-500/10 to-transparent rounded-full animate-pulse delay-1000" />
      </div>

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
          
          <p className="text-xl text-white/80 mb-4 max-w-2xl mx-auto leading-relaxed">
            Transforming the way people use computers
          </p>
          
          <div className="flex items-center justify-center gap-2 mb-6">
            <Sparkles className="w-5 h-5 text-yellow-400 animate-pulse" />
            <p className="text-lg text-yellow-300/90 font-medium">
              A new Jarvis system that thinks, codes, and acts
            </p>
            <Sparkles className="w-5 h-5 text-yellow-400 animate-pulse" />
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 pb-16">
          {/* Task Input Section */}
          <div className="mb-10">
            <TaskInput onSubmit={handleTaskSubmit} isRunning={isRunning} />
          </div>

          {/* Agent Cards */}
          <div className="mb-10">
            <ThinkingOutput steps={thinkingSteps} isActive={isRunning} />
          </div>

          {/* Browser View */}
          <div className="mb-10">
            <BrowserView isAutomationActive={isRunning} />
          </div>

          {/* Progress and Activity */}
          <div className="mb-10 grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ProgressTracker 
              steps={progressSteps}
              currentStep={Math.floor(overallProgress / 25)}
              overallProgress={overallProgress}
            />
            <ActivityFeed activities={activities} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;