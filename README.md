# Sistema Integrado de Evaluación del Espectro Autista

Aplicación **Streamlit** que unifica dos cuestionarios y el RAADS-R
en un informe con puntuaciones por dominio clínico (escala 0–3).

---

## Estructura del proyecto

```
proyecto-autismo/
├── data/
│   └── preguntas.csv          ← 130 ítems (Test 1 × 50 + RAADS-R × 80)
├── src/
│   ├── __init__.py
│   ├── utils.py               ← constantes, cargar_preguntas(), helpers
│   ├── normalizador.py        ← normalizar_a_0_3(), normalizar_respuestas_dict()
│   ├── calculador.py          ← calcular_puntuaciones(), interpretar_media()
│   ├── visualizador.py        ← gráficos Plotly (radar, barras, gauge)
│   └── reporte.py             ← exportación PDF con ReportLab
├── tests/
│   ├── test_normalizador.py   ← 17 pruebas unitarias
│   └── test_calculador.py     ← 13 pruebas unitarias
├── assets/                    ← logos / imágenes opcionales
├── app.py                     ← aplicación principal
├── requirements.txt
└── README.md
```

---

## Instalación rápida

```bash
# 1. Entorno virtual
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Dependencias
pip install -r requirements.txt

# 3. Arrancar la app
streamlit run app.py
```

---

## Tests incluidos

| # | Instrumento | Ítems | Escala |
|---|---|---|---|
| 1 | Cuestionario propio | 50 | 1–4 |
| 2 | Test online adaptativo | externo | resultado por dominio |
| 3 | RAADS-R | 80 | 0–3 |

El **Test 2** es comercial: el usuario introduce el resultado por dominio
directamente en la aplicación (categoría o valor numérico 0–3).

---

## Dominios clínicos

| Dominio | Descripción |
|---|---|
| 👥 Social | Interacción y reciprocidad social |
| 💬 Comunicacion | Lenguaje y comunicación pragmática |
| 🎵 Sensorial | Procesamiento sensorial y motor |
| 🔍 Intereses | Intereses circunscritos y rutinas |

---

## Normalización

| Escala origen | Fórmula | Rango resultante |
|---|---|---|
| 1–4 | `normalizado = raw − 1` | 0–3 |
| 0–3 | `normalizado = raw` | 0–3 |
| Ítem inverso | `final = 3 − normalizado` | 0–3 |

Implementado en `src/normalizador.py`.

---

## Estructura de `preguntas.csv`

| Columna | Descripción |
|---|---|
| id | Identificador único |
| test_id | 1 ó 3 |
| orden | Posición dentro del test |
| texto | Enunciado en español |
| dominio | Social / Comunicacion / Sensorial / Intereses |
| direccion | directa / inversa |
| escala_origen | 1-4 / 0-3 |
| opcion_a … opcion_e | Textos de las opciones de respuesta |
| notas | Observaciones clínicas |

Fuente: hoja `preguntas_short` del Excel original.

---

## Ejecutar las pruebas unitarias

```bash
pytest tests/ -v
# 30 tests, todos deben pasar
```

---

## Notas clínicas

- **Punto de corte RAADS-R:** 65 / 240  
  (Ritvo et al., 2011 — sensibilidad 97%, especificidad 100%)
- Los rangos de interpretación (*Sin indicadores / Leves / Moderados /
  Significativos*) son **orientativos** y deben validarse con la psiquiatra.
- La herramienta **no constituye diagnóstico**.

---

## Tareas pendientes

- [ ] Validar con la psiquiatra los rangos de interpretación por dominio
- [ ] Validar dirección (directa/inversa) de los 20 ítems inversos del Test 1
- [ ] Añadir baremos de referencia si se dispone de muestra normativa
- [ ] Mejorar el PDF: incrustar los gráficos Plotly como imágenes
- [ ] Autenticación / historiales de pacientes si se requiere
