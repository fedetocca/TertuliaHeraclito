#!/usr/bin/env python3
"""Consultas usadas para fundar los hallazgos del nivel 2.

Ejecuta, para cada tipo de cláusula que requiere interpretación judicial, la
consulta BM25 y lista los fallos recuperados con su estado (plenario, Sala,
revocado). Uso:  python consultas.py --fallos ../fallos
"""
import argparse

from buscador import cargar_fallos, construir_indice, consultar, estado

CONSULTAS = [
    # (tema, artículo, texto de consulta)
    ("Cómputo de noches de visitantes simultáneos", 20, "invitados noches coincidentes simultáneas se multiplican por personas límite veintisiete"),
    ("Batería central: cuotas de celdas", 16, "batería central fija adquisición cuotas consumo energía ordinaria bien común permanente"),
    ("Ingreso por alerta aislada de sensor", 18, "alerta aislada sensor sin corroboración técnica ingreso acceso excepcional"),
    ("Decoloración homogénea y pintura al egreso", 14, "decoloración homogénea luz uso desgaste normal pintura daño"),
    ("Adhesión no reintegrable a fondo de cobertura", 12, "adhesión no reintegrable cobertura riesgo deuda daño integra depósito prestación autónoma"),
    ("Marcas automáticas de entrega como recepción", 26, "marcas automáticas plataforma entrega recepción concluyente respuesta humana"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fallos", default="../fallos")
    ap.add_argument("--corte", default="2026-09-30")
    a = ap.parse_args()
    fallos = cargar_fallos(a.fallos)
    indice, fragmentos = construir_indice(fallos)
    for tema, articulo, texto in CONSULTAS:
        print(f"\n=== {tema} (art. {articulo}) :: {texto}")
        for r in consultar(indice, fragmentos, fallos, texto, k=5, articulo=articulo, corte=a.corte):
            print(f"{r['fallo']} [{r['puntaje']}] {r['fecha']} {estado(r)}\n    {r['fragmento'][:400]}")


if __name__ == "__main__":
    main()
