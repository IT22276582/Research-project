from fastapi import FastAPI
from pydantic import BaseModel
from bandit_model import predict_context, context_features

app = FastAPI()

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
def get_prediction(data: ContextInput):
    context_dict = data.dict()
    result = predict_context(context_dict)
    return {"recommended": result}
