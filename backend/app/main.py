from fastapi import FastAPI

app = FastAPI(title="Sacame de la Pobreza API")


@app.get("/health")
def health():
    return {"status": "ok"}
