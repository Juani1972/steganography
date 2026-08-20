"""FastAPI server placeholder for REST API."""
from fastapi import FastAPI
app = FastAPI(title="Stegstr API", version="2.1.5")

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.1.5"}
