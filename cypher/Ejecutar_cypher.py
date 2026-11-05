import re
import sys
from pathlib import Path
 
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
 
from app.database import db  # noqa: E402
 
 
def leer_sentencias(ruta: Path) -> list[str]:
    texto = ruta.read_text(encoding="utf-8")
    # Quita solo las lineas que son unicamente comentario (no toca las URLs con //)
    lineas = [l for l in texto.splitlines() if not l.strip().startswith("//")]
    texto = "\n".join(lineas)
    # Separa por ';' al final de linea
    partes = re.split(r";\s*(?:\n|$)", texto)
    return [p.strip() for p in partes if p.strip()]
 
 
def main() -> None:
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("cypher/02_datos.cypher")
    sentencias = leer_sentencias(ruta)
    print(f"{ruta}: {len(sentencias)} sentencias\n")
 
    db.verificar()
    for i, s in enumerate(sentencias, start=1):
        resumen = " ".join(s.split())[:70]
        try:
            db.escribir(s)
            print(f"[{i:02d}] OK     {resumen}")
        except Exception as e:  # se detiene en el primer fallo
            print(f"[{i:02d}] ERROR  {resumen}\n       {e}")
            db.cerrar()
            sys.exit(1)
 
    db.cerrar()
    print("\nListo. Verifica con: MATCH (n) RETURN labels(n)[0] AS tipo, count(*) AS total;")
 
 
if __name__ == "__main__":
    main()