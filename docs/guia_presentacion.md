# Guía de la presentación, filmina por filmina

Archivo: [`presentacion/Prediccion-de-precios-de-commodities-agropecuarios_FINAL.pptx`](../presentacion/Prediccion-de-precios-de-commodities-agropecuarios_FINAL.pptx)

1. **Portada.** Predecir el precio disponible de soja, maíz y trigo en Rosario a 30, 60 y 90 días, con la historia del precio, Chicago y la lluvia del Corn Belt. Aclarar que no se usan futuros.
2. **El problema.** La pregunta es qué aporta más: el propio precio, Chicago o el clima. Se compara contra "el precio no cambia". Datos: 3 granos, 3 fuentes, 3 plazos, 908 ruedas (ene 2023 – sep 2026).
3. **El proceso.** Mapa de seis pasos: scraping, APIs, limpieza, integración, variables y evaluación. La unión por fecha usa siempre el dato del día anterior para no filtrar el futuro.
4. **Tres fuentes.** Matba/CEM2 (API, 2.743 registros), BCR (scraping, 837 páginas) y NOAA (API/CSV, 14.832 registros). Salen tres CSV.
5. **El scraping de la BCR.** Una página por día hábil con ID correlativo; corta tras 15 inexistentes seguidas. Desafíos y soluciones: bloqueos 429/503 (espera creciente y `Retry-After`), cache `.jsonl` con reanudación, pausas con azar y headers de navegador, timeout y manejo de 404/5xx, HTML irregular (colspan, números `1.234,56`) y modo `--debug`.
6. **Las APIs.** CEM2: se descartaron otras vías (MAE Market Data no cubre agro; Primary API pedía credenciales), paginación en ventanas de 30 días, filtro propio por segmento y símbolo (el filtro de la API no era confiable), cache por ventana y control de huecos. NOAA: mensual y diario, −999,99 como "sin dato", pulgadas a mm, control cruzado (inconsistencia de julio de 2023) y User-Agent académico.
7. **Limpieza y normalización.** Matba: unificar símbolos anuales con regex, resolver solapamientos de enero, quedarse con el disponible. Chicago: formato regional, 24 páginas vacías y 4 ceros como faltantes, índice continuo para 27 saltos de vencimiento. NOAA: pivoteo, 224 datos preliminares marcados, anomalías de lluvia.
8. **Qué predecimos.** El cambio porcentual, no el precio. Ejemplo: soja 375 → +0,3 % → 376. Razones: medir en precio engaña, XGBoost no extrapola y el porcentaje es comparable entre granos.
9. **Entrenamiento y prueba.** Partición temporal: entrenamiento abr 2023 – dic 2024 (validación trimestral en 2024), prueba ene 2025 – sep 2026 con reentrenamiento mensual. La purga evita usar etiquetas que todavía no se conocían.
10. **Los modelos.** 2 referencias (precio constante y tendencia), 3 familias (ElasticNet, XGBoost, ARIMA/ARIMAX) y 3 conjuntos de variables acumulativos (solo precio, + Chicago, + clima).
11. **Resultados.** R² contra precio constante: ARIMAX −0,06 / +0,02 / +0,04; XGBoost el peor. Ninguna mejora es significativa. A 90 días el error de ARIMAX es 16,8 USD/t contra 17,2.
12. **Cuánto aporta cada fuente.** Mismo modelo sumando información de a una: Chicago es lo que más ayuda; la lluvia casi nada; ElasticNet descartó casi todas las variables.
13. **Pronósticos.** ARIMAX desde el 24/09/2026: soja ≈ 370, maíz ≈ 197, trigo ≈ 232 USD/t a 90 días, con rangos amplios (soja 336–432). Cobertura del 80 % en la prueba, no garantizada a futuro.
14. **Conclusiones.** La web alcanzó para armar el dataset; el trabajo pesado fue limpiar e integrar; con estos datos el precio de hoy no se mejora.
15. **Próximos pasos.** Más historia, scraping diario automatizado, minería de texto, dólar y retenciones, clima de Sudamérica y combinación de modelos.
16. **Cierre.** Notebooks 01 (dataset) y 02 (modelos).

## Preguntas probables
- **¿Por qué no anda mejor?** A 30–90 días el precio disponible se comporta casi como un camino aleatorio; la información pública que usamos mejora apenas y no de forma significativa.
- **¿Hubo data leakage?** Se controló en cada paso (ver `docs/metodologia.md`, sección 7).
- **¿Por qué XGBoost es el peor?** Con pocas campañas, los árboles sobreajustan y no extrapolan fuera del rango histórico.
- **¿Por qué se parte el entrenamiento?** Es una serie de tiempo: hay que validar siempre hacia adelante y no mezclar fechas.
