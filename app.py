"""
app.py – Sistema Integrado de Evaluación del Espectro Autista.
 
Ejecutar con:
    streamlit run app.py
"""
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
st.markdown("""
<style>
  .block-container { padding-top: 1.6rem; }
  .stProgress > div > div > div > div { background-color: #4C72B0; }
  div[data-testid="stRadio"] label { font-size: 0.96rem; }
</style>
""", unsafe_allow_html=True)
 
from src.utils import (
    cargar_preguntas, preguntas_de_test, obtener_opciones_lista,
    porcentaje_completado, DOMINIOS, ICONOS_DOMINIO, NOMBRES_TEST,
)
from src.calculador import (
    calcular_puntuaciones, interpretar_media, RAADS_PUNTO_CORTE,
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
    "test2_externo":  None,
    "idx": {1: 0, 3: 0},
    "cola":           {1: [], 3: []},
    "nombre":         "",
    "pesos":          {1: 1.0, 2: 1.0, 3: 1.0},
}
for k, v in _DEF.items():
    if k not in st.session_state:
        st.session_state[k] = (set() if isinstance(v, set) else
                               dict(v) if isinstance(v, dict) else v)
 
# ── Sidebar ───────────────────────────────────────────────────────────────────
PAGINAS = {
    "🏠 Inicio":           "inicio",
    "📝 Test 1":           "test1",
    "🔗 Test 2 (externo)": "test2",
    "📊 RAADS-R":          "test3",
    "📄 Informe":          "informe",
}
 
with st.sidebar:
    st.title("🧩 Evaluación TEA")
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
    for tid, lbl in [(1, "Test 1"), (2, "Test 2"), (3, "RAADS-R")]:
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
| 1 | Cuestionario propio | 50 | 1-4 |
| 2 | Test online adaptativo | Externo | por dominio |
| 3 | RAADS-R | 80 | 0-3 |
 
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
        for tid in [1, 3]:
            df_t = preguntas_de_test(df, tid)
            pct  = porcentaje_completado(df_t, st.session_state["respuestas"])
            if tid in st.session_state["test_completados"]:
                st.success(f"✅ {NOMBRES_TEST[tid]} — Completado")
            else:
                st.warning(f"⭕ {NOMBRES_TEST[tid]} — {pct*100:.0f}%")
                st.progress(pct)
        if 2 in st.session_state["test_completados"]:
            st.success("✅ Test 2 — Resultado registrado")
        else:
            st.warning("⭕ Test 2 — Pendiente")
 
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    btn = lambda label, pag, col, primary=False: col.button(
        label, use_container_width=True, type="primary" if primary else "secondary"
    )
    with c1:
        if btn("▶️ Test 1", "test1", c1, True):
            st.session_state["pagina"] = "test1"; st.rerun()
    with c2:
        if btn("▶️ Test 2", "test2", c2):
            st.session_state["pagina"] = "test2"; st.rerun()
    with c3:
        if btn("▶️ RAADS-R", "test3", c3):
            st.session_state["pagina"] = "test3"; st.rerun()
    with c4:
        hay_datos = len(st.session_state["test_completados"]) > 0
        if c4.button("📄 Informe", use_container_width=True,
                     type="primary", disabled=not hay_datos):
            st.session_state["pagina"] = "informe"; st.rerun()
        if not hay_datos:
            c4.caption("Completa al menos un test")
 
 
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
                else:
                    # Sin respuesta: mover al final de la cola
                    cola.append(cola.pop(idx))
                    st.session_state["cola"][test_id] = cola
                    # idx sin cambio → ahora apunta al siguiente elemento
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
# TEST 2 (externo)
# ══════════════════════════════════════════════════════════════════════════════
_CAT_T2 = {
    "Sin indicadores":       0.0,
    "Indicadores leves":     1.0,
    "Indicadores moderados": 2.0,
    "Indicadores significativos": 3.0,
}
 
def pagina_test2():
    st.title("🔗 Test 2 – Test Online Adaptativo")
    st.markdown(
        "Realiza el test externo y luego introduce aquí el resultado por dominio. "
        "Puedes usar la categoría que proporciona el test o un valor numérico preciso."
    )
    st.link_button("🔗 Abrir Test 2 en Autism360", "https://www.autism360.com/autism-test-for-adults/", use_container_width=True)
    st.divider()
 
    prev = st.session_state.get("test2_externo") or {}
    resultado: dict[str, float] = {}
 
    col1, col2 = st.columns(2)
    for dom, col in zip(DOMINIOS, [col1, col1, col2, col2]):
        with col:
            icono = ICONOS_DOMINIO[dom]
            st.markdown(f"**{icono} {dom}**")
            modo = st.radio(
                f"modo_{dom}", ["Categoría", "Valor numérico (0-3)"],
                horizontal=True, label_visibility="collapsed", key=f"m2_{dom}",
            )
            if modo == "Categoría":
                idx_p = 0
                if prev.get(dom) is not None:
                    for i, v in enumerate(_CAT_T2.values()):
                        if abs(v - prev[dom]) < 0.01:
                            idx_p = i
                cat = st.selectbox(
                    "", list(_CAT_T2.keys()), index=idx_p,
                    label_visibility="collapsed", key=f"c2_{dom}",
                )
                resultado[dom] = _CAT_T2[cat]
            else:
                resultado[dom] = st.slider(
                    "", 0.0, 3.0, float(prev.get(dom, 0.0)), 0.25,
                    label_visibility="collapsed", key=f"s2_{dom}",
                )
            st.caption(f"Valor → **{resultado[dom]:.2f}** / 3.00")
            st.divider()
 
    if st.button("✅ Guardar resultado del Test 2", type="primary", use_container_width=True):
        st.session_state["test2_externo"] = resultado
        st.session_state["test_completados"].add(2)
        st.success("✅ Resultado guardado correctamente.")
        st.balloons()
 
 
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
        for i, (tid, lbl) in enumerate([(1,"Test 1"),(2,"Test 2"),(3,"RAADS-R")]):
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
        test2_externo=st.session_state["test2_externo"],
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
elif pag == "test2":   pagina_test2()
elif pag == "test3":   pagina_cuestionario(3)
elif pag == "informe": pagina_informe()
