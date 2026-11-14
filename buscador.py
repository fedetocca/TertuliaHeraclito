#!/usr/bin/env python3
"""Buscador BM25 sobre el archivo del Tribunal de Locaciones de Calípolis.

Motor de búsqueda: rank_bm25 (código abierto, licencia Apache-2.0).

Etapas (cada una en su función):
  1. cargar_fallos()   -> lee fallos/F-NNN.md y extrae metadatos y secciones.
  2. construir_indice()-> fragmenta por sección/párrafo e indexa con BM25Okapi.
  3. consultar()       -> recupera fragmentos con su número de sentencia.

Uso:
  python buscador.py --fallos ../fallos "alerta aislada sensor ingreso sin aviso"
  python buscador.py --fallos ../fallos --articulo 18 --k 8 "alerta sensor ingreso"
  python buscador.py --fallos ../fallos --todo "batería central cuotas"   # incluye actuaciones
"""
import argparse
import glob
import os
import re
import unicodedata
from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi

SECCION_RE = re.compile(r"^(I|II|III|IV|V|VI|VII|VIII)\. (.+)$")
CABECERA_RE = re.compile(r"Sentencia (F-\d{3})\. (Sala \w+|Plenario)\. Publicación: (\d{2})/(\d{2})/(\d{4})\.")
ARTICULOS_RE = re.compile(r"se encuadra en los artículos ([\d, ]+) de Las Leyes")
REVOCA_RE = re.compile(r"[Ss]e revoca expresamente la doctrina de (F-\d{3})")
# Secciones con contenido jurídico; las actuaciones de trámite son ruido probatorio.
SECCIONES_DECISORIAS = ("Vistos", "Antecedentes", "Consideraciones", "Deliberación", "Parte resolutiva")
STOPWORDS = set(
    "a al ante bajo con contra de del desde durante e el ella en entre es esa ese eso esta este esto "
    "la las lo los más ni no o para pero por que se si sin sobre su sus un una uno y ya como cuando "
    "le les fue son ser ha han hay".split()
)


@dataclass
class Fallo:
    numero: str            # F-NNN
    organo: str            # "Sala Primera" | "Sala Segunda" | "Plenario"
    fecha: str             # AAAA-MM-DD (ordenable)
    articulos: list
    secciones: dict        # nombre de sección -> lista de párrafos
    revoca: list = field(default_factory=list)       # fallos cuya doctrina revoca (art. 32)
    revocado_por: str = ""                            # plenario que lo revocó, si existe

    @property
    def es_plenario(self):
        return self.organo == "Plenario"


@dataclass
class Fragmento:
    numero: str
    seccion: str
    texto: str


