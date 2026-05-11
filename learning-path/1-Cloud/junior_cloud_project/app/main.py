from fastapi import FastAPI

app = FastAPI(title="Junior Cloud App", version="1.0.0")


@app.get("/")
def health_check():
    return {"status": "online"}
