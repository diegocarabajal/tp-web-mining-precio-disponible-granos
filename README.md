# Predicción del precio disponible de granos (soja, maíz y trigo) — Rosario

Trabajo final de **Web Mining** · Maestría en Explotación de Datos y Gestión del Conocimiento · Universidad Austral
**Grupo 6:** Jorge Barbona · Sofía Cremydas · Diego Carabajal · Nicolás Caggiano — Octubre de 2026

## De qué se trata

Predecimos el **precio disponible** de soja, maíz y trigo en el Matba Rofex (Rosario) a **30, 60 y 90 días**, usando solo datos públicos obtenidos de la web:

| Fuente | Qué aporta | Cómo se obtuvo |
|---|---|---|
| **Matba Rofex (CEM2)** | Precio de ajuste del disponible (USD/t) | API pública JSON |
| **BCR – Chicago/Kansas CME** | Precios de Chicago de soja, maíz y trigo | Web scraping (requests + Beautiful Soup) |
| **NOAA NCEI** | Lluvia diaria/mensual de 8 estados del Corn Belt | API / archivos JSON y CSV |

**Pregunta de investigación:** ¿qué aporta más para anticipar el precio disponible: su propia historia, Chicago o el clima del Corn Belt?

> **No se usan precios futuros.** Del archivo de Matba se leen únicamente las filas de tipo `disponible`; los contratos futuros se descartan en la carga.

## Resultado principal

R² fuera de muestra contra la referencia "el precio no cambia" (0 = empate, positivo = mejora). Prueba: enero 2025 – septiembre 2026, los tres granos juntos, mejor conjunto de variables de cada modelo.

| Modelo | 30 días | 60 días | 90 días |
|---|---|---|---|
| **ARIMAX** (Chicago + clima) | −0,06 | **+0,02** | **+0,04** |
| ARIMA (solo precio) | −0,03 | 0,00 | −0,01 |
| ElasticNet (+ Chicago y clima) | −0,07 | −0,11 | −0,12 |
| Tendencia | −0,09 | −0,17 | −0,22 |
| XGBoost (+ Chicago y clima) | −0,21 | −0,43 | −0,15 |

- **Ninguna mejora es estadísticamente significativa** (test de Diebold–Mariano; en ARIMAX, los p-valores de los tres granos juntos van de 0,10 a 0,71).
- A 90 días, el error medio de ARIMAX es 16,8 USD/t contra 17,2 de "el precio no cambia".
- **Chicago es la fuente que más aporta**; la lluvia del Corn Belt casi no agrega.
- Pronóstico desde el 24/09/2026 (ARIMAX, 90 días): soja ≈ 370 (rango 336–432), maíz ≈ 197 (178–213), trigo ≈ 232 (206–267) USD/t.

Detalle por grano y plazo en [`resultados/resultados_modelos_sin_futuros.csv`](resultados/resultados_modelos_sin_futuros.csv).

## Estructura del repositorio

```
├── data/
│   ├── raw/                  # Datos tal como se bajaron de la web (3 CSV)
│   └── processed/            # Panel de modelado y variables (los genera el notebook 01)
├── scraping/
│   └── scrap_bcr_chicago.py  # Scraper de la BCR (reintentos, cache .jsonl, --debug)
├── apis/
│   ├── cem2_api_matba.ipynb            # Descarga de Matba Rofex vía CEM2
│   └── noaa_precipitacion_cornbelt.ipynb  # Descarga de lluvia desde NOAA NCEI
├── notebooks/
│   ├── 01_dataset_sin_futuros.ipynb    # Limpieza, integración, variables, partición y baselines
│   └── 02_modelos_sin_futuros.ipynb    # ElasticNet, XGBoost, ARIMA/ARIMAX, métricas y pronóstico
├── resultados/               # Métricas, predicciones de prueba, pronóstico e hiperparámetros
├── presentacion/             # Presentación final (.pptx)
└── docs/
    ├── metodologia.md        # Target, partición temporal, purga y control de data leakage
    ├── diccionario_datos.md  # Columnas de cada archivo
    └── guia_presentacion.md  # Explicación de cada filmina
```

