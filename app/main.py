from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import db
from app.repositories import sesiones
from app.routers import acciones, admin, auth, gestion, paginas
from app.templating import templates

BASE = Path(__file__).resolve().parent

CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "frame-ancestors 'none'; form-action 'self'; base-uri 'self'")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.verificar()      # falla al arrancar si Neo4j no responde
    sesiones.limpiar()  # borra sesiones vencidas
    yield
    db.cerrar()


# Sin /docs ni /openapi.json: la aplicacion es de paginas, no una API publica
app = FastAPI(title="LinkedUn", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(acciones.router)  # antes que paginas: /perfil/editar gana a /perfil/{id}
app.include_router(gestion.router)
app.include_router(paginas.router)


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = CSP
    if not request.url.path.startswith("/static"):
        resp.headers["Cache-Control"] = "no-store"  # evita ver paginas privadas con el boton "atras"
    return resp


@app.get("/salud", include_in_schema=False)
def salud():
    return db.leer("RETURN 1 AS ok")


@app.exception_handler(StarletteHTTPException)
async def error_http(request: Request, exc: StarletteHTTPException):
    # Las dependencias usan HTTPException(303, Location=...) para redirigir
    if 300 <= exc.status_code < 400 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=exc.status_code)
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(
            request, "error.html",
            {"yo": None, "codigo": exc.status_code, "detalle": exc.detail},
            status_code=exc.status_code,
        )
    return JSONResponse({"detalle": exc.detail}, status_code=exc.status_code)
