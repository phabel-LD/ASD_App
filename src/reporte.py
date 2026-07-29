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
    PageBreak,
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

    # ── Interpretación del perfil global ──────────────────────────────────────
    e.append(Paragraph("¿Qué significa este perfil?", _ST["h3"]))
    
    niveles = []
    for dom in DOMINIOS:
        m = resultado["global_por_dominio"][dom]["media_ponderada"]
        if m is not None:
            etiq, _ = interpretar_media(m)
            niveles.append((dom, etiq, m))
    
    if niveles:
        niveles.sort(key=lambda x: x[2] if x[2] is not None else 0, reverse=True)
        mayor = niveles[0]
        texto_perfil = (
            f"En general, tus respuestas muestran que el área con mayor puntuación "
            f"es <b>{mayor[0]}</b>, con un nivel <b>{mayor[1].lower()}</b>. "
            "Esto significa que podrías experimentar más dificultades en esa área "
            "que en las demás. A continuación, te explicamos qué significan los niveles:"
        )
        e.append(Paragraph(texto_perfil, _ST["normal"]))
        e.append(Spacer(1, 0.2*cm))
    
    niveles_texto = (
        "• <b>Sin indicadores</b>: no se observan señales relevantes en esta área.<br/>"
        "• <b>Leves</b>: algunas dificultades que pueden ser normales o subclínicas.<br/>"
        "• <b>Moderados</b>: dificultades que merecen atención y seguimiento.<br/>"
        "• <b>Significativos</b>: señales marcadas que sugieren la necesidad de una evaluación profesional."
    )
    e.append(Paragraph(niveles_texto, _ST["normal"]))
    e.append(Spacer(1, 0.4*cm))

    # ── 3. Score global ───────────────────────────────────────────────────────────
    score_info = calcular_score_global(resultado)

    # Interpretacion del RAADS-R
    raads_bruta = resultado["raads_bruta"]
    raads_sobre = resultado["raads_sobre_corte"]
    e.append(Paragraph("¿Qué significa tu resultado en el RAADS-R?", _ST["h3"]))

    # Interpretacion del AQ-10
    aq10_bruta = resultado["aq10_bruta"]
    aq10_sobre = resultado["aq10_sobre_corte"]
    e.append(Paragraph("¿Qué significa tu resultado en el AQ-10?", _ST["h3"]))

    if score_info["score"] is not None:
        e.append(Paragraph("Score Global (promedio de dominios)", _ST["h2"]))

        estado_texto = "POR ENCIMA del punto de corte" if score_info["sobre_corte"] else "Por debajo del punto de corte"
        estado_color = "#F44336" if score_info["sobre_corte"] else "#4CAF50"  # Rojo o Verde

        datos_score = [
            ["Concepto", "Valor"],
            ["Score global", f"{score_info['score']:.2f} / 3.00"],
            ["Punto de corte", "1.50"],
            ["Nivel", score_info["nivel"]],
            ["Estado", "POR ENCIMA del punto de corte" if score_info["sobre_corte"] else "Por debajo del punto de corte"],
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

    # ── Interpretación del score global ──────────────────────────────────────
    e.append(Paragraph("¿Qué significa tu puntuación global?", _ST["h3"]))
    if score_info["score"] is not None:
        if score_info["sobre_corte"]:
            texto_score = (
                f"Tu puntuación global es <b>{score_info['score']:.2f}</b> sobre 3.00, "
                "lo que está <b>por encima del punto de corte (1.50)</b>. "
                "Esto indica que, en conjunto, tus respuestas reflejan características "
                "que podrían ser compatibles con el espectro autista. "
                "Sería recomendable que un profesional especializado valore tu caso con más detalle."
            )
        else:
            texto_score = (
                f"Tu puntuación global es <b>{score_info['score']:.2f}</b> sobre 3.00, "
                "lo que está <b>por debajo del punto de corte (1.50)</b>. "
                "Esto sugiere que, en general, tus respuestas no muestran una cantidad "
                "de características que indiquen un perfil claramente asociado al espectro autista. "
                "Si tienes dudas o preocupaciones, siempre es bueno consultar con un profesional."
            )
        e.append(Paragraph(texto_score, _ST["normal"]))
        e.append(Spacer(1, 0.4*cm))
    # ── 4. Graficas ────────────────────────────────────────────────────────────
    e.append(Paragraph("2. Visualizacion del perfil", _ST["h2"]))
 
    fig_radar  = crear_radar(glob)
    fig_barras = crear_barras_por_test(resultado["por_test"])
    img_radar  = _fig_a_imagen(fig_radar,  8.0, 7.0)
    img_barras = _fig_a_imagen(fig_barras, 8.0, 9.0)
 
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

    # ── Interpretación del RAADS-R ────────────────────────────────────────────
    e.append(Paragraph("¿Qué significa tu resultado en el RAADS-R?", _ST["h3"]))
    if raads_sobre:
        texto_raads = (
            f"Has obtenido <b>{raads_bruta} puntos</b> de 240 en el RAADS-R. "
            "Este resultado está <b>por encima del punto de corte (65 puntos)</b>. "
            "Esto significa que tus respuestas son similares a las de personas que han recibido "
            "un diagnóstico de autismo. Es importante que un especialista interprete este resultado "
            "en el contexto de tu historia personal y tu desarrollo."
        )
    else:
        texto_raads = (
            f"Has obtenido <b>{raads_bruta} puntos</b> de 240 en el RAADS-R. "
            "Este resultado está <b>por debajo del punto de corte (65 puntos)</b>. "
            "Esto sugiere que tus respuestas no muestran un patrón claramente asociado al autismo. "
            "Recuerda que este es solo un cuestionario de detección, no un diagnóstico."
        )
    e.append(Paragraph(texto_raads, _ST["normal"]))
    e.append(Spacer(1, 0.4*cm))

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

    # ── Interpretación del AQ-10 ──────────────────────────────────────────────
    e.append(Paragraph("¿Qué significa tu resultado en el AQ-10?", _ST["h3"]))
    if aq10_sobre:
        texto_aq = (
            f"Has obtenido <b>{aq10_bruta} puntos</b> de 10 en el AQ-10. "
            "Este resultado está <b>por encima del punto de corte (6 puntos)</b>. "
            "Esto indica que podrías presentar algunas características asociadas al espectro autista. "
            "Sería aconsejable realizar una evaluación más completa con un profesional."
        )
    else:
        texto_aq = (
            f"Has obtenido <b>{aq10_bruta} puntos</b> de 10 en el AQ-10. "
            "Este resultado está <b>por debajo del punto de corte (6 puntos)</b>. "
            "Esto sugiere que tus respuestas no indican una cantidad significativa de características "
            "autistas. Este cuestionario es solo una herramienta de detección rápida."
        )
    e.append(Paragraph(texto_aq, _ST["normal"]))
    e.append(Spacer(1, 0.4*cm))
 
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

    # ── 8. Mensaje final ──────────────────────────────────────────────────────────
    e.append(Paragraph("💬 ¿Y ahora qué?", _ST["h3"]))
    texto_final = (
        "Este informe es una <b>herramienta de apoyo</b>, no un diagnóstico. "
        "Los cuestionarios son indicadores, pero solo un profesional de la salud mental "
        "puede realizar una evaluación completa y ofrecer un diagnóstico preciso. "
        "Si tienes dudas o inquietudes, te animamos a buscar asesoramiento con un psicólogo o psiquiatra "
        "especializado en autismo. Tu bienestar es lo más importante."
    )
    e.append(Paragraph(texto_final, _ST["normal"]))
    e.append(Spacer(1, 0.5*cm))

    # ── 9. Cuadro de notas adicionales ───────────────────────────────────────────
    e.append(PageBreak())
    e.append(Paragraph("📝 Notas adicionales", _ST["h3"]))
    
    # Creamos una tabla con una sola celda que actuará como recuadro
    notas_data = [
        ["Espacio para observaciones, comentarios o recomendaciones adicionales:"],
        [" "],  # Línea en blanco para escribir
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],
        [" "],  # Ajusta el número de líneas según el espacio deseado
    ]
    
    notas_tabla = Table(notas_data, colWidths=[16*cm])
    notas_tabla.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), "Helvetica"),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # El texto de la primera fila alineado a la izquierda
    ]))
    # Para la fila de título (índice 0), ponemos el texto en negrita (opcional)
    notas_tabla.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (0, 0), 9),
        ('TOPPADDING', (0, 0), (0, 0), 8),
    ]))
    e.append(notas_tabla)
    e.append(Spacer(1, 0.5*cm))
 
    # ── 10. Referencias y pie ───────────────────────────────────────────────────
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