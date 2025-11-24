import { useState } from 'react';
import './App.css';
import Heatmap from './components/Heatmap';

interface PredictionResponse {
  prediction: number;
  confidence: number;
}

function App() {
  const [historicalData, setHistoricalData] = useState<{ date: Date; value: number }[]>([]);
  const [formData, setFormData] = useState({
    block_focus: 0,
    keystroke_intervals_mean: 0,
    burstiness: 0,
    scroll_rate: 0,
    idle_time_percent: 0,
    microEMA: 0,
    sleep_hours_prev_night: 0,
  });
  const [prediction, setPrediction] = useState<number | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: parseFloat(value) || 0
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Update this URL to match your FastAPI backend URL
      const response = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: PredictionResponse = await response.json();
      setPrediction(data.prediction);
      setConfidence(data.confidence);

       // Add to historical data
    setHistoricalData(prev => [
      ...prev,
      {
        date: new Date(),
        value: data.prediction
      }
    ]);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      
      <h1>Context Prediction</h1>

      
      <form onSubmit={handleSubmit} className="prediction-form">
        <h2>Enter Context Features</h2>
        
        {Object.entries(formData).map(([key, value]) => (
          <div key={key} className="form-group">
            <label htmlFor={key}>
              {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
            </label>
            <input
              type="number"
              id={key}
              name={key}
              value={value}
              onChange={handleChange}
              step="0.01"
              required
            />
          </div>
        ))}

        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Predicting...' : 'Predict'}
        </button>
      </form>

      {error && <div className="error">Error: {error}</div>}

      {(prediction !== null && confidence !== null) && (
        <div className="result">
          <h3>Prediction Result</h3>
          <p>Predicted Class: <strong>{prediction}</strong></p>
          <p>Confidence: <strong>{(confidence * 100).toFixed(2)}%</strong></p>
        </div>
      )}

      <Heatmap
        data={historicalData}
        fromDate={new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)} // Last 30 days
        toDate={new Date()}
      />
    </div>
  );
}

export default App;
