"""
utils.py – Carga de datos y constantes compartidas.
"""
from pathlib import Path
import pandas as pd
import streamlit as st

# ── Rutas ─────────────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent.parent / "data" / "preguntas.csv"

# ── Constantes clínicas ───────────────────────────────────────────────────────
DOMINIOS = ["Social", "Comunicacion", "Sensorial", "Intereses"]

NOMBRES_TEST = {
    1: "Test 1 – Cuestionario propio",
    2: "Test 2 – Test online adaptativo",
    3: "RAADS-R",
}

ICONOS_DOMINIO = {
    "Social":       "👥",
    "Comunicacion": "💬",
    "Sensorial":    "🎵",
    "Intereses":    "🔍",
}

COLORES_DOMINIO = {
    "Social":       "#4C72B0",
    "Comunicacion": "#DD8452",
    "Sensorial":    "#55A868",
    "Intereses":    "#C44E52",
}

COLORES_TEST = {
    1: "#4C72B0",
    2: "#DD8452",
    3: "#55A868",
}


# ── Carga ─────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def cargar_preguntas() -> pd.DataFrame:
    """Lee preguntas.csv con cache de Streamlit. Seguro para llamar múltiples veces."""
    df = pd.read_csv(DATA_PATH, dtype={"id": int, "test_id": int, "orden": int})
    df["notas"]    = df["notas"].fillna("")
    df["opcion_e"] = df["opcion_e"].fillna("")
    df["dominio"]  = df["dominio"].fillna("Sin_clasificar")
    return df


# ── Helpers ───────────────────────────────────────────────────────────────────
def preguntas_de_test(df: pd.DataFrame, test_id: int) -> pd.DataFrame:
    return df[df["test_id"] == test_id].sort_values("orden").reset_index(drop=True)


def obtener_opciones_lista(row: pd.Series) -> dict[int, str]:
    """
    Devuelve {valor_numerico: texto_opcion} según la escala del ítem.

    Escala 1-4 → claves 1,2,3,4
    Escala 0-3 → claves 0,1,2,3
    """
    claves = [1, 2, 3, 4] if row["escala_origen"] == "1-4" else [0, 1, 2, 3]
    opciones_cols = ["opcion_a", "opcion_b", "opcion_c", "opcion_d"]

    # Opción E si existe
    e = str(row.get("opcion_e", "")).strip()
    if e:
        opciones_cols.append("opcion_e")
        claves.append(claves[-1] + 1)

    return {k: str(row[c]) for k, c in zip(claves, opciones_cols)}


def porcentaje_completado(df_test: pd.DataFrame, respuestas: dict) -> float:
    ids = set(df_test["id"].tolist())
    return len(ids & set(respuestas)) / len(ids) if ids else 0.0
