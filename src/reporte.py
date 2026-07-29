"""
reporte.py - Generacion de informe PDF con ReportLab.
 
Contenido del PDF
-----------------
  1. Encabezado + advertencia clinica
  2. Perfil global por dominio (tabla + grafica radar)
  3. Comparacion por test (grafica de barras)
  4. Puntuacion RAADS-R
  5. Puntuacion AQ-10
  6. Detalle por test y dominio
  7. Referencias y pie de pagina
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
    Table, TableStyle, HRFlowable, Image, KeepTogether,
)

from pathlib import Path
 
from src.calculador import (
    interpretar_media, RAADS_PUNTO_CORTE, RAADS_MAX,
    AQ10_PUNTO_CORTE, AQ10_MAX, calcular_score_global,
)
from src.utils import DOMINIOS, NOMBRES_TEST
from src.visualizador import crear_radar, crear_barras_por_test
 
# ── Paleta ─────────────────────────────────────────────────────────────────────
_AZUL      = colors.HexColor("#4C72B0")
_AZUL_CLARO= colors.HexColor("#EEF2FA")
_GRIS      = colors.HexColor("#F5F5F5")
_ROJO      = colors.HexColor("#C44E52")
 
_COLORES_NIVEL = {
    "Sin indicadores": colors.HexColor("#4CAF50"),
    "Leves":           colors.HexColor("#8BC34A"),
    "Moderados":       colors.HexColor("#FF9800"),
    "Significativos":  colors.HexColor("#F44336"),
    "Sin datos":       colors.HexColor("#9E9E9E"),
}
_DOM_LABEL = {
    "Social":       "Social",
    "Comunicacion": "Comunicacion",
    "Sensorial":    "Sensorial",
    "Intereses":    "Intereses",
}
 
# ── Estilos ────────────────────────────────────────────────────────────────────
_BASE = getSampleStyleSheet()
 
_ST = {
    "titulo":   ParagraphStyle("titulo", parent=_BASE["Title"],
                               fontSize=18, textColor=_AZUL, spaceAfter=2),
    "subtitulo":ParagraphStyle("subtitulo", parent=_BASE["Normal"],
                               fontSize=10, textColor=colors.HexColor("#555"),
                               spaceAfter=4),
    "h2":       ParagraphStyle("h2", parent=_BASE["Heading2"],
                               fontSize=12, textColor=_AZUL,
                               spaceBefore=14, spaceAfter=4),
    "h3":       ParagraphStyle("h3", parent=_BASE["Heading3"],
                               fontSize=10, textColor=colors.HexColor("#333"),
                               spaceBefore=8, spaceAfter=3),
    "normal":   _BASE["Normal"],
    "small":    ParagraphStyle("small", parent=_BASE["Normal"],
                               fontSize=8, textColor=colors.grey),
    "aviso":    ParagraphStyle("aviso", parent=_BASE["Normal"],
                               fontSize=8, textColor=colors.HexColor("#444"),
                               borderColor=colors.HexColor("#FF9800"),
                               borderWidth=0.6, borderPadding=6,
                               backColor=colors.HexColor("#FFF8E1")),
    "ref":      ParagraphStyle("ref", parent=_BASE["Normal"],
                               fontSize=7, textColor=colors.HexColor("#666"),
                               leftIndent=10, spaceAfter=2),
}
 
_ESTILO_TABLA_BASE = [
    ("BACKGROUND",    (0, 0), (-1, 0), _AZUL),
    ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
    ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE",      (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _GRIS]),
    ("GRID",          (0, 0), (-1, -1), 0.35, colors.HexColor("#CCCCCC")),
    ("TOPPADDING",    (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
]
 
 
def _fig_a_imagen(fig, ancho_cm: float, alto_cm: float) -> Image | None:
    """Convierte una figura Plotly a Image de ReportLab via kaleido."""
    try:
        png = fig.to_image(format="png", width=int(ancho_cm * 37.8),
                           height=int(alto_cm * 37.8), scale=2)
        buf = io.BytesIO(png)
        return Image(buf, width=ancho_cm * cm, height=alto_cm * cm)
    except Exception:
        return None
 
 
def _tabla_corte(label: str, bruta: int, maximo: int,
                 corte: int, sobre: bool, color_hex: str,
                 referencia: str) -> list:
    """Genera tabla estandar de puntuacion bruta vs corte."""
    estado  = "POR ENCIMA del punto de corte" if sobre else "Por debajo del punto de corte"
    c_color = colors.HexColor(color_hex)
    datos   = [
        ["Puntuacion bruta", "Punto de corte", "Maximo", "Resultado"],
        [str(bruta), str(corte), str(maximo), estado],
    ]
    t = Table(datos, colWidths=[3.5*cm, 3.5*cm, 3.0*cm, 6.0*cm])
    s = TableStyle(_ESTILO_TABLA_BASE + [
        ("ALIGN",     (0, 0), (-1, -1), "CENTER"),
        ("TEXTCOLOR", (3, 1), (3, 1),   c_color),
        ("FONTNAME",  (3, 1), (3, 1),   "Helvetica-Bold"),
    ])
    t.setStyle(s)
    return [t, Paragraph(referencia, _ST["ref"]), Spacer(1, 0.3*cm)]
 
 
def generar_pdf(resultado: dict, nombre_evaluado: str = "") -> bytes:
    """
    Genera el PDF y devuelve los bytes listos para st.download_button.
 
    Parameters
    ----------
    resultado       : dict devuelto por calculador.calcular_puntuaciones()
    nombre_evaluado : nombre / codigo de paciente (opcional)
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm,  bottomMargin=2.5*cm,
    )
 
    e = []
 
    # ── 0. Encabezado ──────────────────────────────────────────────────────────
    logo_path = Path(__file__).parent.parent / "assets" / "logo.jpeg"

    # Logo primero (arriba, alineado a la derecha o centrado)
    if logo_path.exists():
        logo_img = Image(str(logo_path), width=7*cm, height=2.7*cm)
        # Alinear a la derecha: usamos una tabla con una fila y una columna, alineada a la derecha
        logo_table = Table([[logo_img]], colWidths=[18*cm])
        logo_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('TOPPADDING', (0, 0), (0, 0), 0),
            ('BOTTOMPADDING', (0, 0), (0, 0), 2),  # pequeño espacio después del logo
        ]))
        e.append(logo_table)
    else:
        # Si no hay logo, no añadimos nada
        pass
    
    # Ahora el título y la información
    e.append(Paragraph("Informe de Evaluacion - Espectro Autista", _ST["titulo"]))
    e.append(Paragraph("Basado en el DSM-5", _ST["subtitulo"]))
    if nombre_evaluado:
        e.append(Paragraph(f"Evaluado/a: <b>{nombre_evaluado}</b>", _ST["normal"]))
    e.append(Paragraph(
        f"Fecha de evaluacion: {datetime.now().strftime('%d/%m/%Y  %H:%M')}",
        _ST["small"],
    ))
    
    # Línea decorativa después del encabezado
    e.append(HRFlowable(width="100%", thickness=1.5, color=_AZUL, spaceAfter=8))
 
    # ── 1. Advertencia clinica ─────────────────────────────────────────────────
    e.append(Paragraph(
        "<b>Nota clinica:</b> Este informe es un apoyo a la evaluacion clinica y "
        "<b>no constituye un diagnostico</b>. Los resultados deben interpretarse "
        "por un profesional de salud mental cualificado. Los instrumentos incluidos "
        "son herramientas de tamizaje, no de diagnostico formal.",
        _ST["aviso"],
    ))
    e.append(Spacer(1, 0.5*cm))
 
    # ── 2. Perfil global por dominio ───────────────────────────────────────────
    e.append(Paragraph("1. Perfil global por dominio", _ST["h2"]))
 
    glob = resultado["global_por_dominio"]
    datos_glob = [["Dominio", "Media (0-3)", "Nivel de indicadores"]]
    for dom in DOMINIOS:
        m = glob[dom]["media_ponderada"]
        etiq, _ = interpretar_media(m)
        datos_glob.append([_DOM_LABEL[dom], f"{m:.2f}" if m is not None else "-", etiq])
 
    t_glob = Table(datos_glob, colWidths=[4.5*cm, 3.5*cm, 8.0*cm])
    s_g = TableStyle(_ESTILO_TABLA_BASE + [("ALIGN", (1, 0), (1, -1), "CENTER")])
    for i, dom in enumerate(DOMINIOS, 1):
        c = _COLORES_NIVEL.get(datos_glob[i][2], colors.black)
        s_g.add("TEXTCOLOR", (2, i), (2, i), c)
        s_g.add("FONTNAME",  (2, i), (2, i), "Helvetica-Bold")
    t_glob.setStyle(s_g)
    e += [t_glob, Spacer(1, 0.4*cm)]
 
    # Leyenda de niveles
    leyenda = [["Nivel", "Rango (media 0-3)", "Interpretacion orientativa"]]
    for nivel, rango, interp in [
        ("Sin indicadores", "0.00 - 0.74", "Sin senales de dificultad en el dominio"),
        ("Leves",           "0.75 - 1.49", "Algunas dificultades leves o subclinicas"),
        ("Moderados",       "1.50 - 2.24", "Dificultades moderadas que merecen atencion"),
        ("Significativos",  "2.25 - 3.00", "Dificultades marcadas, relevancia clinica alta"),
    ]:
        leyenda.append([nivel, rango, interp])
 
    t_ley = Table(leyenda, colWidths=[3.5*cm, 3.5*cm, 9.0*cm])
    s_l = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
    ])
    for i, (nivel, _, _2) in enumerate(
        [("Sin indicadores","",""), ("Leves","",""),
         ("Moderados","",""), ("Significativos","","")], 1
    ):
        c = _COLORES_NIVEL.get(nivel, colors.black)
        s_l.add("TEXTCOLOR", (0, i), (0, i), c)
        s_l.add("FONTNAME",  (0, i), (0, i), "Helvetica-Bold")
    t_ley.setStyle(s_l)
    e.append(Paragraph("Rangos de interpretacion (orientativos, pendientes de validacion normativa):",
                        _ST["small"]))
    e += [t_ley, Spacer(1, 0.5*cm)]

    # ── 3. Score global ───────────────────────────────────────────────────────────
    score_info = calcular_score_global(resultado)
    if score_info["score"] is not None:
        e.append(Paragraph("Score Global (promedio de dominios)", _ST["h2"]))

        estado_texto = "POR ENCIMA del punto de corte" if score_info["sobre_corte"] else "Por debajo del punto de corte"
        estado_color = "#F44336" if score_info["sobre_corte"] else "#4CAF50"  # Rojo o Verde

        datos_score = [
            ["Concepto", "Valor"],
            ["Score global", f"{score_info['score']:.2f} / 3.00"],
            ["Punto de corte", "1.50"],
            ["Nivel", score_info["nivel"]],
            ["Estado", "Por encima del corte" if score_info["sobre_corte"] else "Por debajo del corte"],
        ]
        t_score = Table(datos_score, colWidths=[5*cm, 10*cm])
        s_score = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _GRIS]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ])
        nivel_color = score_info["color"]  # Ej: "#4CAF50", "#FF9800", etc.
        s_score.add("TEXTCOLOR", (1, 3), (1, 3), colors.HexColor(nivel_color))
        s_score.add("FONTNAME", (1, 3), (1, 3), "Helvetica-Bold")
        s_score.add("TEXTCOLOR", (1, 4), (1, 4), colors.HexColor(estado_color))
        s_score.add("FONTNAME", (1, 4), (1, 4), "Helvetica-Bold")

        t_score.setStyle(s_score)
        e.append(t_score)
        e.append(Spacer(1, 0.3*cm))
        e.append(Paragraph(
            f"Basado en {score_info['n_dominios']} dominio(s): "
            f"{', '.join(score_info['dominios_usados'])}",
            _ST["small"],
        ))
        e.append(Spacer(1, 0.5*cm))
    else:
        e.append(Paragraph(
            "No hay suficientes datos para calcular el score global.",
            _ST["normal"],
        ))
        e.append(Spacer(1, 0.5*cm))
 
    # ── 4. Graficas ────────────────────────────────────────────────────────────
    e.append(Paragraph("2. Visualizacion del perfil", _ST["h2"]))
 
    fig_radar  = crear_radar(glob)
    fig_barras = crear_barras_por_test(resultado["por_test"])
    img_radar  = _fig_a_imagen(fig_radar,  8.0, 7.0)
    img_barras = _fig_a_imagen(fig_barras, 8.0, 7.0)
 
    if img_radar and img_barras:
        fila_graficas = Table([[img_radar, img_barras]],
                               colWidths=[8.5*cm, 8.5*cm])
        fila_graficas.setStyle(TableStyle([
            ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        e += [fila_graficas, Spacer(1, 0.3*cm)]
    elif img_radar:
        e += [img_radar, Spacer(1, 0.3*cm)]
 
    e.append(Paragraph(
        "Izquierda: perfil global por dominio (radar). "
        "Derecha: comparacion de medias por test y dominio. "
        "La linea discontinua roja indica el nivel moderado (1.5).",
        _ST["small"],
    ))
    e.append(Spacer(1, 0.5*cm))
 
    # ── 5. RAADS-R ─────────────────────────────────────────────────────────────
    e.append(Paragraph("3. Puntuacion RAADS-R", _ST["h2"]))
    e += _tabla_corte(
        label="RAADS-R",
        bruta=resultado["raads_bruta"],
        maximo=RAADS_MAX,
        corte=RAADS_PUNTO_CORTE,
        sobre=resultado["raads_sobre_corte"],
        color_hex=resultado["raads_color"],
        referencia="Ritvo et al. (2011): sensibilidad 97%, especificidad 100%, "
                   f"corte = {RAADS_PUNTO_CORTE}/240. Escala: 0-3 por item (80 items).",
    )
 
    # ── 6. AQ-10 ───────────────────────────────────────────────────────────────
    e.append(Paragraph("4. Puntuacion AQ-10 (Baron-Cohen)", _ST["h2"]))
    e += _tabla_corte(
        label="AQ-10",
        bruta=resultado["aq10_bruta"],
        maximo=AQ10_MAX,
        corte=AQ10_PUNTO_CORTE,
        sobre=resultado["aq10_sobre_corte"],
        color_hex=resultado["aq10_color"],
        referencia="Allison et al. (2012): punto de corte >= 6/10 indica derivacion "
                   "para evaluacion diagnostica formal. No constituye diagnostico.",
    )
 
    # ── 7. Detalle por test y dominio ──────────────────────────────────────────
    e.append(Paragraph("5. Detalle por test y dominio", _ST["h2"]))
    por_test  = resultado["por_test"]
    datos_det = [["Dominio", "Test 1", "RAADS-R", "AQ-10"]]
    for dom in DOMINIOS:
        fila = [_DOM_LABEL[dom]]
        for tid in [1, 3, 4]:
            res = por_test.get(tid)
            if res is None:
                fila.append("-")
            else:
                m = res["por_dominio"][dom]["media"]
                fila.append(f"{m:.2f}" if m is not None else "-")
        datos_det.append(fila)
 
    t_det = Table(datos_det, colWidths=[5*cm, 3.5*cm, 3.5*cm, 4*cm])
    t_det.setStyle(TableStyle(_ESTILO_TABLA_BASE + [
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    e += [t_det, Spacer(1, 0.6*cm)]
 
    # ── 8. Referencias y pie ───────────────────────────────────────────────────
    e.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=6))
    e.append(Paragraph("<b>Instrumentos e instrumentacion:</b>", _ST["small"]))
    refs = [
        "American Psychiatric Association (2013). Diagnostic and Statistical Manual "
        "of Mental Disorders (DSM-5). Washington, DC: APA.",
        "Ritvo, R.A. et al. (2011). The Ritvo Autism Asperger Diagnostic Scale-Revised "
        "(RAADS-R). J Autism Dev Disord, 41(8), 1076-1089.",
        "Allison, C. et al. (2012). The Autism-Spectrum Quotient: 10 items (AQ-10). "
        "PLoS ONE, 7(9), e44229.",
        "Test 1: Cuestionario propio adaptado para evaluacion clinica (DSM-5).",
    ]
    for ref in refs:
        e.append(Paragraph(f"• {ref}", _ST["ref"]))
 
    e.append(Spacer(1, 0.3*cm))
    e.append(Paragraph(
        "Sistema Integrado de Evaluacion TEA  |  Solo para uso clinico/investigacion  |  "
        "No constituye diagnostico",
        _ST["small"],
    ))
 
    doc.build(e)
    return buf.getvalue()