def normalizar(texto):
    """Minúsculas, sin tildes, sólo palabras; quita palabras vacías."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return [t for t in re.findall(r"[a-z0-9ñ]+", texto) if t not in STOPWORDS]


# ---------------------------------------------------------------- 1. CARGA
def cargar_fallos(carpeta):
    """Lee cada sentencia, separa sus secciones y detecta plenarios y revocaciones."""
    fallos = {}
    for ruta in sorted(glob.glob(os.path.join(carpeta, "F-*.md"))):
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
        cab = CABECERA_RE.search(texto)
        if not cab:
            raise ValueError(f"Cabecera no reconocida en {ruta}")
        numero, organo, dd, mm, aaaa = cab.groups()
        secciones, actual = {"Cabecera": []}, "Cabecera"
        for parrafo in (p.strip() for p in texto.split("\n\n")):
            if not parrafo:
                continue
            m = SECCION_RE.match(parrafo)
            if m:
                actual = m.group(2)
                secciones.setdefault(actual, [])
            elif parrafo.startswith("Anexo de actuaciones"):
                actual = "Anexo de actuaciones"
                secciones.setdefault(actual, [])
            else:
                secciones[actual].append(parrafo)
        arts = ARTICULOS_RE.search(texto)
        resolutiva = " ".join(secciones.get("Parte resolutiva", []))
        fallos[numero] = Fallo(
            numero=numero,
            organo=organo,
            fecha=f"{aaaa}-{mm}-{dd}",
            articulos=sorted(int(a) for a in arts.group(1).replace(" ", "").split(",")) if arts else [],
            secciones=secciones,
            revoca=REVOCA_RE.findall(resolutiva),
        )
    # Art. 32: sólo un plenario revoca, y de forma expresa.
    for f in fallos.values():
        if f.es_plenario:
            for objetivo in f.revoca:
                if objetivo in fallos:
                    fallos[objetivo].revocado_por = f.numero
    return fallos


# ----------------------------------------------------------- 2. INDEXACIÓN
def construir_indice(fallos, incluir_actuaciones=False):
    """Un fragmento por párrafo de cada sección; índice BM25 sobre los tokens."""
    fragmentos = []
    for f in fallos.values():
        for seccion, parrafos in f.secciones.items():
            if seccion == "Cabecera":
                continue
            if not incluir_actuaciones and seccion not in SECCIONES_DECISORIAS:
                continue
            for p in parrafos:
                fragmentos.append(Fragmento(f.numero, seccion, p))
    corpus = [normalizar(fr.texto) for fr in fragmentos]
    return BM25Okapi(corpus), fragmentos


# -------------------------------------------------------------- 3. CONSULTA
def consultar(indice, fragmentos, fallos, consulta, k=8, articulo=None, corte=None):
    """Devuelve los k fallos mejor puntuados (mejor fragmento de cada uno).

    articulo: filtra por artículo debatido. corte: AAAA-MM-DD, descarta fallos posteriores.
    """
    puntajes = indice.get_scores(normalizar(consulta))
    mejor = {}
    for i, puntaje in enumerate(puntajes):
        fr = fragmentos[i]
        f = fallos[fr.numero]
        if puntaje <= 0:
            continue
        if articulo is not None and articulo not in f.articulos:
            continue
        if corte and f.fecha > corte:
            continue
        if fr.numero not in mejor or puntaje > mejor[fr.numero][0]:
            mejor[fr.numero] = (puntaje, fr)
    orden = sorted(mejor.items(), key=lambda kv: -kv[1][0])[:k]
    return [
        {
            "fallo": numero,
            "puntaje": round(float(p), 3),
            "organo": fallos[numero].organo,
            "fecha": fallos[numero].fecha,
            "articulos": fallos[numero].articulos,
            "revoca": fallos[numero].revoca,
            "revocado_por": fallos[numero].revocado_por,
            "seccion": fr.seccion,
            "fragmento": fr.texto,
        }
        for numero, (p, fr) in orden
    ]


def estado(r):
    if r["organo"] == "Plenario":
        return "PLENARIO obligatorio" + (f" (revoca {', '.join(r['revoca'])})" if r["revoca"] else "")
    if r["revocado_por"]:
        return f"REVOCADO por {r['revocado_por']} (sólo antecedente histórico, art. 32)"
    return "Sala (persuasivo, art. 31)"


def main():
    ap = argparse.ArgumentParser(description="Buscador BM25 de sentencias del Tribunal de Locaciones")
    ap.add_argument("consulta")
    ap.add_argument("--fallos", default="../fallos", help="carpeta con F-NNN.md")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--articulo", type=int, default=None)
    ap.add_argument("--corte", default="2026-09-30", help="fecha de corte AAAA-MM-DD")
    ap.add_argument("--todo", action="store_true", help="indexar también actuaciones de trámite y anexos")
    a = ap.parse_args()

    fallos = cargar_fallos(a.fallos)
    indice, fragmentos = construir_indice(fallos, incluir_actuaciones=a.todo)
    for r in consultar(indice, fragmentos, fallos, a.consulta, a.k, a.articulo, a.corte):
        print(f"{r['fallo']}  [{r['puntaje']}]  {r['fecha']}  arts. {r['articulos']}  {estado(r)}")
        print(f"   ({r['seccion']}) {r['fragmento'][:600]}")


if __name__ == "__main__":
    main()
