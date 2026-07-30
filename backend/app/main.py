from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, mesas, pedidos, reservas, restaurantes

app = FastAPI(title="Sacame de la Pobreza API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(restaurantes.router)
app.include_router(mesas.router)
app.include_router(reservas.router)
app.include_router(pedidos.router)


@app.get("/health")
def health():
    return {"status": "ok"}
