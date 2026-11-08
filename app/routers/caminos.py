"""Explorador de caminos: de una persona hasta otra persona, una empresa o una oferta.

El origen SIEMPRE es la persona que tiene la sesion; el formulario solo elige el destino, y ese destino
se valida contra las opciones que se le ofrecen (lo que llega por la URL no se usa sin comprobarlo)."""
from fastapi import APIRouter, Depends, Request

from app.dependencias import usuario_actual
from app.repositories import caminos as repo
from app.routers.utiles import render

router = APIRouter()

TIPOS = {
    "persona": ("Otra persona", "¿Cómo estás conectado con ella?", repo.a_persona),
    "empresa": ("Una empresa", "¿Cómo llegas a ella?", repo.a_empresa),
    "oferta": ("Una oferta laboral", "¿Cómo llegas a la empresa que la publica y a su vacante?", repo.a_oferta),
}


@router.get("/caminos")
def caminos(request: Request, tipo: str | None = None, destino: str | None = None, yo: dict = Depends(usuario_actual)):
    opciones = {"persona": [(i, n) for i, n in repo.personas() if i != yo["id"]], "empresa": repo.empresas(), "oferta": repo.ofertas()}
    resultado = None
    if tipo is not None:
        if tipo not in TIPOS:
            resultado = {"tipo": tipo, "error": "Elige a dónde quieres llegar."}
        elif destino not in {i for i, _ in opciones[tipo]}:
            resultado = {"tipo": tipo, "error": "Elige un destino de la lista." if not destino else "Ese destino no es una opción válida."}
        else:
            rutas = TIPOS[tipo][2](yo["id"], destino)
            resultado = {"tipo": tipo, "destino": destino, "nombre": dict(opciones[tipo])[destino], "rutas": rutas}
    return render(request, "caminos.html", yo, tipos=TIPOS, opciones=opciones, resultado=resultado)
