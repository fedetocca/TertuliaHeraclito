#!/usr/bin/env python3
"""Arma nivel-2/hallazgos.json.

Cada regla asocia un patrón de cláusula con el artículo principal, la explicación
y los fallos que la sustentan. Los fallos citados fueron recuperados con
buscador.py / consultas.py; antes de escribir se verifica que ninguno esté
revocado (art. 32) ni sea posterior a la fecha de corte.

Uso:  python generar_hallazgos.py --contratos ../contratos --fallos ../fallos --salida ../hallazgos.json
"""
import argparse
import glob
import json
import os
import re

from buscador import cargar_fallos

CORTE = "2026-09-30"

# (patrón en el texto de la cláusula, artículo principal, fallos, explicación)
REGLAS = [
    (r"tres visitantes pernoctan simultáneamente", 20, ["F-058"],
     "La cláusula computa treinta noches de visita multiplicando tres visitantes por diez noches simultáneas y cobra un incremento de agua por superar el límite de veintisiete. El plenario F-058, obligatorio según el artículo 31, fijó que para el artículo 20 se cuentan las noches efectivas de ocupación y que las noches coincidentes se cuentan una sola vez: tres visitas durante diez noches simultáneas computan diez, no treinta. Con diez noches no se supera el límite de veintisiete y el artículo 20 no admite cargo alguno, aunque el consumo esté medido y sea inferior a 3,5%. El criterio contrario de la Sala (F-022) fue revocado expresamente por ese plenario y no es autoridad vigente (artículo 32)."),
    (r"renovación de celdas de la batería central fija", 16, ["F-037"],
     "La cláusula traslada al locatario las cuotas de renovación de celdas de la batería central fija, presentándolas como disponibilidad ordinaria de energía. El artículo 16 pone a cargo del locador la adquisición o sustitución de bienes comunes de servicio permanente y aclara que el pago periódico o fraccionado no lo convierte en consumo del artículo 15, que excluye los cargos que corresponden a la adquisición de un bien permanente. El plenario F-037, obligatorio (artículo 31), resolvió precisamente que la batería central fija es bien común permanente a cargo del propietario, que sus cuotas no son consumo y que sólo se traslada la electricidad variable medida. La doctrina de Sala que admitía el traslado (F-014) fue revocada por ese plenario (artículo 32)."),
    (r"alerta aislada del sensor", 18, ["F-106"],
     "La cláusula autoriza ingresar sin aviso, sin consentimiento y a cualquier hora por una alerta aislada del sensor, sin humo, agua, deformación ni corroboración técnica. El artículo 18 exige aviso de cuarenta y dos horas, consentimiento y horario de nueve a dieciocho, y sólo exceptúa el riesgo material inminente de incendio, inundación o derrumbe, con asistencia técnica. El plenario F-106, obligatorio (artículo 31), estableció que la alerta aislada sin corroboración técnica ni manifestación material no habilita el acceso excepcional; sólo lo habilita un riesgo corroborado (por ejemplo, alarma con olor a quemado verificado). La extensión general que admitía la alerta sola (F-043) fue revocada por ese plenario (artículo 32). La cláusula tampoco prevé asistencia técnica ni limitación a lo indispensable."),
    (r"referencia cromática de ingreso", 14, ["F-076"],
     "La cláusula califica como alteración reparable una diferencia homogénea de dos tonos tras doce ciclos con exposición solar, sin roturas, manchas ni desprendimiento, y obliga a pagar la pintura completa. El artículo 14 sólo permite descontar daño imputable con respaldo y dispone que el desgaste de uso normal no constituye daño. El plenario F-076, obligatorio (artículo 31), decidió que la decoloración homogénea por luz y uso es desgaste normal y que el pacto de pintar no crea daño; sólo roturas y manchas imputables probadas generan responsabilidad. La doctrina contraria de F-031 fue revocada por ese plenario (artículo 32). Además, la comparación cromática aislada no prueba por sí sola el daño (artículo 27)."),
    (r"Fondo Atenea", 12, ["F-097"],
     "Además del depósito de 1,35 cánones base se exige una adhesión no reintegrable de 0,45 al Fondo Atenea, administrado por el locador, cuya única función es respaldar deudas o daños del mismo contrato. El artículo 12 limita el depósito total, cualquiera sea su denominación, a 1,35 veces el canon base e incluye las sumas retenidas como garantía; el artículo 25 califica los aportes de cobertura por su función efectiva y sólo los distingue del depósito si retribuyen una prestación autónoma. El plenario F-097, obligatorio (artículo 31), resolvió que una adhesión destinada exclusivamente a cubrir riesgo de deuda o daño integra el depósito aunque sea no reintegrable. El total garantizado asciende así a 1,80 cánones y excede el tope. La doctrina contraria de F-009 fue revocada por ese plenario (artículo 32)."),
    (r"dos marcas automáticas de entrega", 26, ["F-104"],
     "La cláusula tiene por recibida de manera concluyente toda comunicación digital con dos marcas automáticas de entrega de la plataforma, sin respuesta humana ni otra prueba. El artículo 26 exige constancia de recepción, establece que el mero envío no la acredita, que quien invoca el aviso prueba su llegada y que el valor de los registros automatizados depende de su aptitud para acreditar la recepción del contenido. El plenario F-104, obligatorio (artículo 31), fijó que dos marcas de plataforma acreditan entrega técnica al dispositivo, no recepción humana concluyente del contenido, la que puede probarse con respuesta expresa o conducta posterior inequívoca. La doctrina de F-052, que las consideraba concluyentes, fue revocada por ese plenario (artículo 32). La cláusula invierte además la carga de la prueba fijada por la ley."),
    (r"doce días después de la firma", 4, [],
     "La cláusula difiere la entrega de la copia íntegra y los anexos a doce días después de la firma. El artículo 4 obliga al locador a entregar a cada parte una copia íntegra y legible, con inventario y anexos, dentro de cuatro días de la firma. El plazo pactado triplica el legal y queda sustituido por éste (artículo 3)."),
    (r"tributo municipal que grava la titularidad", 16, [],
     "La cláusula traslada íntegramente al locatario el tributo municipal que grava la titularidad del inmueble. El artículo 16 pone a cargo del locador los tributos sobre la propiedad, y el artículo 15 sólo permite trasladar consumos variables medidos y cargos de disponibilidad energética vinculados al uso; la propia cláusula reconoce que no corresponde a un servicio medido. El cargo sin causa autónoma tampoco puede sumarse al canon (artículo 7)."),
    (r"animales de asistencia que superen dieciocho", 19, [],
     "La cláusula prohíbe el ingreso de animales de asistencia de más de dieciocho kilogramos aunque tengan acreditación vigente. El artículo 19 dispone que el animal de asistencia acreditada no cuenta para el límite de cantidad ni de peso (que sólo rige para animales de compañía) y no admite recargo. La prohibición elimina una garantía obligatoria y se sustituye por el régimen legal (artículo 3)."),
    (r"plazo inicial de esta locación ordinaria es de doce ciclos", 5, [],
     "Se fija un plazo inicial de doce ciclos para una locación ordinaria. El artículo 5 establece una duración inicial mínima de diecinueve ciclos y sólo el supuesto del artículo 6 (estadía transitoria con constancia certificada de traslado o cursada y otra vivienda habitual) permite reducirla; la propia cláusula declara que no se invoca traslado ni estudios. El plazo se integra hasta el mínimo legal (artículos 3 y 5)."),
    (r"depósito de uno coma noventa cánones base", 12, [],
     "El depósito pactado es de 1,90 cánones base, que era el máximo anterior a la reforma. Desde el 01/03/2026 el artículo 12 (sustituido por el artículo 40, aplicable a este contrato de septiembre de 2026) fija el tope en 1,35 veces el canon base. No procede el máximo de 1,70 del artículo 13 porque la vivienda se entrega sin bienes muebles y las instalaciones fijas no cuentan. El exceso se reduce al límite legal (artículo 3)."),
    (r"indemnización de cero coma noventa cánones", 22, [],
     "La cláusula impone por salida anticipada, cumplidos cuatro ciclos y con veintitrés días de preaviso, una indemnización de 0,90 cánones vigentes. El artículo 22 permite en ese supuesto exigir como máximo 0,38 del canon vigente, y nada si la salida responde a una reparación esencial incumplida. El exceso se sustituye por el tope legal (artículo 3) y no puede sostenerse como penalidad fija (artículo 37)."),
    (r"interés simple diario de cero coma veinticinco", 11, [],
     "Se pacta un interés moratorio diario de 0,25% con máximo de 3,8% por ciclo. El artículo 11, en su texto vigente según el artículo 40, limita el interés simple diario a 0,08% del canon vencido impago y su acumulación a 2,4% por ciclo. Ambos valores exceden los topes y se sustituyen por el régimen legal (artículo 3); respetar la tolerancia del artículo 10 no salva el exceso."),
    (r"inspeccionar la vivienda con doce horas de aviso", 18, [],
     "La cláusula permite inspeccionar con doce horas de aviso, en cualquier horario y sin aceptación del ocupante, aun sin emergencia. El artículo 18 exige aviso de cuarenta y dos horas, consentimiento y horario entre las nueve y las dieciocho; el ingreso sin esos requisitos sólo procede ante riesgo material inminente de incendio, inundación o derrumbe, y no basta el deseo de inspeccionar. Se afecta además la intimidad del ocupante (artículo 28)."),
    (r"todo el depósito permanecerá retenido por sesenta días", 14, [],
     "La cláusula retiene todo el depósito durante sesenta días tras la entrega de llaves, sin individualizar daños ni gastos. El artículo 14 obliga a restituir el saldo dentro de once días y sólo admite descontar deuda individualizada y daño imputable con respaldo; la única reserva permitida es de hasta 0,22 del último canon por nueve días adicionales, para una reparación ya identificada sin presupuesto, entregando el resto en término."),
    (r"dentro de treinta días de recibido el aviso", 17, [],
     "Se otorgan al locador treinta días para resolver reparaciones estructurales y el mismo plazo ante peligro actual para el suministro esencial. El artículo 17 exige resolver el defecto estructural dentro de ocho días y el peligro actual para salud o suministro esencial dentro de dieciocho horas desde el aviso, con facultad del locatario de intervenir y compensar ante el incumplimiento. La ampliación de plazos reduce una garantía de habitación obligatoria (artículo 3)."),
    (r"arancel de apertura equivalente a cero coma diecisiete", 37, [],
     "Se cobra obligatoriamente al firmar un arancel de apertura de 0,17 del canon base invocando el artículo 36. Ese artículo fue derogado íntegramente por el artículo 40 desde el 01/03/2026 y carece de vigencia para este contrato de septiembre de 2026. El artículo 37 prohíbe imponer tasa de apertura fuera de los gastos expresamente autorizados; el cargo no retribuye un trabajo separado y libremente solicitado, sino que condiciona el acceso a la vivienda."),
    (r"incrementarse un doce por ciento al completar cada tres ciclos", 8, [],
     "La cláusula prevé aumentos del 12% cada tres ciclos. El artículo 8 exige seis ciclos completos desde la fijación anterior y limita cada incremento al 7,3% del canon anterior o a la variación positiva del índice cívico publicado (artículo 38), si fuera menor. Al no haberse pactado la opción cooperativa del artículo 9 no hay excepción aplicable; tanto el intervalo como el porcentaje violan los límites obligatorios."),
    (r"cortar el suministro de agua y sustituir la cerradura", 24, [],
     "La cláusula autoriza al locador, ante cualquier deuda de canon, a cortar el agua y cambiar la cerradura hasta el pago. El artículo 24 prohíbe cortar servicios, cambiar cerraduras o impedir el acceso del ocupante para cobrar o recuperar la vivienda, y aclara que ni la deuda ni una cláusula de autorización alteran la prohibición. El cobro y la recuperación deben pedirse al Tribunal (artículos 23 y 24); la firma no convalida la renuncia (artículo 3)."),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contratos", default="../contratos")
    ap.add_argument("--fallos", default="../fallos")
    ap.add_argument("--salida", default="../hallazgos.json")
    a = ap.parse_args()

    fallos = cargar_fallos(a.fallos)
    hallazgos = []
    for ruta in sorted(glob.glob(os.path.join(a.contratos, "C-*.md"))):
        texto = open(ruta, encoding="utf-8").read()
        contrato = re.search(r"CONTRATO DE LOCACIÓN (C-\d+)", texto).group(1)
        for clausula, cuerpo in re.findall(r"^Cláusula (C\d{2})\. (.+)$", texto, flags=re.M):
            for patron, articulo, citas, explicacion in REGLAS:
                if re.search(patron, cuerpo):
                    for c in citas:  # control de vigencia de cada cita
                        f = fallos[c]
                        assert not f.revocado_por, f"{c} está revocado por {f.revocado_por}"
                        assert f.fecha <= CORTE, f"{c} es posterior al corte"
                    assert 40 <= len(explicacion) <= 3000 and len(set(citas)) == len(citas) <= 8
                    hallazgos.append({"contrato": contrato, "clausula": clausula, "articulo": articulo,
                                      "explicacion": explicacion, "fallos": citas})
                    break
    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump(hallazgos, fh, ensure_ascii=False, indent=2)
    print(len(hallazgos), "hallazgos ->", a.salida)


if __name__ == "__main__":
    main()
