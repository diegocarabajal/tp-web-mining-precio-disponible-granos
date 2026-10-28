"""
Scraping de Precios Chicago/Kansas (CME Group) - Bolsa de Comercio de Rosario
https://www.bcr.com.ar/es/mercados/mercado-de-granos/cotizaciones/cotizaciones-internacionales/chicagokansas-cme-group-<ID>

Cada día hábil tiene su propia página con un ID consecutivo al final de la URL:
    2460 -> 23/12/2022   3248 -> 16/01/2026   3249 -> 19/01/2026 (feriado)
    3250 -> 20/01/2026   3400 -> 24/08/2026
(los fines de semana no consumen número; los feriados sí, con la tabla en "FERIADO").

Para cada fecha toma, de la posición más cercana (primera fila con dato en esa columna):
    Trigo Chicago/2, Maíz Chicago/3, Soja Chicago/4
y guarda también el mes de contrato del que salió cada valor.

Uso:
    pip install requests beautifulsoup4
    python scrap_bcr_chicago.py                       # 01/01/2023 a hoy -> bcr_chicago.csv
    python scrap_bcr_chicago.py --desde 2024-01-01 --salida otro.csv
    python scrap_bcr_chicago.py --debug 3250          # guarda el HTML de una página para inspeccionar
    python scrap_bcr_chicago.py --pausa 3             # más lento, si el sitio devuelve 503

Si el sitio corta (503/429), el script espera y reintenta. Si no se recupera, guarda el
progreso en bcr_chicago_cache.jsonl, escribe el CSV con lo que tiene y al volver a correrlo
retoma desde donde quedó.
"""
import argparse
import csv
import json
import random
import re
import sys
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

BASE = ("https://www.bcr.com.ar/es/mercados/mercado-de-granos/cotizaciones/"
        "cotizaciones-internacionales/chicagokansas-cme-group-{}")

COLUMNAS = ["Trigo Chicago/2", "Maíz Chicago/3", "Soja Chicago/4"]
# Orden de la tabla en el sitio (fallback si el encabezado no se puede leer)
ORDEN_SITIO = ["Trigo Chicago/1", "Trigo Chicago/2", "Maíz Chicago/3",
               "Soja Chicago/4", "Aceite Soja Chicago/5", "Harina Soja Chicago/6"]

ID_INICIO = 2450          # algo antes del 01/01/2023 (2460 = 23/12/2022)
MAX_FALLOS_SEGUIDOS = 15  # cortar cuando ya no hay más páginas
PAUSA = 1.5               # segundos base entre requests (+ hasta otro tanto al azar)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def a_float(txt):
    txt = norm(txt).replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def fila_expandida(tr):
    """Devuelve el texto de cada celda de la fila, repitiendo las celdas con colspan."""
    out = []
    for c in tr.find_all(["td", "th"]):
        span = int(c.get("colspan", 1) or 1)
        out.extend([norm(c.get_text())] * span)
    return out


def parsear(html):
    soup = BeautifulSoup(html, "html.parser")
    texto = soup.get_text(" ")

    # Fecha de la tabla ("Precios de cierre ... dd/mm/yyyy"); fallback: meta published_time
    m = re.search(r"Precios de cierre.*?(\d{2}/\d{2}/\d{4})", texto, re.S)
    if not m:
        meta = soup.find("meta", attrs={"property": "article:published_time"}) \
            or soup.find("meta", attrs={"name": "article:published_time"})
        if meta and re.match(r"\d{2}/\d{2}/\d{4}", meta.get("content", "")):
            m = re.match(r"(\d{2}/\d{2}/\d{4})", meta["content"])
    if not m:
        return None
    fecha = datetime.strptime(m.group(1), "%d/%m/%Y").date()

    # Buscar la tabla que tiene "Soja Chicago" en el encabezado
    tabla = None
    for t in soup.find_all("table"):
        if "Soja Chicago" in t.get_text():
            tabla = t
            break
    if tabla is None:
        return None

    filas = [fila_expandida(tr) for tr in tabla.find_all("tr")]
    filas = [f for f in filas if any(f)]
    idx_header = next((i for i, f in enumerate(filas) if any("Soja Chicago" in c for c in f)), None)
    if idx_header is None:
        return None
    header = filas[idx_header]
    datos = filas[idx_header + 1:]

    res = {"fecha": fecha, "feriado": "FERIADO" in tabla.get_text()}

    for col in COLUMNAS:
        # Columna del precio según el encabezado (con colspan expandido)
        idx = next((i for i, h in enumerate(header) if h.replace(" ", "") == col.replace(" ", "")), None)
        if idx is None or len(header) < 13:
            idx = 1 + 2 * ORDEN_SITIO.index(col)  # posición + (precio, variación) x 6
        valor, var, pos = None, None, None
        for f in datos:
            if len(f) <= idx or not re.match(r"[A-Za-z]{3}-\d{2}", f[0]):
                continue
            v = a_float(f[idx])
            if v is not None:
                valor, pos = v, f[0]
                var = a_float(f[idx + 1]) if len(f) > idx + 1 else None
                break
        res[col] = valor
        res[col + " var"] = var
        res[col + " posición"] = pos
    return res


class BloqueoServidor(Exception):
    """El sitio sigue devolviendo 429/5xx después de todos los reintentos."""


