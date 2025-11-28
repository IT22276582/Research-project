from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bandit_model import predict_context

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Bandit API Running!"}

@app.get("/predict")
async def get_prediction():
    try:
        result = predict_context()
        return {"prediction": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
