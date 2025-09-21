import React from 'react';
import { Clock, CheckCircle, AlertCircle, Target, Code, Gamepad2 } from 'lucide-react';

interface Activity {
  id: string;
  agent: 'orchestrator' | 'programmer' | 'gui-operator';
  action: string;
  details: string;
  status: 'pending' | 'in-progress' | 'completed' | 'error';
  timestamp: Date;
}

interface ActivityFeedProps {
  activities: Activity[];
}

const ActivityFeed: React.FC<ActivityFeedProps> = ({ activities }) => {
  const getAgentIcon = (agent: string) => {
    switch (agent) {
      case 'orchestrator':
        return <Target className="w-4 h-4 text-blue-400" />;
      case 'programmer':
        return <Code className="w-4 h-4 text-green-400" />;
      case 'gui-operator':
        return <Gamepad2 className="w-4 h-4 text-amber-400" />;
      default:
        return null;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      case 'in-progress':
        return <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getAgentColor = (agent: string) => {
    switch (agent) {
      case 'orchestrator':
        return 'border-blue-400/30 bg-blue-500/10';
      case 'programmer':
        return 'border-green-400/30 bg-green-500/10';
      case 'gui-operator':
        return 'border-amber-400/30 bg-amber-500/10';
      default:
        return 'border-gray-400/30 bg-gray-500/10';
    }
  };

  return (
    <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-6">
      <div className="flex items-center gap-2 mb-6">
        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
        <h3 className="text-white font-semibold text-lg">Live Activity Feed</h3>
      </div>

      <div className="space-y-4 max-h-96 overflow-y-auto scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
        {activities.length === 0 ? (
          <div className="text-center py-8">
            <Clock className="w-12 h-12 text-white/30 mx-auto mb-3" />
            <p className="text-white/60">Waiting for task to begin...</p>
            <p className="text-white/40 text-sm mt-1">Activity will appear here once automation starts</p>
          </div>
        ) : (
          activities.map((activity) => (
            <div
              key={activity.id}
              className={`
                relative p-4 rounded-lg border transition-all duration-300
                hover:scale-[1.01] hover:shadow-lg
                ${getAgentColor(activity.agent)}
              `}
            >
              <div className="flex items-start gap-3">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {getAgentIcon(activity.agent)}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="text-white font-medium text-sm capitalize truncate">
                        {activity.agent.replace('-', ' ')}
                      </h4>
                      <span className="text-white/50 text-xs flex-shrink-0">
                        {activity.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    
                    <p className="text-white/90 text-sm font-medium mb-1">
                      {activity.action}
                    </p>
                    
                    <p className="text-white/70 text-xs leading-relaxed">
                      {activity.details}
                    </p>
                  </div>
                  
                  <div className="flex-shrink-0">
                    {getStatusIcon(activity.status)}
                  </div>
                </div>
              </div>

              {/* Progress indicator for in-progress activities */}
              {activity.status === 'in-progress' && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/10 rounded-b-lg overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-blue-400 to-purple-400 animate-pulse" />
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {activities.length > 0 && (
        <div className="mt-4 text-center">
          <span className="text-white/50 text-xs">
            {activities.filter(a => a.status === 'completed').length} of {activities.length} tasks completed
          </span>
        </div>
      )}
    </div>
  );
};

export default ActivityFeed;