import math
from pathlib import Path


def proximo_pm_horas(horometro_actual: float, intervalo: int) -> float:
    h = max(0.0, float(horometro_actual or 0))
    if h <= 0:
        return float(intervalo)
    return math.ceil(h / intervalo) * intervalo


def semaforo_pm(horometro_actual: float, proximo: float, margen: float = 50.0) -> str:
    """Retorna: ok | proximo | vencido"""
    h = float(horometro_actual or 0)
    p = float(proximo)
    faltante = p - h
    if h >= p and h > 0:
        return "vencido"
    if faltante <= margen:
        return "proximo"
    return "ok"


SEMAFORO_ESTILO = {
    "ok": ("background:#DCFCE7;border:2px solid #22C55E;", "OK"),
    "proximo": ("background:#FEF9C3;border:2px solid #EAB308;", "Próximo"),
    "vencido": ("background:#FEE2E2;border:2px solid #EF4444;", "Vencido"),
}


def estilo_tarjeta(semaforo: str) -> str:
    base = (
        "border-radius:8px;padding:12px;min-width:120px;"
        "font-family:Segoe UI;font-size:10pt;"
    )
    css, _ = SEMAFORO_ESTILO.get(semaforo, SEMAFORO_ESTILO["ok"])
    return base + css


def semaforo_estado_equipo(estado: str) -> str:
    e = (estado or "").lower()
    if "mantenimiento" in e:
        return "proximo"
    if "fuera" in e or "servicio" in e:
        return "vencido"
    return "ok"


def icono_tipo_archivo(ruta: str) -> str:
    if not ruta:
        return "📁"
    ext = Path(ruta).suffix.lower()
    if ext == ".pdf":
        return "📄 PDF"
    if ext in (".xlsx", ".xls", ".csv"):
        return "📊 Excel"
    if ext in (".doc", ".docx"):
        return "📝 Word"
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
        return "🖼 Imagen"
    return "📁 Archivo"
