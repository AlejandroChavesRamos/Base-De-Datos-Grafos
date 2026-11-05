from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.verificar()
    yield
    db.cerrar()

app = FastAPI(lifespan=lifespan)

@app.get("/salud")
def salud():
    return db.leer("RETURN 1 AS ok")