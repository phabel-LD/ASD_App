"""
reporte.py – Generación de informe PDF con ReportLab.

Contenido del PDF
-----------------
  1. Encabezado + advertencia clínica
  2. Perfil global por dominio (tabla con nivel e interpretación)
  3. Puntuación bruta RAADS-R vs. punto de corte
  4. Tabla de detalle por test y dominio
  5. Pie de página
"""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable,
)

from src.calculador import interpretar_media, RAADS_PUNTO_CORTE, RAADS_MAX
from src.utils import DOMINIOS, NOMBRES_TEST

# ── Paleta ─────────────────────────────────────────────────────────────────────
_AZUL   = colors.HexColor("#4C72B0")
_GRIS   = colors.HexColor("#F5F5F5")
_COLORES_NIVEL = {
    "Sin indicadores": colors.HexColor("#4CAF50"),
    "Leves":           colors.HexColor("#8BC34A"),
    "Moderados":       colors.HexColor("#FF9800"),
    "Significativos":  colors.HexColor("#F44336"),
    "Sin datos":       colors.HexColor("#9E9E9E"),
}
_DOM_LABEL = {
    "Social": "Social", "Comunicacion": "Comunicación",
    "Sensorial": "Sensorial", "Intereses": "Intereses",
}

# ── Estilos ────────────────────────────────────────────────────────────────────
_BASE = getSampleStyleSheet()

_ST = {
    "titulo": ParagraphStyle("titulo", parent=_BASE["Title"],
                             fontSize=17, textColor=_AZUL, spaceAfter=4),
    "h2":     ParagraphStyle("h2", parent=_BASE["Heading2"],
                             fontSize=12, textColor=_AZUL, spaceBefore=12, spaceAfter=3),
    "normal": _BASE["Normal"],
    "small":  ParagraphStyle("small", parent=_BASE["Normal"],
                             fontSize=8, textColor=colors.grey),
    "aviso":  ParagraphStyle("aviso", parent=_BASE["Normal"],
                             fontSize=8, textColor=colors.HexColor("#444"),
                             borderColor=colors.HexColor("#FF9800"),
                             borderWidth=0.6, borderPadding=5,
                             backColor=colors.HexColor("#FFF8E1")),
}

_ESTILO_TABLA_BASE = [
    ("BACKGROUND",   (0, 0), (-1, 0), _AZUL),
    ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
    ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE",     (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _GRIS]),
    ("GRID",         (0, 0), (-1, -1), 0.35, colors.HexColor("#CCCCCC")),
    ("TOPPADDING",   (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
]


def generar_pdf(resultado: dict, nombre_evaluado: str = "") -> bytes:
    """
    Genera el PDF y devuelve los bytes listos para st.download_button.

    Parameters
    ----------
    resultado       : dict devuelto por calculador.calcular_puntuaciones()
    nombre_evaluado : nombre / código de paciente (opcional)
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm,  bottomMargin=2.5*cm,
    )

    e = []   # elementos

    # ── 0. Encabezado ──────────────────────────────────────────────────────────
    e.append(Paragraph("Informe de Evaluación – Espectro Autista", _ST["titulo"]))
    if nombre_evaluado:
        e.append(Paragraph(f"Evaluado/a: <b>{nombre_evaluado}</b>", _ST["normal"]))
    e.append(Paragraph(
        f"Fecha: {datetime.now().strftime('%d/%m/%Y  %H:%M')}",
        _ST["small"],
    ))
    e.append(HRFlowable(width="100%", thickness=1, color=_AZUL, spaceAfter=8))

    # ── 1. Advertencia clínica ─────────────────────────────────────────────────
    e.append(Paragraph(
        "⚠️ <b>Nota clínica:</b> Este informe es un apoyo a la evaluación y "
        "<b>no constituye un diagnóstico</b>. Los resultados deben interpretarse "
        "siempre por un profesional de salud mental cualificado.",
        _ST["aviso"],
    ))
    e.append(Spacer(1, 0.4*cm))

    # ── 2. Perfil global por dominio ───────────────────────────────────────────
    e.append(Paragraph("1. Perfil global por dominio", _ST["h2"]))

    glob = resultado["global_por_dominio"]
    datos_glob = [["Dominio", "Media (0–3)", "Nivel"]]
    for dom in DOMINIOS:
        m = glob[dom]["media_ponderada"]
        etiq, _ = interpretar_media(m)
        datos_glob.append([_DOM_LABEL[dom], f"{m:.2f}" if m is not None else "—", etiq])

    t_glob = Table(datos_glob, colWidths=[5*cm, 4*cm, 6*cm])
    s = TableStyle(_ESTILO_TABLA_BASE + [("ALIGN", (1, 0), (1, -1), "CENTER")])
    for i, dom in enumerate(DOMINIOS, 1):
        c = _COLORES_NIVEL.get(datos_glob[i][2], colors.black)
        s.add("TEXTCOLOR", (2, i), (2, i), c)
        s.add("FONTNAME",  (2, i), (2, i), "Helvetica-Bold")
    t_glob.setStyle(s)
    e += [t_glob, Spacer(1, 0.4*cm)]

    # ── 3. RAADS-R ─────────────────────────────────────────────────────────────
    e.append(Paragraph("2. Puntuación RAADS-R", _ST["h2"]))
    raads  = resultado["raads_bruta"]
    sobre  = resultado["raads_sobre_corte"]
    estado = "POR ENCIMA del punto de corte" if sobre else "Por debajo del punto de corte"
    c_raads = colors.HexColor(resultado["raads_color"])

    datos_raads = [
        ["Puntuación bruta", "Punto de corte", "Máximo", "Resultado"],
        [str(raads), str(RAADS_PUNTO_CORTE), str(RAADS_MAX), estado],
    ]
    t_raads = Table(datos_raads, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 5.5*cm])
    s_r = TableStyle(_ESTILO_TABLA_BASE + [
        ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
        ("TEXTCOLOR", (3, 1), (3, 1),  c_raads),
        ("FONTNAME",  (3, 1), (3, 1),  "Helvetica-Bold"),
    ])
    t_raads.setStyle(s_r)
    e += [t_raads, Spacer(1, 0.4*cm)]

    # ── 4. Detalle por test y dominio ──────────────────────────────────────────
    e.append(Paragraph("3. Detalle por test y dominio", _ST["h2"]))
    por_test = resultado["por_test"]
    datos_det = [["Dominio", "Test 1", "RAADS-R"]]
    for dom in DOMINIOS:
        fila = [_DOM_LABEL[dom]]
        for tid in [1, 3]:
            res = por_test.get(tid)
            if res is None:
                fila.append("—")
            else:
                m = res["por_dominio"][dom]["media"]
                fila.append(f"{m:.2f}" if m is not None else "—")
        datos_det.append(fila)

    t_det = Table(datos_det, colWidths=[5*cm, 4*cm, 4*cm])
    t_det.setStyle(TableStyle(_ESTILO_TABLA_BASE + [
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    e += [t_det, Spacer(1, 0.6*cm)]

    # ── 5. Pie ─────────────────────────────────────────────────────────────────
    e.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    e.append(Paragraph(
        "Sistema Integrado de Evaluación TEA · Solo para uso clínico/investigación · "
        "No constituye diagnóstico · "
        "RAADS-R: Ritvo et al., 2011 (sensibilidad 97%, especificidad 100%, corte = 65/240).",
        _ST["small"],
    ))

    doc.build(e)
    return buf.getvalue()
