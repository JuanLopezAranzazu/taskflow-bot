from fastapi import FastAPI

app = FastAPI(title="Bot de Telegram - Seguimiento de proyectos", version="1.0.0")

# ---------------- API REST ----------------

@app.get("/health")
async def health():
    return {"status": "ok"}
