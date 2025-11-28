import { useEffect, useState } from "react";

function App() {
  const [prediction, setPrediction] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch prediction from backend
  const fetchPrediction = async () => {
    try {
      const response = await fetch("http://localhost:8000/predict"); // your FastAPI endpoint
      if (!response.ok) {
        throw new Error("Server error: " + response.status);
      }
      const data = await response.json();
      setPrediction(data.prediction); // "morning" / "afternoon" / "evening"
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-fetch when component mounts
  useEffect(() => {
    fetchPrediction();
  }, []);

  return (
    <div style={{ padding: "30px", fontFamily: "Arial", fontSize: "20px" }}>
      <h1>Contextual Bandit Prediction</h1>

      {isLoading && <p>Loading prediction...</p>}
      {error && <p style={{ color: "red" }}>Error: {error}</p>}

      {prediction && !isLoading && (
        <div style={{ marginTop: "20px" }}>
          <h2>Predicted Best Time: <strong>{prediction}</strong></h2>
        </div>
      )}
    </div>
  );
}

export default App;
