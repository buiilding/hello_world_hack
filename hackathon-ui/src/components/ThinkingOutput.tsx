import React from 'react';
import { Brain, Zap, Code, Eye, CheckCircle, Clock, AlertCircle } from 'lucide-react';

interface ThinkingStep {
  id: string;
  type: 'thinking' | 'planning' | 'coding' | 'executing' | 'observing' | 'completed' | 'error';
  content: string;
  timestamp: Date;
  status: 'active' | 'completed' | 'error';
}

interface ThinkingOutputProps {
  steps: ThinkingStep[];
  isActive: boolean;
}

const ThinkingOutput: React.FC<ThinkingOutputProps> = ({ steps, isActive }) => {
  const getStepIcon = (type: string, status: string) => {
    if (status === 'active') {
      switch (type) {
        case 'thinking':
          return <Brain className="w-4 h-4 text-blue-400 animate-pulse" />;
        case 'planning':
          return <Zap className="w-4 h-4 text-purple-400 animate-pulse" />;
        case 'coding':
          return <Code className="w-4 h-4 text-green-400 animate-pulse" />;
        case 'executing':
          return <div className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />;
        case 'observing':
          return <Eye className="w-4 h-4 text-cyan-400 animate-pulse" />;
        default:
          return <Clock className="w-4 h-4 text-gray-400 animate-pulse" />;
      }
    } else if (status === 'completed') {
      return <CheckCircle className="w-4 h-4 text-green-400" />;
    } else if (status === 'error') {
      return <AlertCircle className="w-4 h-4 text-red-400" />;
    }
    return <Clock className="w-4 h-4 text-gray-400" />;
  };

  const getStepColor = (type: string, status: string) => {
    if (status === 'error') return 'border-red-400/30 bg-red-500/10';
    if (status === 'active') {
      switch (type) {
        case 'thinking':
          return 'border-blue-400/30 bg-blue-500/10';
        case 'planning':
          return 'border-purple-400/30 bg-purple-500/10';
        case 'coding':
          return 'border-green-400/30 bg-green-500/10';
        case 'executing':
          return 'border-amber-400/30 bg-amber-500/10';
        case 'observing':
          return 'border-cyan-400/30 bg-cyan-500/10';
        default:
          return 'border-gray-400/30 bg-gray-500/10';
      }
    }
    return 'border-white/10 bg-white/5';
  };

  const getStepLabel = (type: string) => {
    switch (type) {
      case 'thinking':
        return 'Thinking';
      case 'planning':
        return 'Planning';
      case 'coding':
        return 'Coding';
      case 'executing':
        return 'Executing';
      case 'observing':
        return 'Observing';
      case 'completed':
        return 'Completed';
      case 'error':
        return 'Error';
      default:
        return 'Processing';
    }
  };

  return (
    <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg shadow-lg">
          <Brain className="w-6 h-6 text-white" />
        </div>
        <div>
          <h3 className="text-white font-semibold text-lg">Real-time Model Output</h3>
          <p className="text-white/70 text-sm">Live thinking process and execution steps</p>
        </div>
        {isActive && (
          <div className="ml-auto flex items-center gap-2 px-3 py-1 bg-green-500/20 rounded-full border border-green-400/30">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-green-400 text-xs font-medium">Active</span>
          </div>
        )}
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
        {steps.length === 0 ? (
          <div className="text-center py-12">
            <Brain className="w-16 h-16 text-white/20 mx-auto mb-4" />
            <p className="text-white/60 text-lg font-medium">Waiting for task input...</p>
            <p className="text-white/40 text-sm mt-2">The model's thinking process will appear here</p>
          </div>
        ) : (
          steps.map((step, index) => (
            <div
              key={step.id}
              className={`
                relative p-4 rounded-lg border transition-all duration-300
                hover:scale-[1.01] hover:shadow-lg
                ${getStepColor(step.type, step.status)}
                ${step.status === 'active' ? 'ring-1 ring-white/20' : ''}
              `}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {getStepIcon(step.type, step.status)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`
                        text-xs font-medium px-2 py-1 rounded-full
                        ${step.status === 'active' ? 'bg-white/20 text-white' : 
                          step.status === 'completed' ? 'bg-green-500/20 text-green-300' :
                          step.status === 'error' ? 'bg-red-500/20 text-red-300' :
                          'bg-white/10 text-white/70'}
                      `}>
                        {getStepLabel(step.type)}
                      </span>
                      {step.status === 'active' && (
                        <div className="flex space-x-1">
                          <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" />
                          <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce delay-100" />
                          <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce delay-200" />
                        </div>
                      )}
                    </div>
                    <span className="text-white/50 text-xs">
                      {step.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  
                  <div className={`
                    text-sm leading-relaxed
                    ${step.status === 'active' ? 'text-white' : 
                      step.status === 'completed' ? 'text-white/90' : 
                      step.status === 'error' ? 'text-red-300' :
                      'text-white/70'}
                  `}>
                    {step.type === 'coding' ? (
                      <pre className="bg-black/20 p-3 rounded-lg overflow-x-auto text-xs font-mono">
                        <code>{step.content}</code>
                      </pre>
                    ) : (
                      <p className="whitespace-pre-wrap">{step.content}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Active step indicator */}
              {step.status === 'active' && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/10 rounded-b-lg overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-blue-400 to-purple-400 animate-pulse" />
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {steps.length > 0 && (
        <div className="mt-4 flex items-center justify-between text-xs text-white/50">
          <span>
            {steps.filter(s => s.status === 'completed').length} of {steps.length} steps completed
          </span>
          {isActive && (
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
              Processing...
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default ThinkingOutput;