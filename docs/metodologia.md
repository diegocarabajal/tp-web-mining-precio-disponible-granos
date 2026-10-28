# Metodología

## 1. Datos y construcción del panel
1. **Disponible (Matba/CEM2):** de 33.993 registros se conservan solo las filas `tipo_instrumento == "disponible"` de soja, maíz y trigo (2.743 registros). Los símbolos anuales (`SOJ.ROS/DIS23` … `DIS26`) se unifican en una serie continua por especie; en enero, cuando cotizan dos contratos a la vez, se toma el del año en curso. Se usa el **precio de ajuste** (`settlement`, USD/t).
2. **Chicago (BCR):** 837 páginas (una por día hábil). Se convierten los números al formato con punto decimal y las fechas `dd/mm/aaaa`. Las 24 páginas vacías y 4 registros en cero quedan como faltantes, sin imputar. Se arma un índice continuo que absorbe los 27 saltos de vencimiento de la soja.
3. **Lluvia (NOAA):** 8 estados del Corn Belt, 14.832 registros (224 preliminares, marcados). Se calcula la anomalía de lluvia acumulada a 30 y 60 días contra la climatología mensual.
4. **Integración:** unión por fecha tomando el último dato disponible del día anterior (`merge_asof` con `allow_exact_matches=False`).

## 2. Variable a predecir (target)
Se predice el **log-retorno** a *h* días, `y = ln(P_{t+h} / P_t)`, con *h* ∈ {30, 60, 90}, y el pronóstico de precio es `P_t · exp(ŷ)`.
Razones: medir en nivel engaña (copiar el precio de hace 30 días da R² ≈ 0,51 en soja, pero en variación aporta 0); los árboles (XGBoost) no extrapolan fuera del rango visto; y un porcentaje es comparable entre granos.

## 3. Variables
| Conjunto | Contenido |
|---|---|
| 1 · Solo precio | Retornos recientes (5, 21, 63 ruedas), volatilidad de 21 ruedas, distancia a la media de 63 ruedas, estacionalidad mensual (seno/coseno) |
| 2 · + Chicago | Retornos de Chicago (5, 21, 63) y base Rosario–Chicago (diferencial en logaritmos) y su desvío respecto de la media de 126 ruedas |
| 3 · + Clima | Anomalía de lluvia acumulada 30/60 días, indicador de meses críticos (jun–ago) e interacción clima × mes crítico (solo soja y maíz) |

ARIMA usa solo el precio; ARIMAX suma Chicago y clima como variables externas rezagadas.

## 4. Partición temporal
| Tramo | Período | Uso |
|---|---|---|
| Arranque | ene–abr 2023 | Sin historia suficiente para armar rezagos |
| Entrenamiento | abr 2023 – dic 2024 | Elegir variables e hiperparámetros |
| Validación | 2024, trimestre a trimestre | Validación cruzada temporal |
| Prueba out-of-sample | ene 2025 – sep 2026 | Walk-forward mes a mes con reentrenamiento expandido |

El entrenamiento se parte en validaciones temporales (no al azar) porque los datos son una serie de tiempo: mezclar fechas permitiría que el modelo "vea" el futuro.

## 5. Evaluación
- **Métrica principal:** R² fuera de muestra contra el random walk ("el precio no cambia"). 0 = empate; positivo = mejora.
- Otras: MAE, RMSE, MAPE, acierto de dirección (¿subió o bajó?).
- **Significancia:** test de Diebold–Mariano con corrección Harvey–Leybourne–Newbold, con rezagos según el plazo.
- **Bandas de pronóstico:** rango del 80 %; en la prueba histórica cubrieron aproximadamente el 80 %.

## 6. Modelos
Referencias: **random walk** y **tendencia promedio**. Familias: **ElasticNet** (regresión penalizada), **XGBoost** (árboles muy regularizados), **ARIMA** y **ARIMAX**. Los tres granos se modelan juntos, con la especie como variable (maíz es la base). Semilla 42.

## 7. Control de data leakage
| Riesgo | Control |
|---|---|
| Usar datos del mismo día o posteriores | Unión *as-of* en *t−1* |
| Entrenar con etiquetas que aún no se conocían | Purga temporal: un pronóstico a 90 días hecho en diciembre recién se resuelve en marzo y no entra al entrenamiento de enero o febrero |
| Climatología calculada con toda la serie | Se calcula solo con datos hasta 2024 |
| Escalado con estadísticos del conjunto de prueba | El `StandardScaler` está dentro del pipeline, ajustado solo con entrenamiento |
| Elegir hiperparámetros mirando la prueba | Tuning con 2023–2024; la prueba no se usa |
| Precios futuros | No se cargan: se descartan al leer el archivo de Matba |

## 8. Hallazgos
- Con estos datos, **ningún modelo mejora de forma significativa al precio de hoy**.
- **Chicago** es la fuente que más aporta; la **lluvia del Corn Belt** casi nada (posible explicación: Chicago ya refleja parte del clima — es una hipótesis, no un resultado demostrado).
- XGBoost fue el peor; ElasticNet descartó casi todas las variables.
