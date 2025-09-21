import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Clock, CheckCircle } from 'lucide-react';

interface TaskInputProps {
  onSubmit: (task: string) => void;
  isRunning: boolean;
}

const TaskInput: React.FC<TaskInputProps> = ({ onSubmit, isRunning }) => {
  const [task, setTask] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const suggestions = [
    "Go to Amazon and find the cheapest laptop",
    "Open Gmail and compose an email to team@company.com",
    "Navigate to GitHub and create a new repository called 'my-project'",
    "Search for Python tutorials on YouTube",
    "Book a flight from New York to London on Expedia",
    "Create a new document in Google Docs with title 'Meeting Notes'"
  ];

  // Handle click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    if (showSuggestions) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showSuggestions]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (task.trim() && !isRunning) {
      onSubmit(task.trim());
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setTask(suggestion);
    setShowSuggestions(false);
  };

  return (
    <div className="relative" ref={containerRef}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-xl blur-xl" />
          <div className="relative bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-6">
            <label className="block text-white/90 text-lg font-semibold mb-4">
              What would you like CoAct-1 to do for you?
            </label>
            
            <div className="relative">
              <textarea
                value={task}
                onChange={(e) => setTask(e.target.value)}
                onFocus={() => setShowSuggestions(true)}
                placeholder="Type your task here... (e.g., 'Go to Amazon and find the cheapest laptop under $500')"
                className="
                  w-full h-32 px-4 py-3 pr-14
                  bg-white/10 border border-white/20 rounded-lg
                  text-white placeholder-white/50
                  focus:outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-transparent
                  resize-none text-lg
                  backdrop-blur-sm
                "
                disabled={isRunning}
              />
              
              <button
                type="submit"
                disabled={!task.trim() || isRunning}
                className="
                  absolute right-3 top-3 p-2
                  bg-gradient-to-r from-blue-500 to-blue-600
                  hover:from-blue-600 hover:to-blue-700
                  disabled:from-gray-500 disabled:to-gray-600
                  disabled:cursor-not-allowed
                  rounded-lg transition-all duration-200
                  hover:scale-105 disabled:hover:scale-100
                  shadow-lg hover:shadow-xl
                "
              >
                {isRunning ? (
                  <div className="animate-spin">
                    <Clock className="w-5 h-5 text-white" />
                  </div>
                ) : (
                  <Send className="w-5 h-5 text-white" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Suggestions Dropdown */}
        {showSuggestions && !isRunning && (
          <div className="relative">
            <div className="absolute top-2 left-0 right-0 z-10">
              <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-4 h-4 text-blue-400" />
                  <span className="text-white/90 text-sm font-medium">Suggested Tasks</span>
                </div>
                
                <div className="space-y-2">
                  {suggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="
                        w-full text-left p-3 rounded-lg
                        bg-white/5 hover:bg-white/10
                        border border-transparent hover:border-white/20
                        text-white/80 hover:text-white
                        transition-all duration-200
                        hover:scale-[1.01]
                      "
                    >
                      <div className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                        <span className="text-sm">{suggestion}</span>
                      </div>
                    </button>
                  ))}
                </div>
                
                <button
                  onClick={() => setShowSuggestions(false)}
                  className="
                    mt-3 w-full text-center py-2 px-4
                    text-white/60 hover:text-white/80
                    text-sm transition-colors duration-200
                  "
                >
                  Close suggestions
                </button>
              </div>
            </div>
          </div>
        )}
      </form>
    </div>
  );
};

export default TaskInput;