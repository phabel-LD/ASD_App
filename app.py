"""
app.py – Sistema Integrado de Evaluación del Espectro Autista.

Ejecutar con:
    streamlit run app.py
"""

try:
    import reportlab
    st.success("✅ reportlab instalado correctamente")
except ImportError:
    st.error("❌ reportlab NO está instalado")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="Evaluación TEA",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Insertar Logo jpeg
logo_path = Path(__file__).parent / "assets" / "logo.jpeg"
# Crear tres columnas: la primera ocupa la mayor parte, la segunda y tercera son pequeñas
col1, col2, col3 = st.columns([3, 1, 3])
with col3:  # Columna más a la derecha
    if logo_path.exists():
        st.image(str(logo_path), width=500)  # Ajusta el ancho (130 px es un buen tamaño para un logo cuadrado)
    else:
        # Si el archivo no existe, muestra un espacio en blanco o un mensaje opcional
        st.caption("")  # Espacio vacío    

st.markdown("""
<style>
  .block-container { padding-top: 5rem; }
  .stProgress > div > div > div > div { background-color: #4C72B0; }
  div[data-testid="stRadio"] label { font-size: 0.96rem; }
</style>
""", unsafe_allow_html=True)

from src.utils import (
    cargar_preguntas, preguntas_de_test, obtener_opciones_lista,
    porcentaje_completado, DOMINIOS, ICONOS_DOMINIO, NOMBRES_TEST,
)
from src.calculador import (
    calcular_puntuaciones, interpretar_media, RAADS_PUNTO_CORTE, calcular_score_global,
)
from src.visualizador import (
    crear_radar, crear_barras_por_test, crear_gauge_raads, crear_tabla_detalles,
)

# ── Datos ─────────────────────────────────────────────────────────────────────
df = cargar_preguntas()

# ── Estado de sesión ──────────────────────────────────────────────────────────
_DEF: dict = {
    "pagina":         "inicio",
    "respuestas":     {},
    "test_completados": set(),
    "idx": {1: 0, 3: 0, 4: 0},
    "cola":           {1: [], 3: [], 4: []},
    "nombre":         "",
    "pesos":          {1: 1.0, 3: 1.0, 4: 1.0},
}
for k, v in _DEF.items():
    if k not in st.session_state:
        st.session_state[k] = (set() if isinstance(v, set) else
                               dict(v) if isinstance(v, dict) else v)

# ── Sidebar ───────────────────────────────────────────────────────────────────
PAGINAS = {
    "🏠 Inicio":           "inicio",
    "📝 Test 1":           "test1",
    "📊 RAADS-R":          "test3",
    "🧮 AQ-10":            "test4",
    "📄 Informe":          "informe",
}

with st.sidebar:
    st.title("🧩 Evaluación TEA")
    st.caption("Basado en el DSM-5")
    st.divider()
    sel = st.radio(
        "Navegar a",
        list(PAGINAS.keys()),
        index=list(PAGINAS.values()).index(st.session_state["pagina"]),
        label_visibility="collapsed",
    )
    st.session_state["pagina"] = PAGINAS[sel]

    st.divider()
    st.caption("**Estado de tests:**")
    comp = st.session_state["test_completados"]
    for tid, lbl in [(1, "Test 1"), (3, "RAADS-R"), (4, "AQ-10")]:
        st.caption(("✅ " if tid in comp else "⭕ ") + lbl)

    st.divider()
    if st.button("🔄 Reiniciar todo", use_container_width=True):
        for k, v in _DEF.items():
            st.session_state[k] = (set() if isinstance(v, set) else
                                   dict(v) if isinstance(v, dict) else v)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# INICIO
