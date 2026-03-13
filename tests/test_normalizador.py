"""
tests/test_normalizador.py – Pruebas unitarias del módulo normalizador.

Ejecutar con:
    pytest tests/
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.normalizador import normalizar_a_0_3, normalizar_respuestas_dict
import pandas as pd


# ── normalizar_a_0_3 ──────────────────────────────────────────────────────────

class TestNormalizarA03:

    # Escala 1-4 directa
    def test_escala14_directa_minimo(self):
        assert normalizar_a_0_3(1, "1-4", "directa") == 0

    def test_escala14_directa_maximo(self):
        assert normalizar_a_0_3(4, "1-4", "directa") == 3

    def test_escala14_directa_medios(self):
        assert normalizar_a_0_3(2, "1-4", "directa") == 1
        assert normalizar_a_0_3(3, "1-4", "directa") == 2

    # Escala 1-4 inversa
    def test_escala14_inversa_minimo(self):
        # raw=1 → norm=0 → 3-0=3
        assert normalizar_a_0_3(1, "1-4", "inversa") == 3

    def test_escala14_inversa_maximo(self):
        # raw=4 → norm=3 → 3-3=0
        assert normalizar_a_0_3(4, "1-4", "inversa") == 0

    def test_escala14_inversa_medios(self):
        assert normalizar_a_0_3(2, "1-4", "inversa") == 2
        assert normalizar_a_0_3(3, "1-4", "inversa") == 1

    # Escala 0-3 directa
    def test_escala03_directa_minimo(self):
        assert normalizar_a_0_3(0, "0-3", "directa") == 0

    def test_escala03_directa_maximo(self):
        assert normalizar_a_0_3(3, "0-3", "directa") == 3

    # Escala 0-3 inversa
    def test_escala03_inversa_minimo(self):
        # raw=0 → norm=0 → 3-0=3
        assert normalizar_a_0_3(0, "0-3", "inversa") == 3

    def test_escala03_inversa_maximo(self):
        # raw=3 → norm=3 → 3-3=0
        assert normalizar_a_0_3(3, "0-3", "inversa") == 0

    # Siempre en rango [0, 3]
    def test_clip_inferior(self):
        # No debería ocurrir en uso normal, pero el clip lo protege
        assert 0 <= normalizar_a_0_3(0, "0-3", "directa") <= 3

    def test_clip_superior(self):
        assert 0 <= normalizar_a_0_3(3, "0-3", "directa") <= 3


# ── normalizar_respuestas_dict ────────────────────────────────────────────────

class TestNormalizarRespuestasDict:

    @pytest.fixture
    def df_mock(self):
        return pd.DataFrame([
            {"id": 1, "test_id": 1, "escala_origen": "1-4", "direccion": "directa"},
            {"id": 2, "test_id": 1, "escala_origen": "1-4", "direccion": "inversa"},
            {"id": 3, "test_id": 3, "escala_origen": "0-3", "direccion": "directa"},
            {"id": 4, "test_id": 3, "escala_origen": "0-3", "direccion": "inversa"},
        ])

    def test_normaliza_correctamente(self, df_mock):
        respuestas = {1: 1, 2: 1, 3: 0, 4: 0}
        norm = normalizar_respuestas_dict(respuestas, df_mock)
        assert norm[1] == 0   # 1-4 directa: 1-1=0
        assert norm[2] == 3   # 1-4 inversa: 3-(1-1)=3
        assert norm[3] == 0   # 0-3 directa: 0
        assert norm[4] == 3   # 0-3 inversa: 3-0=3

    def test_ignora_ids_inexistentes(self, df_mock):
        respuestas = {1: 2, 99: 3}   # 99 no existe en df_mock
        norm = normalizar_respuestas_dict(respuestas, df_mock)
        assert 99 not in norm
        assert 1 in norm

    def test_dict_vacio(self, df_mock):
        norm = normalizar_respuestas_dict({}, df_mock)
        assert norm == {}
