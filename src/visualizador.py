"""
visualizador.py – Gráficos Plotly para el informe.

Funciones públicas
------------------
crear_radar(global_por_dominio)             → figura radar global
crear_barras_por_test(resultados_por_test)  → barras agrupadas por test
crear_gauge_raads(raads_bruta)              → gauge RAADS-R
crear_tabla_detalles(resultados_por_test)   → lista de dicts para st.dataframe
"""
from __future__ import annotations

import plotly.graph_objects as go

from src.utils import DOMINIOS, NOMBRES_TEST, COLORES_TEST
from src.calculador import RAADS_PUNTO_CORTE, RAADS_MAX, AQ10_PUNTO_CORTE, AQ10_MAX, interpretar_media

_LABELS = {
    "Social":       "Social",
    "Comunicacion": "Comunicación",
    "Sensorial":    "Sensorial",
    "Intereses":    "Intereses",
}


# ── Radar ──────────────────────────────────────────────────────────────────────

def crear_radar(global_por_dominio: dict) -> go.Figure:
    """Radar chart del perfil global (media ponderada), eje 0-3."""
    labels  = [_LABELS[d] for d in DOMINIOS]
    valores = [global_por_dominio[d]["media_ponderada"] or 0 for d in DOMINIOS]

    # Cerrar el polígono
    lc = labels  + [labels[0]]
    vc = valores + [valores[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vc, theta=lc, fill="toself",
        fillcolor="rgba(76,114,176,0.20)",
        line=dict(color="#4C72B0", width=2.5),
        name="Perfil global",
        hovertemplate="%{theta}: <b>%{r:.2f}</b><extra></extra>",
    ))
    # Línea de referencia nivel moderado
    ref = [1.5] * (len(labels) + 1)
    fig.add_trace(go.Scatterpolar(
        r=ref, theta=lc, mode="lines",
        line=dict(color="rgba(200,0,0,0.35)", dash="dash", width=1.2),
        name="Nivel moderado (1.5)",
        hoverinfo="skip",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 3], tickfont_size=10)),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, font_size=11),
        margin=dict(t=50, b=70, l=60, r=60),
        height=390,
        title=dict(text="Perfil global por dominio", font_size=14, x=0.5),
    )
    return fig


# ── Barras por test ────────────────────────────────────────────────────────────

def crear_barras_por_test(resultados_por_test: dict) -> go.Figure:
    """Barras agrupadas: un grupo por dominio, una barra por test disponible."""
    fig = go.Figure()
    x_labels = [_LABELS[d] for d in DOMINIOS]

    for tid in [1, 3, 4]:
        res = resultados_por_test.get(tid)
        if res is None:
            continue
        y = [
            round(res["por_dominio"][d]["media"], 3)
            if res["por_dominio"][d]["media"] is not None else 0
            for d in DOMINIOS
        ]
        fig.add_trace(go.Bar(
            name=NOMBRES_TEST[tid],
            x=x_labels, y=y,
            marker_color=COLORES_TEST[tid],
            text=[f"{v:.2f}" if v > 0 else "—" for v in y],
            textposition="outside",
            hovertemplate="%{x}: <b>%{y:.2f}</b><extra>" + NOMBRES_TEST[tid] + "</extra>",
        ))

    fig.add_hline(
        y=1.5, line_dash="dash", line_color="rgba(200,0,0,0.4)",
        annotation_text="Nivel moderado", annotation_position="top right",
        annotation_font_size=10,
    )
    fig.update_layout(
        barmode="group",
        yaxis=dict(range=[0, 3.5], title="Media normalizada (0-3)"),
        xaxis_title="Dominio clínico",
        legend=dict(orientation="h", y=-0.20, font_size=11),
        margin=dict(t=40, b=90, l=55, r=30),
        height=390,
        title=dict(text="Comparación por test y dominio", font_size=14, x=0.5),
    )
    return fig


# ── Gauge RAADS-R ──────────────────────────────────────────────────────────────

def crear_gauge_raads(raads_bruta: int) -> go.Figure:
    """Gauge indicador para la puntuación bruta del RAADS-R (rango 0-240)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=raads_bruta,
        delta={"reference": RAADS_PUNTO_CORTE, "valueformat": ".0f",
               "increasing": {"color": "#F44336"},
               "decreasing": {"color": "#4CAF50"}},
        gauge={
            "axis": {"range": [0, RAADS_MAX], "tickwidth": 1, "tickfont_size": 10},
            "bar":  {"color": "#4C72B0"},
            "steps": [
                {"range": [0,                   RAADS_PUNTO_CORTE], "color": "#E8F5E9"},
                {"range": [RAADS_PUNTO_CORTE,   RAADS_MAX],         "color": "#FFEBEE"},
            ],
            "threshold": {
                "line":      {"color": "#F44336", "width": 3},
                "thickness": 0.80,
                "value":     RAADS_PUNTO_CORTE,
            },
        },
        title={"text": f"RAADS-R &nbsp; (corte: {RAADS_PUNTO_CORTE})", "font": {"size": 14}},
        number={"suffix": f" / {RAADS_MAX}", "font": {"size": 26}},
    ))
    fig.update_layout(height=270, margin=dict(t=65, b=20, l=30, r=30))
    return fig


# ── Gauge AQ-10 ────────────────────────────────────────────────────────────────

def crear_gauge_aq10(aq10_bruta: int) -> go.Figure:
    """Gauge indicador para la puntuación bruta del AQ-10 (rango 0-10)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=aq10_bruta,
        delta={"reference": AQ10_PUNTO_CORTE, "valueformat": ".0f",
               "increasing": {"color": "#F44336"},
               "decreasing": {"color": "#4CAF50"}},
        gauge={
            "axis": {"range": [0, AQ10_MAX], "tickwidth": 1, "tickfont_size": 10},
            "bar":  {"color": "#C44E52"},
            "steps": [
                {"range": [0,                    AQ10_PUNTO_CORTE], "color": "#E8F5E9"},
                {"range": [AQ10_PUNTO_CORTE,     AQ10_MAX],         "color": "#FFEBEE"},
            ],
            "threshold": {
                "line":      {"color": "#F44336", "width": 3},
                "thickness": 0.80,
                "value":     AQ10_PUNTO_CORTE,
            },
        },
        title={"text": f"AQ-10 &nbsp; (corte: {AQ10_PUNTO_CORTE})", "font": {"size": 14}},
        number={"suffix": f" / {AQ10_MAX}", "font": {"size": 26}},
    ))
    fig.update_layout(height=270, margin=dict(t=65, b=20, l=30, r=30))
    return fig

def crear_tabla_detalles(resultados_por_test: dict) -> list[dict]:
    """
    Lista de dicts para st.dataframe.
    Columnas: Dominio | Test 1 | RAADS-R | AQ-10
    """
    filas = []
    for dom in DOMINIOS:
        fila = {"Dominio": _LABELS[dom]}
        for tid, col in [(1, "Test 1"), (3, "RAADS-R"), (4, "AQ-10")]:
            res = resultados_por_test.get(tid)
            if res is None:
                fila[col] = "—"
            else:
                m = res["por_dominio"][dom]["media"]
                fila[col] = f"{m:.2f}" if m is not None else "—"
        filas.append(fila)
    return filas