# ══════════════════════════════════════════════════════════════════════════════
def pagina_inicio():
    st.title("🧩 Sistema de Evaluación del Espectro Autista")
    st.caption("Basado en el DSM-5")
    st.markdown(
        "Herramienta que integra **dos cuestionarios** y el **RAADS-R** en un "
        "informe unificado por dominio clínico."
    )
    st.info(
        "Esta herramienta es un **apoyo a la evaluación clínica**, no sustituye "
        "el juicio profesional ni constituye un diagnóstico.",
        icon="⚠️",
    )

    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Tests incluidos")
        st.markdown("""
| # | Instrumento | Ítems | Escala |
|---|---|---|---|
| 1 | Cuestionario propio | 89 | 1-4 |
| 2 | RAADS-R | 80 | 0-3 |
| 3 | AQ-10 (Baron-Cohen) | 10 | 0-3 |

Resultados unificados en **4 dominios** (escala 0–3):  
👥 Social · 💬 Comunicación · 🎵 Sensorial · 🔍 Intereses
        """)
        st.subheader("Nombre / código (opcional)")
        nombre = st.text_input(
            "Para el informe PDF", value=st.session_state["nombre"],
            placeholder="Ej. P-001 o nombre del paciente",
        )
        if nombre != st.session_state["nombre"]:
            st.session_state["nombre"] = nombre

    with col2:
        st.subheader("Progreso actual")
        for tid in [1, 3, 4]:
            df_t = preguntas_de_test(df, tid)
            pct  = porcentaje_completado(df_t, st.session_state["respuestas"])
            if tid in st.session_state["test_completados"]:
                st.success(f"✅ {NOMBRES_TEST[tid]} — Completado")
            else:
                st.warning(f"⭕ {NOMBRES_TEST[tid]} — {pct*100:.0f}%")
                st.progress(pct)

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    btn = lambda label, pag, col, primary=False: col.button(
        label, use_container_width=True, type="primary" if primary else "secondary"
    )
    with c1:
        if btn("▶️ Test 1", "test1", c1, True):
            st.session_state["pagina"] = "test1"; st.rerun()
    with c2:
        if btn("▶️ RAADS-R", "test3", c2):
            st.session_state["pagina"] = "test3"; st.rerun()
    with c3:
        if btn("▶️ AQ-10", "test4", c3):
            st.session_state["pagina"] = "test4"; st.rerun()
    with c4:
        hay_datos = len(st.session_state["test_completados"]) > 0
        if c3.button("📄 Informe", use_container_width=True,
                     type="primary", disabled=not hay_datos):
            st.session_state["pagina"] = "informe"; st.rerun()
        if not hay_datos:
            c3.caption("Completa al menos un test")


# ══════════════════════════════════════════════════════════════════════════════
# CUESTIONARIO GENÉRICO (Test 1 y RAADS-R)
# ══════════════════════════════════════════════════════════════════════════════
def pagina_cuestionario(test_id: int):
    df_test  = preguntas_de_test(df, test_id)
    total    = len(df_test)
    ids_list = df_test["id"].tolist()
    ids_set  = set(ids_list)

    st.title(NOMBRES_TEST[test_id])

    # ── Inicializar cola ──────────────────────────────────────────────────────
    # Lista de posiciones (índices en df_test). Las preguntas saltadas sin
    # respuesta se mueven al final cuando el usuario presiona "Siguiente".
    cola = st.session_state["cola"][test_id]
    if not cola:
        cola = list(range(total))
        st.session_state["cola"][test_id] = cola

    # Índice actual dentro de la cola
    idx = st.session_state["idx"].get(test_id, 0)
    idx = max(0, min(idx, len(cola) - 1))

    # Progreso
    n_resp = len(ids_set & set(st.session_state["respuestas"]))
    st.progress(n_resp / total, text=f"Respondidas: **{n_resp} / {total}**")

    # Pregunta actual
    pos_en_cola = cola[idx]
    row   = df_test.iloc[pos_en_cola]
    pid   = int(row["id"])
    dom   = row["dominio"]
    icono = ICONOS_DOMINIO.get(dom, "❓")
    opts  = obtener_opciones_lista(row)
    inv   = row["direccion"] == "inversa"

    # Encabezado
    marcas = f"{icono} *{dom}*" + ("  🔄 *ítem inverso*" if inv else "")
    st.markdown(f"**Pregunta {idx + 1} de {len(cola)}** &nbsp; {marcas}")
    st.markdown(f"### {row['texto']}")
    if row["notas"]:
        st.caption(f"📌 {row['notas']}")

    # Radio de respuesta
    prev   = st.session_state["respuestas"].get(pid)
    i_prev = list(opts.keys()).index(prev) if prev in opts else None
    resp   = st.radio(
        "Selecciona una opción:",
        options=list(opts.keys()),
        format_func=lambda x: opts[x],
        index=i_prev,
        key=f"r_{test_id}_{pid}",
    )
    if resp is None:
        st.caption("💡 Sin respuesta — si avanzas, esta pregunta aparecerá al final.")

    st.divider()

    # ── Botones de navegación ─────────────────────────────────────────────────
    es_ultimo = (idx == len(cola) - 1)
    col_ant, col_sig = st.columns(2)

    # — Anterior —
    with col_ant:
        if idx > 0:
            if st.button("← Anterior", use_container_width=True):
                st.session_state["idx"][test_id] = idx - 1
                st.rerun()

    # — Siguiente / Finalizar —
    with col_sig:
        if not es_ultimo:
            if st.button("Siguiente →", use_container_width=True, type="primary"):
                if resp is not None:
                    st.session_state["respuestas"][pid] = resp
                    st.session_state["idx"][test_id] = idx + 1
                else:
                    # Sin respuesta: mover al final de la cola, idx queda igual
                    # (ahora apunta al elemento que era idx+1)
                    cola.append(cola.pop(idx))
                    st.session_state["cola"][test_id] = cola
                    st.session_state["idx"][test_id] = idx
                st.rerun()
        else:
            if st.button("✅ Finalizar", use_container_width=True, type="primary"):
                if resp is not None:
                    st.session_state["respuestas"][pid] = resp
                n_sin = total - len(ids_set & set(st.session_state["respuestas"]))
                if n_sin > 0:
                    st.warning(f"{n_sin} pregunta(s) sin responder. Puedes finalizar igualmente.")
                    if st.button("Confirmar finalización", key=f"forzar_{test_id}"):
                        st.session_state["test_completados"].add(test_id)
                        st.session_state["pagina"] = "inicio"
                        st.balloons()
                        st.rerun()
                else:
                    st.session_state["test_completados"].add(test_id)
                    st.session_state["pagina"] = "inicio"
                    st.balloons()
                    st.rerun()

    # Sidebar: progreso por dominio
    with st.sidebar:
        st.divider()
        st.caption("**Progreso por dominio:**")
        for dom_s in DOMINIOS:
            preg_d = df_test[df_test["dominio"] == dom_s]
            if preg_d.empty:
                continue
            resp_d = len(set(preg_d["id"]) & set(st.session_state["respuestas"]))
            n_d    = len(preg_d)
            st.caption(f"{ICONOS_DOMINIO[dom_s]} {dom_s}: {resp_d}/{n_d}")
            st.progress(resp_d / n_d)


