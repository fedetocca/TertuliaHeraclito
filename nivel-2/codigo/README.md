# Buscador de sentencias — nivel 2

Buscador BM25 sobre las 120 sentencias del Tribunal de Locaciones de Calípolis, usado para
fundar `../hallazgos.json`. Motor de código abierto: [`rank_bm25`](https://github.com/dorianbrown/rank_bm25) (Apache-2.0).

## Entradas

- `../fallos/F-NNN.md`: sentencias (cabecera con órgano y fecha, secciones I a VI y anexo de actuaciones).
- `../contratos/C-NNN.md`: contratos con cláusulas C01 a C10 (sólo para `generar_hallazgos.py`).
- Normas: `leyes-de-platon.md` (recibidas en el nivel 1).

## Instalación

```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## Archivos

| Archivo | Función |
|---|---|
| `buscador.py` | **Carga** (`cargar_fallos`), **indexación** (`construir_indice`) y **consulta** (`consultar`). |
| `consultas.py` | Consultas ejecutadas para cada tipo de cláusula que requiere interpretación judicial. |
| `generar_hallazgos.py` | Aplica las reglas a los contratos, verifica vigencia de las citas y escribe el JSON. |
| `requirements.txt` | Dependencia única. |

## Cómo funciona

1. **Carga**: lee cada `F-NNN.md`, extrae número, órgano (Sala/Plenario), fecha de publicación, artículos
   debatidos y secciones. Detecta la frase "Se revoca expresamente la doctrina de F-NNN" en la parte
   resolutiva de los plenarios y marca al fallo revocado (art. 32).
2. **Indexación**: un fragmento por párrafo de las secciones decisorias (Vistos, Antecedentes,
   Consideraciones, Deliberación, Parte resolutiva). Tokenización en minúsculas, sin tildes ni palabras
   vacías; índice `BM25Okapi` en memoria. Con `--todo` se indexan también las actuaciones de trámite.
3. **Consulta**: puntúa los fragmentos, conserva el mejor por sentencia y devuelve número `F-NNN`,
   órgano, fecha, estado (plenario obligatorio / Sala persuasiva / revocado) y el fragmento. Filtros
   opcionales por artículo y por fecha de corte (30/09/2026 por defecto).

## Comando de consulta

```
python buscador.py --fallos ../fallos "alerta aislada sensor ingreso sin aviso"
python buscador.py --fallos ../fallos --articulo 26 --k 5 "marcas automáticas entrega recepción concluyente"
python consultas.py --fallos ../fallos          # todas las consultas usadas
python generar_hallazgos.py --contratos ../contratos --fallos ../fallos --salida ../hallazgos.json
```

## Criterio de cita (arts. 31 y 32)

Sólo se citan plenarios vigentes a la fecha de corte que deciden la cuestión de la cláusula. Los fallos
de Sala revocados (F-009, F-014, F-022, F-031, F-043 en su extensión general, F-052) se mencionan en la
explicación únicamente como antecedente histórico y no figuran en `fallos`. Las cláusulas que chocan con
un tope o prohibición expresos de la ley llevan `fallos` vacío.
