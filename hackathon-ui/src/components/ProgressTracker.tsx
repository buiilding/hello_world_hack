import React from 'react';
import { CheckCircle, Circle, Clock } from 'lucide-react';

interface ProgressStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in-progress' | 'completed';
}

interface ProgressTrackerProps {
  steps: ProgressStep[];
  currentStep: number;
  overallProgress: number;
}

const ProgressTracker: React.FC<ProgressTrackerProps> = ({ 
  steps, 
  currentStep, 
  overallProgress 
}) => {
  const getStepIcon = (status: string, index: number) => {
    if (status === 'completed') {
      return <CheckCircle className="w-6 h-6 text-green-400" />;
    } else if (status === 'in-progress') {
      return (
        <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      );
    } else {
      return <Circle className="w-6 h-6 text-white/30" />;
    }
  };

  return (
    <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-white font-semibold text-lg">Task Progress</h3>
        <div className="text-right">
          <div className="text-2xl font-bold text-white mb-1">{Math.round(overallProgress)}%</div>
          <div className="text-white/60 text-sm">Complete</div>
        </div>
      </div>

      {/* Overall Progress Bar */}
      <div className="mb-8">
        <div className="w-full bg-white/10 rounded-full h-3 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-400 via-purple-400 to-green-400 transition-all duration-500 ease-out relative"
            style={{ width: `${overallProgress}%` }}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
          </div>
        </div>
      </div>

      {/* Step List */}
      <div className="space-y-4">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-start gap-4">
            <div className="flex-shrink-0 relative">
              {getStepIcon(step.status, index)}
              
              {/* Connecting line */}
              {index < steps.length - 1 && (
                <div className="absolute top-8 left-3 w-px h-8 bg-white/20" />
              )}
            </div>

            <div className={`
              flex-1 pb-4 transition-all duration-300
              ${step.status === 'in-progress' ? 'text-white' : 
                step.status === 'completed' ? 'text-white/90' : 'text-white/50'}
            `}>
              <h4 className="font-medium mb-1">{step.title}</h4>
              <p className="text-sm opacity-80">{step.description}</p>
              
              {step.status === 'in-progress' && (
                <div className="mt-2">
                  <div className="flex items-center gap-2 text-blue-400 text-sm">
                    <Clock className="w-3 h-3 animate-pulse" />
                    <span>In Progress...</span>
                  </div>
                </div>
              )}
            </div>

            {step.status === 'completed' && (
              <div className="flex-shrink-0">
                <div className="text-green-400 text-sm font-medium">✓ Done</div>
              </div>
            )}
          </div>
        ))}
      </div>

      {overallProgress === 100 && (
        <div className="mt-6 p-4 bg-green-500/20 border border-green-400/30 rounded-lg">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">Task Completed Successfully!</span>
          </div>
          <p className="text-green-300/80 text-sm mt-1">
            All agents have finished their work. The automation is complete.
          </p>
        </div>
      )}
    </div>
  );
};

export default ProgressTracker;