# ══════════════════════════════════════════════════════════════════════════════
# INFORME
# ══════════════════════════════════════════════════════════════════════════════
def pagina_informe():
    st.title("📄 Informe Unificado")

    comp = st.session_state["test_completados"]
    if not comp:
        st.warning("Completa al menos un test para ver el informe.")
        return

    # Pesos configurables
    with st.expander("⚙️ Ponderación de tests (opcional)", expanded=False):
        st.caption("Ajusta la influencia relativa de cada test en la media global.")
        pc = st.columns(3)
        pesos: dict[int, float] = {}
        for i, (tid, lbl) in enumerate([(1,"Test 1"),(3,"RAADS-R"),(4,"AQ-10")]):
            with pc[i]:
                pesos[tid] = st.slider(
                    lbl, 0.0, 3.0,
                    float(st.session_state["pesos"].get(tid, 1.0)), 0.25,
                    key=f"p_{tid}", disabled=tid not in comp,
                )
        if st.button("Aplicar pesos"):
            st.session_state["pesos"] = pesos
            st.rerun()

    pesos_act = {k: v for k, v in st.session_state["pesos"].items() if k in comp}

    # Calcular
    res = calcular_puntuaciones(
        respuestas=st.session_state["respuestas"],
        df_preguntas=df,
        pesos=pesos_act or None,
    )

    # ── Métricas ────────────────────────────────────────────────────────────
    st.subheader("Perfil global")
    cols_m = st.columns(4)
    for i, dom in enumerate(DOMINIOS):
        with cols_m[i]:
            m     = res["global_por_dominio"][dom]["media_ponderada"]
            etiq, color = interpretar_media(m)
            st.metric(
                label=f"{ICONOS_DOMINIO[dom]} {dom}",
                value=f"{m:.2f}" if m is not None else "—",
                help="Escala 0-3",
            )
            st.markdown(
                f"<span style='color:{color}; font-weight:600'>{etiq}</span>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Score global ──────────────────────────────────────────────────────────
    score_info = calcular_score_global(res)
    if score_info["score"] is not None:
        st.subheader("📊 Score Global (promedio de dominios)")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Score", f"{score_info['score']:.2f} / 3.00")
        with col_s2:
            st.metric("Punto de corte", "1.50")
        with col_s3:
            nivel_color = score_info["color"]
            st.markdown(
                f"**Nivel:** <span style='color:{nivel_color}; font-weight:bold'>{score_info['nivel']}</span>",
                unsafe_allow_html=True,
            )
        if score_info["sobre_corte"]:
            st.warning("⚠️ El puntaje supera el punto de corte (1.5). Se recomienda evaluación adicional.")
        else:
            st.success("✅ El puntaje está por debajo del punto de corte (1.5).")
        st.caption(
            f"Basado en {score_info['n_dominios']} dominio(s): "
            f"{', '.join(score_info['dominios_usados'])}"
        )
    else:
        st.info("No hay suficientes datos para calcular el score global.")

    st.divider()

    # ── Gráficos ────────────────────────────────────────────────────────────
    cg1, cg2 = st.columns(2)
    with cg1:
        st.plotly_chart(crear_radar(res["global_por_dominio"]), use_container_width=True)
    with cg2:
        st.plotly_chart(crear_barras_por_test(res["por_test"]), use_container_width=True)

    # ── RAADS-R ─────────────────────────────────────────────────────────────
    if 3 in comp:
        st.subheader("Puntuación RAADS-R")
        cr1, cr2 = st.columns([2, 3])
        with cr1:
            st.plotly_chart(crear_gauge_raads(res["raads_bruta"]), use_container_width=True)
        with cr2:
            sobre  = res["raads_sobre_corte"]
            color  = res["raads_color"]
            st.markdown(f"**Puntuación bruta:** {res['raads_bruta']} / 240")
            st.markdown(f"**Punto de corte:** {RAADS_PUNTO_CORTE}")
            icono_r = "⬆️" if sobre else "⬇️"
            st.markdown(
                f"**Resultado:** "
                f"<span style='color:{color}; font-weight:700'>"
                f"{icono_r} {'Por encima' if sobre else 'Por debajo'} "
                f"del punto de corte</span>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Ritvo et al. (2011): sensibilidad 97%, especificidad 100% "
                f"con corte en {RAADS_PUNTO_CORTE}/240. "
                "Una puntuación elevada es sugestiva, no diagnóstica."
            )

    if 4 in comp:
        st.subheader("Puntuación AQ-10")
        ca1, ca2 = st.columns([2, 3])
        with ca1:
            from src.visualizador import crear_gauge_aq10
            st.plotly_chart(crear_gauge_aq10(res["aq10_bruta"]), use_container_width=True)
        with ca2:
            sobre_aq = res["aq10_sobre_corte"]
            color_aq = res["aq10_color"]
            st.markdown(f"**Puntuación bruta:** {res['aq10_bruta']} / 10")
            st.markdown("**Punto de corte:** 6")
            icono_aq = "⬆️" if sobre_aq else "⬇️"
            st.markdown(
                f"**Resultado:** "
                f"<span style='color:{color_aq}; font-weight:700'>"
                f"{icono_aq} {'Por encima' if sobre_aq else 'Por debajo'} "
                f"del punto de corte</span>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Allison et al. (2012): punto de corte ≥ 6/10 indica derivación "
                "para evaluación diagnóstica formal. No constituye diagnóstico."
            )

    st.divider()

    # ── Tabla de detalle ─────────────────────────────────────────────────────
    st.subheader("Detalle por test y dominio")
    _pd = __import__("pandas")
    st.dataframe(
        _pd.DataFrame(crear_tabla_detalles(res["por_test"])),
        use_container_width=True, hide_index=True,
    )

    st.divider()

    # ── Exportar PDF ─────────────────────────────────────────────────────────
    st.subheader("Exportar")
    ce1, ce2 = st.columns([2, 3])
    with ce1:
        try:
            from src.reporte import generar_pdf
            pdf = generar_pdf(res, st.session_state["nombre"])
            st.download_button(
                "📥 Descargar informe PDF", data=pdf,
                file_name="informe_tea.pdf", mime="application/pdf",
                use_container_width=True, type="primary",
            )
        except ImportError:
            st.warning("Instala `reportlab` para generar el PDF.")
    with ce2:
        st.caption(
            "El PDF incluye perfil global por dominio, puntuación RAADS-R "
            "y tabla comparativa entre tests."
        )


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
pag = st.session_state["pagina"]
if   pag == "inicio":  pagina_inicio()
elif pag == "test1":   pagina_cuestionario(1)
elif pag == "test3":   pagina_cuestionario(3)
elif pag == "test4":   pagina_cuestionario(4)
elif pag == "informe": pagina_informe()