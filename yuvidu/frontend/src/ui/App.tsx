import { useEffect, useState } from "react";
import Heatmap from "./components/Heatmap";
import "./AppStyles.css";

interface PredictionData {
  best_time: string;
  percentages: {
    morning: number;
    afternoon: number;
    evening: number;
    night: number;
  };
  status: string;
}

function App() {
  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch prediction from backend
  const fetchPrediction = async () => {
    console.log('Starting to fetch prediction...');
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("http://localhost:8000/predictall");
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Server error:', errorText);
        throw new Error(`Server error: ${response.status} - ${errorText}`);
      }
      
      const data: PredictionData = await response.json();
      console.log('Received data:', data);
      setPrediction(data);
    } catch (err) {
      console.error('Error in fetchPrediction:', err);
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      console.log('Finished loading');
      setIsLoading(false);
    }
  };

  // Auto-fetch when component mounts
  useEffect(() => {
    fetchPrediction();
  }, []);

  return (
    <>
    <div className="app-container">
      <h1 className="app-title">Contextual Bandit Prediction</h1>
      <div className="prediction-form">

      {isLoading && <p className="loading-message">Loading prediction...</p>}
      {error && <p className="error-message">Error: {error}</p>}

      {prediction && !isLoading && (
        <div className="prediction-results">
          <div className="best-time-section">
            <h2 className="best-time-title">
              Predicted Best Time: <span className="best-time-value">{prediction.best_time}</span>
            </h2>
          </div>
          
          <div className="probabilities-section">
            <h3 className="probabilities-title">Prediction Probabilities:</h3>
            <ul className="probabilities-list">
              {Object.entries(prediction.percentages).map(([time, percentage]) => (
                <li key={time} className="probability-item">
                  <div className="probability-row">
                    <span className="probability-label">{time}:</span>
                    <div className="probability-bar-container">
                      <div 
                        className={`probability-bar ${time === prediction.best_time ? 'probability-bar-best' : 'probability-bar-normal'}`}
                        style={{ width: `${percentage}%` }}
                      >
                        <span className="probability-value">{percentage.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    {prediction && <Heatmap percentages={prediction.percentages} />}
    </div>
    </div>
    </>
    
  );
}

export default App;