ESPERAS_REINTENTO = [15, 30, 60, 120, 300]  # segundos, ante 429/503/errores de red


def bajar(sesion, id_pag):
    """Devuelve el HTML, o None si la página no existe (404).
    Ante 429/5xx o errores de red espera y reintenta; si no se recupera, lanza BloqueoServidor
    (NO se cuenta como página inexistente)."""
    for i, espera in enumerate([0] + ESPERAS_REINTENTO):
        if espera:
            print(f"  ID {id_pag}: el servidor rechaza requests, espero {espera}s "
                  f"(reintento {i}/{len(ESPERAS_REINTENTO)})", file=sys.stderr)
            time.sleep(espera)
        try:
            r = sesion.get(BASE.format(id_pag), timeout=30)
        except requests.RequestException as e:
            print(f"  ID {id_pag}: error de red {e}", file=sys.stderr)
            continue
        if r.status_code == 404:
            return None
        if r.status_code == 429 or r.status_code >= 500:
            ra = r.headers.get("Retry-After", "")
            if ra.isdigit():
                time.sleep(int(ra))
            continue
        r.raise_for_status()
        return r.text
    raise BloqueoServidor(f"ID {id_pag}: el sitio sigue devolviendo error")


def cargar_cache(ruta):
    filas = {}
    try:
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                d = json.loads(linea)
                filas[d["id"]] = d
    except FileNotFoundError:
        pass
    return filas


def escribir_csv(cache, salida, desde, hasta):
    registros = [d for d in cache.values() if d.get("fecha")
                 and desde.isoformat() <= d["fecha"] <= hasta.isoformat()]
    vistos, unicos = set(), []
    for r in sorted(registros, key=lambda x: (x["fecha"], x["id"])):
        if r["fecha"] not in vistos:
            vistos.add(r["fecha"])
            unicos.append(r)

    campos = ["Fecha"]
    for c in COLUMNAS:
        campos += [c, f"{c} variación", f"{c} posición"]
    campos += ["Feriado", "ID página"]

    with open(salida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(campos)
        for r in unicos:
            fila = [date.fromisoformat(r["fecha"]).strftime("%d/%m/%Y")]
            for c in COLUMNAS:
                fila += [r[c], r[c + " var"], r[c + " posición"]]
            fila += ["S" if r["feriado"] else "N", r["id"]]
            w.writerow(["" if v is None else str(v).replace(".", ",") if isinstance(v, float) else v
                        for v in fila])
    return len(unicos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2023-01-01")
    ap.add_argument("--hasta", default=date.today().isoformat())
    ap.add_argument("--salida", default="bcr_chicago.csv")
    ap.add_argument("--cache", default="bcr_chicago_cache.jsonl",
                    help="progreso guardado; si existe, se retoma desde ahí")
    ap.add_argument("--id-inicio", type=int, default=ID_INICIO)
    ap.add_argument("--pausa", type=float, default=PAUSA)
    ap.add_argument("--debug", type=int, help="guarda el HTML de ese ID y muestra el parseo")
    a = ap.parse_args()

    sesion = requests.Session()
    sesion.headers.update(HEADERS)

    if a.debug:
        html = bajar(sesion, a.debug)
        open(f"bcr_{a.debug}.html", "w", encoding="utf-8").write(html or "")
        print(parsear(html) if html else "Sin página")
        return

    desde = date.fromisoformat(a.desde)
    hasta = date.fromisoformat(a.hasta)

    cache = cargar_cache(a.cache)
    ids_ok = [i for i, d in cache.items() if d.get("fecha")]
    id_pag = max(ids_ok) + 1 if ids_ok else a.id_inicio
    if ids_ok:
        print(f"Retomando: {len(ids_ok)} páginas ya bajadas, sigo desde el ID {id_pag}")

    fallos = 0
    try:
        with open(a.cache, "a", encoding="utf-8") as fc:
            while fallos < MAX_FALLOS_SEGUIDOS:
                html = bajar(sesion, id_pag)
                r = parsear(html) if html else None
                if r is None:
                    fallos += 1          # página inexistente / sin tabla
                else:
                    fallos = 0
                    if r["fecha"] > hasta:
                        break
                    r["id"] = id_pag
                    r["fecha"] = r["fecha"].isoformat()
                    cache[id_pag] = r
                    fc.write(json.dumps(r, ensure_ascii=False) + "\n")
                    fc.flush()
                    estado = "FERIADO" if r["feriado"] else " | ".join(
                        f"{c}: {r[c]}" for c in COLUMNAS)
                    print(f"{id_pag} {date.fromisoformat(r['fecha']):%d/%m/%Y}  {estado}")
                id_pag += 1
                time.sleep(a.pausa + random.uniform(0, a.pausa))
    except BloqueoServidor as e:
        print(f"\n{e}. Progreso guardado en {a.cache}: volvé a correr el script "
              f"más tarde y retoma desde el ID {id_pag}.", file=sys.stderr)
    except KeyboardInterrupt:
        print(f"\nInterrumpido. Progreso guardado en {a.cache}.", file=sys.stderr)

    n = escribir_csv(cache, a.salida, desde, hasta)
    print(f"\n{n} fechas guardadas en {a.salida}")


if __name__ == "__main__":
    main()