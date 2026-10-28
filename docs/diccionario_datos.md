# Diccionario de datos

## data/raw/
**`futuros_y_disponible_agropecuario_2023_a_hoy.csv`** (separador `;`) — Matba Rofex vía CEM2. 33.993 registros, 246 símbolos. Solo se usan las filas con `tipo_instrumento == "disponible"`.
Columnas: `dateTime`, `symbol`, `settlement` (precio de ajuste, USD/t — el que se usa), `high`, `low`, `open`, `close`, `openInterest`, `volume`, `tradeCount`, `product`, `tipo_instrumento`, entre otras.

**`bcr_chicago_1.csv`** (separador `;`, decimal `,`) — Chicago/Kansas CME Group, BCR. 837 filas.
`Fecha` (dd/mm/aaaa); para cada grano (`Trigo Chicago/2`, `Maíz Chicago/3`, `Soja Chicago/4`): precio, `variación` y `posición` (mes de contrato del que salió el dato); `Feriado` (`S`/`N`); `ID página` (ID consecutivo de la URL).

**`prcp_diaria_cornbelt.csv`** — NOAA nClimGrid-Daily. `estado`, `fecha`, `precip_mm` (−999,99 = sin dato; ya tratado), `calidad` (`final` o `preliminar`).

## data/processed/
**`variables_diarias.csv`** — una fila por fecha y especie (`soja`, `maiz`, `trigo`).
| Columna | Significado |
|---|---|
| `P_t` | Precio disponible (ajuste), USD/t |
| `ret_5`, `ret_21`, `ret_63` | Log-retorno del disponible a 5, 21 y 63 ruedas |
| `vol_21` | Volatilidad de 21 ruedas |
| `dist_ma63` | Distancia del precio a su media de 63 ruedas |
| `chi_ret_5/21/63` | Log-retornos de Chicago |
| `base` | Diferencial Rosario–Chicago: log(precio Rosario) − log(precio Chicago) |
| `base_desvio` | `base` menos su media móvil de 126 ruedas |
| `anom_acum30`, `anom_acum60` | Anomalía de lluvia acumulada del Corn Belt (30 y 60 días) |
| `critico` | 1 en jun–ago (meses críticos del cultivo) |
| `clima_x_critico` | Interacción anomalía de 30 días × mes crítico (se anula para trigo) |
| `mes_sin`, `mes_cos` | Estacionalidad mensual |

**`panel_sin_futuros.csv`** — lo anterior, una fila por fecha, especie y plazo `h`, más: `fecha_obj` (fecha objetivo), `P_obj` (precio observado en esa fecha), `y` (target: log-retorno), `conjunto` (`tuning`, `purga` o `test`), `pred_rw`, `pred_tendencia` (predicciones de las referencias).

**`resultados_baselines_sin_futuros.csv`** — métricas de las dos referencias.

## resultados/
- **`predicciones_test_sin_futuros.csv`** — predicción de cada modelo (log-retorno) para cada fecha de prueba: `pred_rw`, `pred_tendencia`, `pred_enet_{precio,chicago,completo}`, `pred_xgb_{precio,chicago,completo}`, `pred_arima`, `pred_arimax`.
- **`resultados_modelos_sin_futuros.csv`** — por especie (incl. `TODAS`), plazo y modelo: `n`, `MAE`, `RMSE`, `MAPE_%`, `R2_niveles`, `R2_ret`, `R2_oos_vs_RW`, `acierto_dir_%`, `DM_stat_vs_RW`, `DM_p_vs_RW`.
- **`pronostico_sin_futuros.csv`** — pronóstico desde la última fecha con datos: `precio_hoy`, `pronostico`, `banda_80_baja`, `banda_80_alta`, `R2_oos_test`.
- **`hiperparametros_sin_futuros.csv`** — hiperparámetros elegidos en el tuning.
