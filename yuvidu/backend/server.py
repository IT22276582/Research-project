from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from bandit_model import predict_context, context_features

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5123"],  # React dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request body shape
class ContextInput(BaseModel):
    block_focus: float
    keystroke_intervals_mean: float
    burstiness: float
    scroll_rate: float
    idle_time_percent: float
    microEMA: float
    sleep_hours_prev_night: float


@app.get("/")
def home():
    return {"status": "Bandit API Running!"}


@app.post("/predict")
async def get_prediction(data: ContextInput):
    try:
        context_dict = data.dict()
        result = predict_context(context_dict)
        return {
            "prediction": result,
            "confidence": 0.95  # Replace with actual confidence from your model if available
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
