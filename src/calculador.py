"""
calculador.py – Motor de puntuación unificado.

Calcula medias por dominio para cada test, media global ponderada
entre tests, y puntuación bruta RAADS-R.

Función principal:  calcular_puntuaciones()
Función auxiliar:   interpretar_media()
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.normalizador import normalizar_respuestas_dict
from src.utils import DOMINIOS

RAADS_PUNTO_CORTE = 65
RAADS_MAX         = 240   # 80 ítems × 3

PESOS_DEFAULT: dict[int, float] = {1: 1.0, 3: 1.0}


# ── Interpretación ─────────────────────────────────────────────────────────────

def interpretar_media(media: float | None) -> tuple[str, str]:
    """
    Devuelve (etiqueta, color_hex) para una media en escala 0-3.

    Rangos (a validar con la psiquiatra):
      [0.00, 0.75)  → Sin indicadores  #4CAF50
      [0.75, 1.50)  → Leves            #8BC34A
      [1.50, 2.25)  → Moderados        #FF9800
      [2.25, 3.00]  → Significativos   #F44336
    """
    if media is None:
        return "Sin datos", "#9E9E9E"
    if media < 0.75:
        return "Sin indicadores", "#4CAF50"
    if media < 1.50:
        return "Leves", "#8BC34A"
    if media < 2.25:
        return "Moderados", "#FF9800"
    return "Significativos", "#F44336"


def interpretar_raads(puntuacion: int) -> tuple[str, str]:
    if puntuacion >= RAADS_PUNTO_CORTE:
        return f"Por encima del punto de corte ({RAADS_PUNTO_CORTE})", "#F44336"
    return f"Por debajo del punto de corte ({RAADS_PUNTO_CORTE})", "#4CAF50"


# ── Cálculo por test ───────────────────────────────────────────────────────────

def _agrupar_por_dominio(
    norm: dict[int, int],
    df_test: pd.DataFrame,
) -> dict[str, dict]:
    """
    Agrupa puntuaciones normalizadas por dominio.

    Returns
    -------
    {dominio: {"media": float|None, "n": int, "valores": list[int]}}
    """
    resultado: dict[str, dict] = {}
    for dom in DOMINIOS:
        ids_dom = df_test.loc[df_test["dominio"] == dom, "id"].tolist()
        vals    = [norm[pid] for pid in ids_dom if pid in norm]
        resultado[dom] = {
            "media":   float(np.mean(vals)) if vals else None,
            "n":       len(vals),
            "valores": vals,
        }
    return resultado


def calcular_puntuaciones_test(
    test_id: int,
    respuestas: dict[int, int],
    df_preguntas: pd.DataFrame,
) -> dict:
    """
    Calcula puntuaciones para un test individual.

    Returns
    -------
    {
      "por_dominio":      {dominio: {"media", "n", "valores"}},
      "total_items":      int,
      "items_respondidos": int,
      "completado":       bool,
      "raads_bruta":      int | None,   # solo test_id == 3
    }
    """
    df_test  = df_preguntas[df_preguntas["test_id"] == test_id]
    ids_test = set(df_test["id"].tolist())

    # Normalizar solo las respuestas de este test
    norm_all  = normalizar_respuestas_dict(respuestas, df_preguntas)
    norm_test = {k: v for k, v in norm_all.items() if k in ids_test}

    raads_bruta = sum(norm_test.values()) if test_id == 3 else None

    return {
        "por_dominio":       _agrupar_por_dominio(norm_test, df_test),
        "total_items":       len(df_test),
        "items_respondidos": len(norm_test),
        "completado":        len(norm_test) == len(df_test),
        "raads_bruta":       raads_bruta,
    }


# ── Informe global ─────────────────────────────────────────────────────────────

def calcular_puntuaciones(
    respuestas: dict[int, int],
    df_preguntas: pd.DataFrame,
    pesos: dict[int, float] | None = None,
) -> dict:
    """
    Punto de entrada principal. Devuelve el informe completo.

    Parameters
    ----------
    respuestas    : {id_pregunta: valor_raw} para Test1 y RAADS-R
    df_preguntas  : DataFrame completo cargado con cargar_preguntas()
    pesos         : {test_id: peso_float}; por defecto todos = 1.0

    Returns
    -------
    {
      "por_test":             {1: res1, 3: res3},
      "global_por_dominio":   {dominio: {"media_ponderada", "etiqueta", "color", "contribuciones"}},
      "raads_bruta":          int,
      "raads_pct":            float,
      "raads_sobre_corte":    bool,
      "raads_interpretacion": str,
      "raads_color":          str,
      "pesos_usados":         dict,
    }
    """
    if pesos is None:
        pesos = {1: 1.0, 3: 1.0}

    r1 = calcular_puntuaciones_test(1, respuestas, df_preguntas)
    r3 = calcular_puntuaciones_test(3, respuestas, df_preguntas)

    resultados: dict[int, dict | None] = {1: r1, 3: r3}

    # ── Media ponderada global por dominio ────────────────────────────────────
    global_por_dominio: dict[str, dict] = {}
    for dom in DOMINIOS:
        aportaciones: list[tuple[float, float]] = []
        contribuciones: dict[int, float | None] = {}

        for tid, res in resultados.items():
            if res is None:
                contribuciones[tid] = None
                continue
            m = res["por_dominio"][dom]["media"]
            contribuciones[tid] = m
            if m is not None:
                aportaciones.append((m, pesos.get(tid, 1.0)))

        if aportaciones:
            peso_total = sum(p for _, p in aportaciones)
            media_pond = sum(m * p for m, p in aportaciones) / peso_total
        else:
            media_pond = None

        etiqueta, color = interpretar_media(media_pond)
        global_por_dominio[dom] = {
            "media_ponderada": media_pond,
            "etiqueta":        etiqueta,
            "color":           color,
            "contribuciones":  contribuciones,
        }

    # ── RAADS-R bruta ─────────────────────────────────────────────────────────
    raads_bruta  = r3["raads_bruta"] or 0
    raads_interp, raads_color = interpretar_raads(raads_bruta)

    return {
        "por_test":             resultados,
        "global_por_dominio":   global_por_dominio,
        "raads_bruta":          raads_bruta,
        "raads_pct":            raads_bruta / RAADS_MAX,
        "raads_sobre_corte":    raads_bruta >= RAADS_PUNTO_CORTE,
        "raads_interpretacion": raads_interp,
        "raads_color":          raads_color,
        "pesos_usados":         pesos,
    }
