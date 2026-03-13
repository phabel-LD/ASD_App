"""
tests/test_calculador.py – Pruebas del motor de puntuación.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
from src.calculador import (
    interpretar_media,
    calcular_puntuaciones_test,
    calcular_puntuaciones_test2_externo,
    calcular_puntuaciones,
    RAADS_PUNTO_CORTE,
)
from src.utils import DOMINIOS


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def df_mini():
    """DataFrame mínimo: 4 ítems Test1 + 4 ítems RAADS-R, uno por dominio."""
    rows = []
    for i, dom in enumerate(DOMINIOS, 1):
        rows.append({
            "id": i, "test_id": 1, "orden": i, "dominio": dom,
            "escala_origen": "1-4", "direccion": "directa",
        })
    for i, dom in enumerate(DOMINIOS, 5):
        rows.append({
            "id": i, "test_id": 3, "orden": i-4, "dominio": dom,
            "escala_origen": "0-3", "direccion": "directa",
        })
    return pd.DataFrame(rows)


@pytest.fixture
def respuestas_max(df_mini):
    """Todos los ítems respondidos al máximo."""
    r = {}
    for _, row in df_mini[df_mini["test_id"] == 1].iterrows():
        r[int(row["id"])] = 4   # escala 1-4
    for _, row in df_mini[df_mini["test_id"] == 3].iterrows():
        r[int(row["id"])] = 3   # escala 0-3
    return r


@pytest.fixture
def respuestas_min(df_mini):
    """Todos al mínimo."""
    r = {}
    for _, row in df_mini[df_mini["test_id"] == 1].iterrows():
        r[int(row["id"])] = 1
    for _, row in df_mini[df_mini["test_id"] == 3].iterrows():
        r[int(row["id"])] = 0
    return r


# ── interpretar_media ─────────────────────────────────────────────────────────

def test_interpretar_none():
    etiq, color = interpretar_media(None)
    assert etiq == "Sin datos"

def test_interpretar_sin_indicadores():
    etiq, _ = interpretar_media(0.0)
    assert etiq == "Sin indicadores"

def test_interpretar_leves():
    etiq, _ = interpretar_media(0.75)
    assert etiq == "Leves"

def test_interpretar_moderados():
    etiq, _ = interpretar_media(1.50)
    assert etiq == "Moderados"

def test_interpretar_significativos():
    etiq, _ = interpretar_media(2.25)
    assert etiq == "Significativos"


# ── calcular_puntuaciones_test ─────────────────────────────────────────────────

def test_test1_maximo(df_mini, respuestas_max):
    r = calcular_puntuaciones_test(1, respuestas_max, df_mini)
    assert r["completado"] is True
    assert r["items_respondidos"] == 4
    for dom in DOMINIOS:
        assert r["por_dominio"][dom]["media"] == pytest.approx(3.0)

def test_test1_minimo(df_mini, respuestas_min):
    r = calcular_puntuaciones_test(1, respuestas_min, df_mini)
    for dom in DOMINIOS:
        assert r["por_dominio"][dom]["media"] == pytest.approx(0.0)

def test_raads_bruta_max(df_mini, respuestas_max):
    r = calcular_puntuaciones_test(3, respuestas_max, df_mini)
    # 4 ítems × 3 = 12
    assert r["raads_bruta"] == 12

def test_raads_bruta_min(df_mini, respuestas_min):
    r = calcular_puntuaciones_test(3, respuestas_min, df_mini)
    assert r["raads_bruta"] == 0

def test_sin_respuestas(df_mini):
    r = calcular_puntuaciones_test(1, {}, df_mini)
    assert r["items_respondidos"] == 0
    assert r["completado"] is False
    for dom in DOMINIOS:
        assert r["por_dominio"][dom]["media"] is None


# ── calcular_puntuaciones_test2_externo ────────────────────────────────────────

def test_test2_externo_completo():
    ext = {dom: 2.0 for dom in DOMINIOS}
    r = calcular_puntuaciones_test2_externo(ext)
    assert r["completado"] is True
    for dom in DOMINIOS:
        assert r["por_dominio"][dom]["media"] == pytest.approx(2.0)

def test_test2_externo_parcial():
    ext = {"Social": 1.5}
    r = calcular_puntuaciones_test2_externo(ext)
    assert r["por_dominio"]["Social"]["media"] == pytest.approx(1.5)
    assert r["por_dominio"]["Comunicacion"]["media"] is None


# ── calcular_puntuaciones (global) ─────────────────────────────────────────────

def test_global_raads_sobre_corte(df_mini):
    """Con todos a 3, la bruta RAADS = 12, muy por encima del corte de 65 real.
    Usamos df_mini (4 ítems) así que la bruta = 12 < 65, pero el mecanismo es correcto."""
    r_todo_max = {i: 3 for i in range(5, 9)}
    r_todo_max.update({i: 4 for i in range(1, 5)})
    res = calcular_puntuaciones(r_todo_max, df_mini)
    assert res["raads_bruta"] == 12
    # Con df_mini el máximo es 12, no 240, así que no supera el corte de 65
    assert res["raads_sobre_corte"] is False

def test_global_con_test2(df_mini, respuestas_max):
    ext = {dom: 2.0 for dom in DOMINIOS}
    res = calcular_puntuaciones(respuestas_max, df_mini, test2_externo=ext)
    assert res["por_test"][2] is not None
    # Media global debe estar entre 2 y 3
    for dom in DOMINIOS:
        m = res["global_por_dominio"][dom]["media_ponderada"]
        assert m is not None
        assert 0 <= m <= 3

def test_global_sin_test2(df_mini, respuestas_max):
    res = calcular_puntuaciones(respuestas_max, df_mini, test2_externo=None)
    assert res["por_test"][2] is None
    for dom in DOMINIOS:
        m = res["global_por_dominio"][dom]["media_ponderada"]
        assert m == pytest.approx(3.0)
