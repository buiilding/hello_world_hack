import React, { useState, useEffect } from 'react';
import { Monitor, Maximize2, Minimize2, RotateCcw, Zap } from 'lucide-react';

interface BrowserViewProps {
  isAutomationActive: boolean;
}

const BrowserView: React.FC<BrowserViewProps> = ({ isAutomationActive }) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1500);
  };

  useEffect(() => {
    if (isAutomationActive) {
      setIsLoading(true);
      setTimeout(() => setIsLoading(false), 2000);
    }
  }, [isAutomationActive]);

  return (
    <div className={`
      relative transition-all duration-300 ease-in-out
      ${isFullscreen ? 'fixed inset-4 z-50' : 'h-[600px]'}
    `}>
      <div className="relative h-full bg-white/10 backdrop-blur-md border border-white/20 rounded-xl overflow-hidden">
        {/* Browser Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/20 bg-white/5">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-400"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
              <div className="w-3 h-3 rounded-full bg-green-400"></div>
            </div>
            <div className="flex items-center gap-2 ml-4">
              <Monitor className="w-4 h-4 text-white/70" />
              <span className="text-white/90 font-medium">Live Browser View</span>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {isAutomationActive && (
              <div className="flex items-center gap-2 px-3 py-1 bg-green-500/20 rounded-full border border-green-400/30">
                <Zap className="w-3 h-3 text-green-400 animate-pulse" />
                <span className="text-green-400 text-xs font-medium">Automation Active</span>
              </div>
            )}
            
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="p-2 hover:bg-white/10 rounded-lg transition-all duration-200 hover:scale-105"
            >
              <RotateCcw className={`w-4 h-4 text-white/70 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 hover:bg-white/10 rounded-lg transition-all duration-200 hover:scale-105"
            >
              {isFullscreen ? (
                <Minimize2 className="w-4 h-4 text-white/70" />
              ) : (
                <Maximize2 className="w-4 h-4 text-white/70" />
              )}
            </button>
          </div>
        </div>

        {/* Address Bar */}
        <div className="px-4 py-2 border-b border-white/20 bg-white/5">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-white/10 rounded-lg px-3 py-2 border border-white/20">
              <span className="text-white/80 text-sm">localhost:8006</span>
            </div>
          </div>
        </div>

        {/* Browser Content */}
        <div className="relative flex-1 h-full">
          {isLoading && (
            <div className="absolute inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-10">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                <p className="text-white/80 text-sm">Loading automation environment...</p>
              </div>
            </div>
          )}
          
          <iframe
            src="http://localhost:8006"
            className="w-full h-full border-none bg-white"
            title="Automation Browser View"
            style={{ minHeight: isFullscreen ? 'calc(100vh - 120px)' : '500px' }}
          />
          
        </div>
      </div>

      {/* Fullscreen backdrop */}
      {isFullscreen && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          onClick={() => setIsFullscreen(false)}
        />
      )}
    </div>
  );
};

export default BrowserView;