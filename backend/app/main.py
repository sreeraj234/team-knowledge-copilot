from fastapi import FastAPI

app = FastAPI(title="Team Knowledge Copilot")


@app.get("/health")
def health() -> dict:
    """Simple liveness check: returns ok if the server is running."""
    return {"status": "ok"}