Los notebooks se guardan **con sus salidas ejecutadas**, así que GitHub muestra gráficos y tablas sin correr nada.

## Cómo reproducirlo

```bash
git clone <URL-del-repo> && cd <repo>
python -m venv .venv && source .venv/bin/activate      # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Desde la carpeta notebooks/ (las rutas son relativas a ella)
cd notebooks
jupyter nbconvert --to notebook --execute --inplace 01_dataset_sin_futuros.ipynb   # ~15 s
jupyter nbconvert --to notebook --execute --inplace 02_modelos_sin_futuros.ipynb   # ~3-4 min
```

El notebook 01 lee `data/raw/` y escribe en `data/processed/`; el 02 lee de ahí y escribe en `resultados/`. Los resultados son deterministas (semilla 42): al volver a ejecutar se obtienen los mismos archivos que están en el repo.

**En Google Colab:** subir los notebooks y los CSV; cuando detectan Colab usan `/content` y piden subir los archivos que falten.

### Volver a bajar los datos de la web

```bash
# 1) Chicago (BCR) — hace ~840 requests con pausas, tarda un rato
pip install requests beautifulsoup4
python scraping/scrap_bcr_chicago.py --desde 2023-01-01 --salida data/raw/bcr_chicago_1.csv
#    si el sitio corta (429/503) espera y reintenta; al volver a correrlo retoma del cache
#    otras opciones: --pausa 3  |  --debug 3250 (guarda el HTML de un ID para inspeccionarlo)

# 2) Matba Rofex y 3) NOAA: ejecutar los notebooks de apis/
```

> **Ojo con el notebook de CEM2:** la versión que está en `apis/` descarga **futuros desde 2024** (`FECHA_DESDE_GLOBAL = 2024-01-01` y un patrón de símbolo de futuros). El archivo `data/raw/futuros_y_disponible_agropecuario_2023_a_hoy.csv` incluye además el **disponible desde 2023**, así que para regenerarlo hay que cambiar la fecha de inicio a 2023-01-01 y ajustar el filtro de símbolos para incluir los `…/DISxx`. Por eso el CSV de `data/raw/` es la fuente de verdad del análisis.

> Las páginas y APIs pueden cambiar con el tiempo (el scraper depende del HTML de la BCR). Los CSV de `data/raw/` son la foto con la que se hizo el trabajo.

## Cómo se evitó el data leakage

Resumen (detalle en [`docs/metodologia.md`](docs/metodologia.md)):

- Cada variable en la fecha *t* usa solo información de *t−1* o anterior (unión *as-of* estricta).
- **Purga temporal** en la evaluación mes a mes: no se entrena con observaciones cuyo resultado todavía no se conocía.
- La climatología de lluvia se calcula solo con datos hasta 2024.
- El escalado de variables está dentro del pipeline, ajustado solo con datos de entrenamiento.
- El ajuste de hiperparámetros se hace con 2023–2024; el período de prueba (2025 en adelante) no se toca.

## Limitaciones

- Solo ~3,7 años de historia (2023–2026): pocas campañas.
- Los tres granos se modelan juntos para tener más observaciones; no hay un modelo específico por grano.
- Las bandas de pronóstico cubrieron el 80 % en la prueba histórica, lo que no garantiza esa cobertura hacia adelante.
- El scraper depende de la estructura actual del sitio de la BCR.

## Próximos pasos

Más historia (antes de 2023), scraping diario automatizado con alertas, minería de texto de noticias e informes (USDA, BCR), tipo de cambio y retenciones, clima de Argentina y Brasil, y combinación de modelos.

## Licencia

MIT — ver [`LICENSE`](LICENSE).
