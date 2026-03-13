"""
normalizador.py – Conversión de respuestas brutas a escala 0-3 unificada.

Reglas:
  Escala 1-4   →  normalizado = raw - 1
  Escala 0-3   →  normalizado = raw  (sin cambio)
  Ítem inverso →  final = 3 - normalizado
"""
import numpy as np
import pandas as pd


def normalizar_a_0_3(valor_raw: int, escala_origen: str, direccion: str) -> int:
    """
    Normaliza un único valor bruto.

    Parameters
    ----------
    valor_raw     : respuesta tal como la registró el usuario
    escala_origen : "1-4"  ó  "0-3"
    direccion     : "directa"  ó  "inversa"

    Returns
    -------
    int en [0, 3]

    Examples
    --------
    >>> normalizar_a_0_3(1, "1-4", "directa")   # mín directo  → 0
    0
    >>> normalizar_a_0_3(4, "1-4", "directa")   # máx directo  → 3
    3
    >>> normalizar_a_0_3(1, "1-4", "inversa")   # mín inverso  → 3
    3
    >>> normalizar_a_0_3(0, "0-3", "inversa")   # mín inverso  → 3
    3
    """
    norm = (int(valor_raw) - 1) if escala_origen == "1-4" else int(valor_raw)
    if direccion == "inversa":
        norm = 3 - norm
    return int(np.clip(norm, 0, 3))


def normalizar_respuestas_dict(
    respuestas: dict[int, int],
    df_preguntas: pd.DataFrame,
) -> dict[int, int]:
    """
    Normaliza un diccionario completo {id_pregunta: valor_raw}.

    Solo procesa los ids que existen en df_preguntas; ignora el resto.

    Returns
    -------
    {id_pregunta: valor_normalizado_0_3}
    """
    lookup = (
        df_preguntas
        .set_index("id")[["escala_origen", "direccion"]]
        .to_dict("index")
    )
    return {
        pid: normalizar_a_0_3(raw, lookup[pid]["escala_origen"], lookup[pid]["direccion"])
        for pid, raw in respuestas.items()
        if pid in lookup
    }
