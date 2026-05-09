from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {
        "message": "MoneyRoute Rates API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }
