from fastapi import FastAPI

app = FastAPI(title="junior-k8s-app")


@app.get("/health")
def health():
    return {"status": "ok"}
