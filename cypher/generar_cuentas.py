import re
import sys
import unicodedata
from pathlib import Path
 
# Permite importar "app" aunque el script viva dentro de cypher/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
 
from argon2 import PasswordHasher  # noqa: E402
from app.database import db  # noqa: E402
 
ph = PasswordHasher()
 
# Contrasenas SOLO para pruebas. Cambiarlas en cualquier entorno real.
CLAVE_PRUEBA = "Prueba12345"
CLAVE_STAFF = "Staff12345!"
CLAVE_ADMIN = "Admin12345!"
 
 
def slug(texto: str) -> str:
    """'Juan David' -> 'juandavid' (sin tildes, espacios ni simbolos)."""
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", ascii_.lower())
 
 
CREAR_CUENTAS_PERSONA = """
UNWIND $filas AS f
MATCH (p:Usuario {id: f.perfil_id}), (r:Rol {nombre: 'persona'})
MERGE (c:Cuenta {id: f.cuenta_id})
  ON CREATE SET c.email = f.email, c.password_hash = f.hash, c.tipo = 'persona',
                c.activa = true, c.email_verificado = true,
                c.intentos_fallidos = 0, c.creada_en = datetime()
MERGE (c)-[:TIENE_PERFIL]->(p)
MERGE (c)-[:TIENE_ROL]->(r)
RETURN count(c) AS creadas
"""
 
CREAR_CUENTAS_EMPRESA = """
UNWIND $filas AS f
MATCH (p:Empresa {id: f.perfil_id}), (r:Rol {nombre: 'empresa'})
MERGE (c:Cuenta {id: f.cuenta_id})
  ON CREATE SET c.email = f.email, c.password_hash = f.hash, c.tipo = 'empresa',
                c.activa = true, c.email_verificado = true,
                c.intentos_fallidos = 0, c.creada_en = datetime()
MERGE (c)-[:TIENE_PERFIL]->(p)
MERGE (c)-[:TIENE_ROL]->(r)
RETURN count(c) AS creadas
"""
 
CREAR_CUENTAS_INTERNAS = """
UNWIND $filas AS f
MATCH (r:Rol {nombre: f.tipo})
MERGE (c:Cuenta {id: f.cuenta_id})
  ON CREATE SET c.email = f.email, c.password_hash = f.hash, c.tipo = f.tipo,
                c.activa = true, c.email_verificado = true,
                c.intentos_fallidos = 0, c.creada_en = datetime()
MERGE (c)-[:TIENE_ROL]->(r)
RETURN count(c) AS creadas
"""
 
 
def main() -> None:
    db.verificar()
 
    # --- Personas sin cuenta ---
    personas = db.leer(
        """
        MATCH (u:Usuario)
        WHERE NOT (:Cuenta)-[:TIENE_PERFIL]->(u)
        RETURN u.id AS id, u.nombre AS nombre, u.apellido AS apellido
        """
    )
    filas = [
        {
            "cuenta_id": f"c-{p['id']}",
            "perfil_id": p["id"],
            "email": f"{slug(p['nombre'])}.{slug(p['apellido'])}@example.com",
            "hash": ph.hash(CLAVE_PRUEBA),
        }
        for p in personas
    ]
    if filas:
        db.escribir(CREAR_CUENTAS_PERSONA, filas=filas)
    print(f"Cuentas de persona creadas: {len(filas)}")
 
    # --- Empresas sin cuenta ---
    empresas = db.leer(
        """
        MATCH (e:Empresa)
        WHERE NOT (:Cuenta)-[:TIENE_PERFIL]->(e)
        RETURN e.id AS id, e.nombre AS nombre
        """
    )
    filas = [
        {
            "cuenta_id": f"c-{e['id']}",
            "perfil_id": e["id"],
            "email": f"contacto@{slug(e['nombre'])}.example.com",
            "hash": ph.hash(CLAVE_PRUEBA),
        }
        for e in empresas
    ]
    if filas:
        db.escribir(CREAR_CUENTAS_EMPRESA, filas=filas)
    print(f"Cuentas de empresa creadas: {len(filas)}")
 
    # --- Cuentas internas (sin perfil publico) ---
    internas = [
        {"cuenta_id": "c-staff01", "tipo": "staff", "email": "staff@redprofesional.test", "hash": ph.hash(CLAVE_STAFF)},
        {"cuenta_id": "c-admin01", "tipo": "admin", "email": "admin@redprofesional.test", "hash": ph.hash(CLAVE_ADMIN)},
    ]
    db.escribir(CREAR_CUENTAS_INTERNAS, filas=internas)
    print("Cuentas internas listas: staff y admin")
 
    print("\nContrasena de prueba (personas y empresas):", CLAVE_PRUEBA)
    print("Ejemplos de login: camila.restrepo@example.com | contacto@caribesoftwarelabs.example.com")
 
    db.cerrar()
 
 
if __name__ == "__main__":
    main()