# Motor de cierre del PPDI — validado contra PTAR Cajamarca

Reproduce el cálculo del PPDI del modelo aprobado sin Excel y sin Solver.

## Resultado de la validación (14-set-2026)

    PPDI base mensual resuelto  :      3,872.7122 S/ miles
    PPDI base mensual del libro :      3,872.7122 S/ miles
    Diferencia                  :        0.000000   (+0.000000 %)

Y las seis series intermedias calzan con desvío máximo 0.000000 contra los
valores en caché del libro: PPDI cobrado, ingresos financieros, impuesto a la
renta, efecto neto de IGV, saldo del activo financiero y flujo de caja antes de
deuda. La tasa implícita del activo financiero sale en 0.0086962975 mensual
(10.949 % anual), idéntica a la del libro.

El cierre converge a seis decimales en 50 iteraciones de bisección, en 0.7
segundos. Buscar Objetivo no hace falta.

## Archivos

- `extraer_primitivos.py` — lee el .xlsm y saca las series que NO dependen del
  PPDI (costo de obra, fideicomiso, seguros, garantías, reembolso, costo de
  estructuración, comisión, gastos financieros de la deuda) más el calendario.
  Escribe `cajamarca_primitivos.json`. No ejecuta macros.
- `motor_cajamarca.py` — el motor. Reconstruye el activo financiero, el estado
  de resultados, el bloque tributario y el flujo de IGV, y resuelve el PPDI
  base mensual que hace VAN(FC antes de deuda ; WACC) = 0.
- `cajamarca_primitivos.json` — las primitivas ya extraídas.

## Cómo correrlo

    pip install openpyxl
    python extraer_primitivos.py     # necesita el .xlsm en el mismo directorio
    python motor_cajamarca.py

## Lo que quedó replicado

- Activo financiero con tasa implícita igual a la TIR de sus propios flujos
  (en el libro es una referencia circular resuelta por cálculo iterativo).
- PPDI devengado mensual y cobrado al cierre de cada trimestre calendario,
  con el primer cobro en el primer cierre de trimestre posterior al inicio del
  periodo de pago.
- Bloque tributario: deducción del ingreso financiero durante la construcción,
  adición posterior en cuotas de 1/15 mientras corre el PPDI, arrastre de
  pérdidas y base imponible.
- IGV con recuperación anticipada a un mes y crédito fiscal acumulado.

## Lo que todavía no está en el motor

El PPDMO (fijo y variable) y su cierre contra el VAN financiero al Ke, el
dimensionamiento de la deuda por cobertura, y la escritura del libro Excel de
salida. Los gastos financieros de la deuda entran hoy como primitiva extraída
del libro; para un proyecto nuevo hay que calcularlos.

---

## San Martín (Hitos Funcionales) — validado el 14-sep-2026

`motor_sanmartin.py` (PPDI) + `motor_ppdmo_sm.py` (PPDMO) + `ipm_sm.py` (reajuste)
reproducen el libro aprobado **al céntimo**:

| Magnitud | Motor | Libro |
|---|---|---|
| PPDI anual (`Control!C16`) | 97 607 149.9419 | 97 607 149.9421 |
| Referencia PPDMO (`Control!C49`) | 5 683 476.2269 | 5 683 476.2269 |
| Intereses de construcción | 66 454 727.9311 | 66 454 727.9311 |
| Deuda desembolsada | 558 486 229.4540 | 558 486 229.4540 |
| Impuesto a la renta | 188 359 633.52 | 188 359 633.53 |
| VAN del FCF (`FC!D80`) | 0.00 | 0.00 |

Piezas que cubre, además de lo que ya hacía Cajamarca:

- Punto fijo de las necesidades de financiamiento: los intereses y comisiones de
  construcción se capitalizan y vuelven a financiarse. El saldo de deuda vive solo
  dentro de la etapa D+C+PM (`Nec_Fin!F67 = +E70*F6`); ese es el detalle que hace
  o rompe la convergencia.
- **Dimensionamiento de deuda por cobertura**: amortización = mín(saldo, máx(0,
  FCSD/RCSD + intereses + comisiones)), con RCSD 1.25 y cuenta de reserva (CRSD)
  al 50 % del servicio del año siguiente. Ya no entra como primitiva del libro.
- Bloque tributario anual completo: participación de trabajadores, arrastre de
  pérdidas sistema B al 50 %, amortización del CAPEX a lo largo del pago del PPDI
  y de los gastos financieros de construcción en diez años.
- Reajuste por IPM: ingresos con gatillo de 3 % y truncado a 5 decimales
  (`Hip_Mensual!33`), OPEX sin gatillo (`Hip_Mensual!35`). Replicado con desvío
  0.0000000000 contra las 336 columnas del libro.

`correr_sanmartin.py` corre cuatro escenarios y escribe `sanmartin_resultados.txt`
y `resultado_sm.json`. Resultado con parámetros al 14-sep-2026: PPDI anual
96 637 183.52 y referencia mensual del PPDMO 5 595 176.35 (5 464 330.39 si además
se actualiza el IPM al 2.67 %).

Documento con el contraste completo y las fuentes:
https://claude.ai/code/artifact/0c2495ba-363c-4bc9-9888-89be03800112

---

## Aviso para quien construya el PPDMO de Cajamarca

**El cierre del PPDMO no es el mismo en los dos modelos.** Verificado contra los
libros el 14-set-2026.

- **San Martín** cierra el PPDMO **completo**: el Solver mueve `Control!C49`, que
  vía `Ingresos!D90` escala a la vez la pata fija por hito (`Ingresos!D94:D97`) y
  el precio unitario variable (`Ingresos!D109`). Es lo que hace `motor_ppdmo_sm.py`.
- **Cajamarca** cierra **solo la pata variable**: Buscar Objetivo mueve
  `Resumen!J6` (`Tarifa_Media_Vta`) contra `M.Sombra!D74` = 0, y esa celda alimenta
  únicamente `PPDMO!D26`, el precio por kg de DBO5. La pata fija sale de costos y
  queda fuera del cierre: `PPDMO!D21` = promedio de costos fijos (`Costos!E41`)
  ÷ 12 × factor de ajuste × (1 + `Margen_CF`), con `Margen_CF` = 15 % fijo en
  `Inputs!D155`.

Copiar el módulo de San Martín para Cajamarca da un resultado equivocado: en
Cajamarca todo el remanente del flujo de caja financiero se carga sobre el
81.3 % del PPDMO
(S/ 28 935 miles al año de pata variable contra S/ 6 672 miles de pata fija),
mientras que en San Martín se reparte sobre el 100 %.

---

## Cajamarca completo (2026-09-15)

Tres modulos nuevos, los tres validados contra el libro antes de usarlos:

- **`deuda_cajamarca.py`** — la hoja `Deuda`, exacta mes a mes (desvio
  0.000000000 en el interes, la cuota, el servicio y el saldo). **Cajamarca no
  dimensiona por cobertura**, a diferencia de San Martin: la linea es 80 % del
  costo de obra y el servicio es una **anualidad de cuota constante**
  (`-PMT(tasa mensual, 144, saldo al mes base)`), con la amortizacion como
  residuo. Durante la obra el servicio es cero y el interes se capitaliza.
- **`ipm_cajamarca.py`** — el factor de reajuste de ingresos (`PPDMO!18`),
  desvio 0.000000000000 en los 318 meses. Gatillo de 3 % y TRUNC a 5 decimales.
- **`sombra_cajamarca.py`** — el modelo sombra. Reproduce las series
  trimestrales del PPDMO fijo y variable con desvio 1e-9 y **cierra la tarifa
  en 4.3176689715 contra las 4.3176689715 del libro**.

Con esto **el PPDI de Cajamarca deja de ser una banda**: 46 362.15 S/ miles al
ano con los parametros de hoy, por debajo de los dos extremos que se habian
estimado (46 458 y 47 008), porque escalar los gastos financieros por
Kd_nuevo/Kd_libro subestima el alza: el interes sube 10.44 % cuando el Kd sube
8.66 %, ya que el interes de obra se capitaliza.

**Cajamarca indexa con dos indices distintos**, y esto importa: los ingresos con
el **IPM** (`Inputs!D35`, con gatillo de 3 %) y los costos con el **IPC de largo
plazo** (`Inputs!N23` = 2.00 %, sin gatillo, via `'OPEX proyecto'!13`). Cambiar
el IPM mueve solo la pata de ingresos. En San Martin los dos son IPM.

Resultados con IPM 2.67 % en `cajamarca_ipm267.json`, resumen y malla trimestral.

## Excel de salida con formulas vivas (2026-09-15)

`escribir_excel.py` + `correr_generador.py` producen
**`PTAR_Cajamarca_generado.xlsx`**: cinco hojas, `Resumen`, `Inputs`, `Deuda`,
`PPDMO` y `Flujo`, con formulas que apuntan a nombres definidos sobre `Inputs`.
Cambiar el Kd, el IPM o el tamano de deuda recalcula el libro entero. El cierre
queda como en los libros aprobados: la tarifa y el PPDI son celdas de entrada y
`Flujo` trae la celda de VAN que Buscar Objetivo lleva a cero; el motor ya las
deja resueltas, asi que el libro abre cuadrado.

**Verificado recalculando de verdad.** Se abre el xlsx con LibreOffice Calc en
modo headless, se recalcula y se leen los resultados: el `Resumen` devuelve
46 362.1457 de PPDI, 6 679.9101 de PPDMO fijo, 25 940.0717 de variable y
3.87072351 de tarifa, las mismas cifras del motor, con **VAN = 0**.

Dos cosas que costaron cuadrar y que conviene no repetir:

- `MINIFS` no sobrevive el viaje entre escritores de xlsx. En su lugar hay una
  fila que marca el primer mes de operacion y un `SUMPRODUCT`, que dice lo mismo
  y abre en cualquier lector.
- La supervision SUNASS no es 1 % del PPD a secas: lleva el flag
  `'Concepto de Pago'!35`, que apaga el cobro cuando termina el contrato de O&M.
  Sin el flag sobra un trimestre y el VAN no cierra.
- Ademas de la deuda senior hay un **tramo complementario** en `M.Sombra!192:195`
  (IGV y capital de trabajo, 12 706.57 S/ miles desembolsados). Entra por ahora
  como primitiva del libro; falta modularlo.

Lineas que todavia entran como valores y no como formulas, marcadas
"(del motor)" en la hoja `Flujo`: costos de operacion, CAPEX, IGV, ITAN, el
tramo complementario de deuda y el bloque de impuestos. Se calculan cuando el
generador tome el CAPEX y el OPEX del usuario desde la plantilla de entrada.

## Plantilla de entrada para un proyecto nuevo (2026-09-15)

`plantilla.py` escribe **`Plantilla_Proyecto_Nuevo.xlsx`** y `leer_plantilla.py`
la lee. Cuatro hojas, todo a precios constantes, porque el reajuste lo pone el
motor:

- `Proyecto`: cronograma, esquema de pago, financiamiento, reajuste y tributos.
- `CAPEX`: malla mensual de inversion en S/ miles sin IGV.
- `OPEX`: las once lineas de costo y la demanda, por ano.
- `Otros`: seguros, fianzas, fideicomiso, promocion, garantias y reembolsos.

Viene precargada con Cajamarca para que se vea la forma esperada.

**Lo que ya esta probado del viaje de ida.** Leyendo la plantilla cargada con
Cajamarca, el lector reproduce contra el libro:

| Serie | Desvio |
|---|---|
| Produccion en kg DBO5 | 0.000000000 |
| PPDMO fijo base mensual | 0.000000000 |
| PPDMO fijo y variable trimestrales | 0.000000000 |
| Costo fijo, costo variable y gastos SPV | 0.01 S/ miles, que es la unidad de redondeo del libro |

Tres reglas del libro que hay que respetar y que no son obvias:

1. **Cada linea se busca por una clave distinta.** Los costos fijos y los gastos
   de la SPV van por **ano de concesion** (`'OPEX proyecto'!T$6`); los costos
   variables y la demanda van por **ano calendario**, porque siguen al caudal.
   Mezclarlas desvia el costo variable 0.73 %.
2. **El indice de costos no arranca en 1.** Al inicio de O&M ya trae el IPC
   acumulado desde la fecha de los precios constantes, 1.098628385697407 en
   Cajamarca (`Inputs!77`). Es un dato de la plantilla porque mezcla IPC
   observado y proyectado.
3. **El PPDMO fijo se calcula sin reposiciones.** `Costos!38` excluye la linea de
   reposiciones del promedio que alimenta `PPDMO!D21`.

**Falta del viaje de ida**: la cadena de construccion, es decir CAPEX de la
plantilla hacia el costo de obra con su propio indice y su IGV, que es lo que
alimenta el cierre del PPDI y el modulo de deuda; el bloque tributario; y el
escritor equivalente para San Martin.

## El viaje completo, de la plantilla a los pagos (2026-09-15)

`correr_desde_plantilla.py` lee `Plantilla_Proyecto_Nuevo.xlsx`, arma la cadena
de construccion, dimensiona la deuda, cierra el PPDI y cierra la tarifa variable
del PPDMO. Cargada con Cajamarca, **reproduce el libro aprobado en toda la
linea**:

| | Desde la plantilla | Libro | Desvio |
|---|---|---|---|
| PPDI anual | 46 472.546555 | 46 472.546555 | 0.00000004 |
| Tarifa variable | 4.317669 | 4.317669 | 0.00000000 |
| Cuota de deuda mensual | 2 692.275886 | 2 692.275886 | 0.00000000 |
| Interes total de la deuda | 178 771.878203 | 178 771.878203 | 0.00000000 |
| PPDMO fijo base mensual | 555.985681 | 555.985681 | 0.00000000 |
| PPDMO fijo trimestral | | | 0.00000000 |
| PPDMO variable trimestral | | | 0.00000001 |

Y con los parametros de hoy e IPM 2.67 % devuelve las mismas cifras que el motor:
PPDI 46 362.1457, tarifa 3.8707235, PPDMO fijo 6 679.9101 y variable 25 940.0717.

Cadena, con lo que valida cada eslabon:

1. `leer_plantilla.construccion` toma el CAPEX a precios constantes y le aplica el
   indice del CAPEX (`'CAPEX proyecto'!16`): da el costo de obra, 278 511.04,
   exacto, y la inversion a financiarse, 261 144.81, exacta.
2. `deuda_cajamarca.corrida` acepta esa inversion y los flags de la plantilla:
   cuota, intereses, servicio, estructuracion y comision, los cinco exactos.
   Ojo con la comision: la linea se abre el primer mes de obra (`Deuda!35`), no
   al arranque de la malla.
3. `leer_plantilla.series` arma costos y produccion, y la base del PPDMO fijo a
   precios constantes, sin el mes de IPM, que lo pone el modelo sombra porque
   depende del IPM que se corra.
4. `motor_cajamarca.cerrar(ext=...)` cierra el PPDI con esas series.
5. `sombra_cajamarca.cerrar` cierra la tarifa variable.

**Lo que todavia no sale de la plantilla**, y por eso un proyecto realmente
distinto aun no corre solo: el bloque tributario del modelo sombra (IR y
participacion con arrastre de perdidas), el flujo neto de IGV, el efecto ITAN y
el tramo complementario de deuda de `M.Sombra!192:195`. Los cuatro entran como
primitivas del libro de Cajamarca.

## Modelo sombra estructural, con impuestos calculados (2026-09-15)

`flujo_cajamarca.py` reemplaza el atajo del primer modelo sombra. En vez de
partir de los flujos en cache del libro y sumarles deltas a un tipo marginal,
**construye cada linea del flujo** y corre el bloque tributario entero
(`tributos_cajamarca.py`, replica de `EEFF Anuales` filas 82 a 98): deduccion
del ingreso financiero durante la construccion, adicion en cuotas de 1/15 desde
que se cobra el PPDI, y arrastre de perdidas.

Contra el libro: participacion 18 338.001922 e IR 102 784.500775, los dos
exactos; **flujo de caja trimestral con desvio 0.00000000**; VAN cero con la
tarifa del libro; y la tarifa cierra en 4.3176689715 contra 4.3176689715.

Con los parametros de hoy e IPM 2.67 % la tarifa pasa de 3.8707235 a
**3.8721535** y el PPDMO variable de 25 940.07 a **25 949.66 S/ miles**, 0.04 %
arriba. El numero estructural es el bueno.

**Dos cosas del libro que hay que respetar y que no se ven de fuera:**

1. **El estado de resultados devenga el PPDMO y la caja lo cobra un trimestre
   despues.** `EEPPGG!10` lee `PPDMO!23` (el pago del propio trimestre) y
   `M.Sombra!10` lee `PPDMO!34` (el del trimestre anterior). Usar la serie de
   caja para el impuesto desplaza toda la base imponible.
2. **`EEFF Anuales` agrega por el trimestre fiscal de EEPPGG**, que no coincide
   con la etiqueta de ano de `M.Sombra`. La clave correcta es el numero de
   trimestre, no la posicion en la malla.

**El CAPEX de caja y el flujo neto de IGV tampoco son primitivas**: el CAPEX de
`M.Sombra!24` es exactamente el costo del servicio de construccion que calcula
`motor_cajamarca` (292 995.02, desvio 0.000000) y el IGV de `M.Sombra!26` es el
que ya calcula el mismo motor con recuperacion anticipada (desvio 0.000000 en
los 107 trimestres). Los dos salen ahora del motor.

Quedan **dos** primitivas del libro, las dos de segundo orden y medidas:

| Primitiva | Suma | Valor presente al Ke |
|---|---|---|
| Efecto ITAN (`M.Sombra!23`) | 0.00 | -376.26 |
| Tramo complementario de deuda (`M.Sombra!192:195`), neto | | +305.38 |

El ITAN necesita el balance (es 0.4 % del activo neto, y se acredita contra el
IR, por eso suma cero y solo deja un efecto de calce). El tramo complementario
son tres facilidades identicas de cuota constante que financian el IGV y el
capital de trabajo (`M.Sombra!150:186`), atadas a la necesidad de IGV de
`M.Sombra!200`. Para un proyecto nuevo van en cero mientras no se modelen, y el
error que eso introduce es del orden de 70 S/ miles de valor presente, contra un
PPDMO variable que cierra en 25 950 al ano.

---

## Proyecto nuevo, de punta a punta (2026-09-15)

`generar.py` es el punto de entrada. Lee `Plantilla_Proyecto_Nuevo.xlsx`, deriva
el calendario, arma la cadena de construccion, dimensiona la deuda, cierra el
PPDI, cierra la tarifa variable con el modelo sombra estructural y escribe el
libro de salida con formulas vivas:

    python3 generar.py     ->  <Nombre del proyecto>_generado.xlsx

### El calendario ya no sale del libro

`calendario_caj.py` reconstruye **solo a partir de las fechas de la plantilla**
las doce series que antes se copiaban del JSON de Cajamarca: el flag de O&M, el
de cierre de trimestre, el de cobro, el trimestre de cada mes, el ano y el ano
fiscal de cada trimestre, los meses por trimestre, el flag de supervision, los
trimestres en que se carga el impuesto, el devengo del PPDI, el mes de carga del
IR y el ano de cada mes. `python3 calendario_caj.py` las contrasta una a una
contra el libro: **cero diferencias en once de las doce**.

La unica que no calza son dos meses del flag de carga del IR: el libro carga el
ejercicio 2051 en septiembre y no en diciembre. Es un ano sin base imponible (el
ultimo devengo de PPDI es 2045-09), y el PPDI cierra identico con una regla o la
otra, desvio 0.0000000000.

### La plantilla creció un bloque

La hoja `Otros` tenia solo las lineas del periodo de construccion, que alimentan
el activo financiero del PPDI. Ahora tiene un segundo bloque, **periodo de
operacion**, con seguros, fianzas, fideicomiso y gastos de promocion, que son
costos del flujo de caja financiero y no entran al PPDI. El libro los trata en dos
sitios distintos y la plantilla ahora tambien.

### Lo que da la cadena completa

Cargada con Cajamarca y con los parametros del libro, `generar.py` reproduce el
modelo aprobado sin tocar ninguna serie del libro salvo las dos primitivas
declaradas:

| | desvio contra el libro |
|---|---|
| PPDI anual | 0.00000004 |
| Tarifa variable | 0.00000036 |
| FCF trimestral, maximo | 0.024 S/ miles (redondeo de las lineas de costo) |

Poniendo en cero el efecto ITAN y el tramo complementario de deuda de
`M.Sombra!192:195`, que es como corre un proyecto nuevo, **la tarifa se mueve
0.028 %**. Esa es la medida exacta de lo que falta por modelar.

### Verificacion del libro de salida

Los dos libros se abrieron y se recalcularon de verdad con LibreOffice Calc en
headless, no se confio en que las formulas estuvieran bien escritas:

- `PTAR_Cajamarca_generado.xlsx`: PPDI 46 362.1457, PPDMO fijo 6 679.9101,
  variable 25 954.0327, tarifa 3.87280673, **VAN 2.7e-11**.
- `PTAR_San_Martin_generado.xlsx`: PPDI 96 490 727.19, cuota trimestral
  24 122 681.80, referencia mensual 5 479 810.06, PPDMO fijo anual
  47 594 308.15, precio unitario 3.647797, **VAN 2.2e-08**.

El recalculo del libro de San Martin delato un error real: el motor guarda el IR
y la participacion como importes positivos, igual que `EEFF Anuales`, y la fila
del flujo los estaba sumando en vez de restarlos. El VAN salia 81 940 536 en vez
de cero. De paso la hoja `Flujo` abrio en lineas separadas lo que antes era un
bulto: CAPEX, otros costos del periodo D+C+PM, variacion de IGV, cierre de la
laguna SJS y reposiciones; y `FC!23` quedo con su nombre real, "Pago por Obras",
que no es supervision.

### Lo que falta

- La rama **por hitos** de la plantilla. San Martin todavia corre desde las
  primitivas de su libro, no desde CAPEX y OPEX de la plantilla.
- El efecto ITAN, que necesita el balance, y el tramo complementario de deuda.

## La rama por hitos, primer tramo (2026-09-15)

`calendario_sm.py` hace para San Martin lo que `calendario_caj.py` hace para
Cajamarca: deriva de las fechas el flag del periodo [D + C + PM], el numero de
mes del contrato, los meses de pago del PPDI y el ano de cada mes. Las cuatro
series calzan **exacto** contra el libro (`python3 calendario_sm.py`).

Ojo con la numeracion: el libro cuenta los meses del contrato desde el primero
de obra y no desde el arranque de la malla (`Nec_Fin!nro_mes`), y tanto el mes
del cierre financiero como el calendario de aportes de capital se expresan en
esa numeracion, no en la de la malla.

La plantilla gano una hoja `Hitos` con el cronograma del contrato, el
financiamiento, el calendario de aportes, el capital de trabajo inicial y el
reparto del CAPEX por hito. `generar_sm.py` la lee y cierra el PPDI:

| | plantilla | libro | desvio |
|---|---|---|---|
| Necesidades totales | 698 107 786.8175 | 698 107 786.8175 | 0.000000 |
| Intereses de construccion | 66 454 727.9311 | 66 454 727.9311 | 0.000000 |
| Comisiones | 18 504 126.3965 | 18 504 126.3965 | 0.000000 |
| Deuda desembolsada | 558 486 229.4540 | 558 486 229.4540 | 0.000000 |
| VAN de las necesidades | 519 739 073.6514 | 519 739 073.6514 | 0.000000 |
| PPDI anual | 97 607 149.9419 | 97 607 149.9421 | -0.000160 |

**Falta el bloque anual del PPDMO** (`motor_ppdmo_sm`), que sigue escalando las
primitivas del libro: las lineas de costo de `FC`, los seis flujos de O&M de
`Ingresos!62:67` que reparten fijo y variable, y las filas tributarias de
`Impuestos`.

## La rama por hitos, completa (2026-09-15)

`generar_sm.py` cierra el PPDI **y** todo el PPDMO desde la plantilla, con el
flujo anual armado linea por linea en `flujo_sm.py`. Ya no reescala ninguna fila
del libro de San Martin. Las piezas nuevas, cada una contrastada contra el libro:

| pieza | que reconstruye | desvio |
|---|---|---|
| `calendario_sm.py` | flags del contrato, meses de pago, ano | 0 diferencias en 4 series |
| `ingresos_sm.py` | `Ingresos` 112-116, 131-135, 154-161 | 0.000001 |
| `opex_sm.py` | 14 lineas de costo, anuales y mensuales | 0.000000 |
| `tributos_sm.py` | `Impuestos` 61 y 70 | 0.000000 |
| `flujo_sm.py` | el flujo anual entero | VAN 0 |

Cargada con San Martin y con los parametros del libro, la cadena devuelve PPDI
97 607 149.9419 contra 97 607 149.9421, referencia del PPDMO 5 683 476.226929
contra 5 683 476.226942 y precio unitario 3.782649 exacto. El libro de salida
de esa corrida, `PTAR_San_Martin_plantilla.xlsx`, recalculado con LibreOffice,
devolvio esas cifras con **VAN −1.2e-07**. Ese libro **ya no esta en la
carpeta**: lo escribio una corrida suelta del 2026-09-15, ningun script lo
regenera y Oscar pidio borrarlo el 2026-09-18. La cadena se vuelve a verificar
con `correr_desde_plantilla.py`, que compara contra el libro sin escribir uno.

### Cinco reglas del libro que costaron encontrar

1. El libro cuenta los meses del contrato **desde el primero de obra**
   (`Nec_Fin!nro_mes`), y el mes del cierre financiero y el calendario de
   aportes estan en esa numeracion, no en la de la malla.
2. El reparto del PPDMO entre fijo y variable sale de los **VAN de los seis
   flujos de O&M**, primero entre sistemas y despues dentro de cada sistema.
   Depende del Ke.
3. **El precio unitario no es un dato**: es la parte variable de la referencia
   dividida por la carga organica **de referencia**, que es la de diseno y no la
   del primer ano. Usar la del primer ano mueve el precio un 27 %.
4. **El ultimo pago se descuenta** dos meses al Ke mensual, porque cae fuera de
   trimestre (`Ingresos!118:123`). Sin eso el cobro sale 57 249.66 de mas.
5. `FC!36`, la variacion del IGV de construccion, **suma casi cero en toda la
   obra pero se mueve millones ano a ano**. Omitirla desplaza el flujo y con el
   la deuda dimensionada por cobertura, y el PPDMO cierra 0.33 % abajo.

### El PPDMO de San Martin con parametros de hoy se movio

Con IPM 2.67 % el modelo estructural devuelve referencia **5 451 150.39** y
precio **3.628719**, contra 5 479 810.06 y 3.647797 del motor anterior, que
escalaba las filas del libro. Los dos reproducen el libro con los parametros del
libro; se separan 0.54 % solo al cambiar la proyeccion, porque el motor anterior
aplicaba el cociente de factores **anuales** a cifras anuales mientras que el
estructural indexa **mes a mes** cada linea a precios constantes, que es lo que
hacen las formulas del libro. La cifra buena es la del estructural.

Una corrida intermedia dio 5 450 081.82 y 3.611859; esa esta **retirada**. Salio
de pasarle el Ke del accionista donde el libro usa el WACC (`Ingresos!D80`), que
es la tasa con la que se reparte el PPDMO entre fijo y variable y con la que se
descuenta el ultimo pago. No lo caza la validacion contra el libro, porque ahi
las dos tasas entran por la misma variable.

## Los dos regimenes de la APP: activo financiero y activo intangible

La plantilla trae, en la hoja `Proyecto`, el campo **"Regimen de la APP"** con
dos valores. `generar.py` despacha por el.

### `cofinanciada` -> activo financiero (CINIIF 12 p.16)

El concedente se obliga a pagar importes determinables y el derecho de cobro es
incondicional, asi que la obra no es un intangible sino una cuenta por cobrar.
El libro de salida trae la hoja **`Activo financiero`**, con formulas vivas:
flag de devengo, flag de cobro, PPDI devengado, PPDI cobrado, devengado
pendiente, saldo inicial, servicio de construccion, ingreso financiero
devengado, amortizacion y saldo final.

El activo devenga al **tipo de interes efectivo**, que aqui es la TIR de sus
propios flujos (p.25, medicion al costo amortizado). La **amortizacion es el
cobro del mes menos el ingreso financiero devengado, SIN truncar en cero**: en
los meses sin cobro sale negativa porque el activo crece, y truncarla infla el
total amortizado. Es la misma definicion que usa el tablero, acordada con ese
hilo.

Con parametros de hoy e IPM 2.67 %, en S/ miles: tasa implicita mensual
0.008669496654 (10.914072 % anual), saldo maximo **354 452.24** en el mes 49,
amortizacion acumulada **292 995.02** —que es exactamente la suma del servicio
de construccion, el control de que el activo se recupera entero—, saldo final
1.9e-08 y **251 meses con amortizacion negativa**.

### `autofinanciada` -> activo intangible (CINIIF 12 p.17 y p.22)

Lo que recibe el concesionario es la licencia de cobrar al usuario, que depende
del uso, asi que va como intangible. Motor: `intangible_caj.py`. Punto de
entrada: `generar.correr_auto`. Escritor: `escribir_excel.escribir_auto`.

Cambia esto y nada mas:

1. **No hay PPDI ni PPDMO.** La incognita del cierre pasa a ser la **tarifa al
   usuario**, un precio por kg DBO5 reajustado por IPM con el mismo gatillo.
2. **No hay activo financiero**, ni tasa implicita, ni deduccion del ingreso
   financiero durante la construccion, ni adicion en cuotas de 1/15. Esas tres
   reglas son del p.16 y no aplican.
3. El intangible se reconoce **al termino de obra** por la inversion mas los
   **intereses de la deuda capitalizados** (p.22, que solo rige en este
   regimen), y se amortiza **linealmente durante la operacion**. La amortizacion
   es gasto deducible y **no es caja**: entra al estado de resultados, no al
   flujo. La hoja `Flujo` la muestra dentro del bloque de utilidad y fuera del
   flujo de caja, para que se vea.
4. El interes posterior al inicio de operacion si es gasto del periodo.
5. El usuario paga IGV sobre la tarifa, asi que el credito fiscal de la
   construccion se recupera contra ese debito y no contra el PPDI.

Lo que no cambia, porque no depende del regimen: calendario, CAPEX, OPEX y su
indexacion, dimensionamiento de la deuda, supervision del regulador y arrastre
de perdidas.

Libro de salida `PTAR_Cajamarca_autofinanciada.xlsx`, con las mismas cifras de
hoy: tarifa al usuario **9.4608605** S/ por kg DBO5, intangible al termino de
obra **324 200.32** S/ miles (inversion 292 995.02 mas intereses capitalizados
31 205.30), amortizacion lineal **1 228.03** al mes por 264 meses, ingreso
tarifario del primer mes anualizado **63 402.98**. Recalculado con LibreOffice
da **VAN -4.6e-12**, y sus lineas calzan con el motor con desvio 0.00000000.

**Las reposiciones siguen como costo de caja, no como provision del p.21 /
NIC 37.** Lo decidio Oscar el 2026-09-15 ("no lo provisiones"), y vale para las
dos ramas.

## El RCSD como input, y el agujero que destapo

La hoja `Proyecto` de la plantilla trae ahora **"Cobertura minima RCSD"** (1.25)
y **"Cuenta de reserva CRSD"** (0.5), junto al resto del financiamiento. Antes
vivian en la hoja `Hitos`; se subieron para que haya un solo sitio donde
mirarlos. `generar_sm._param` los busca primero en `Proyecto` y cae a `Hitos`
solo por compatibilidad con plantillas viejas. **Solo muerden si "Servicio de la
deuda" es "por cobertura"**: Cajamarca es cuota constante y la cobertura no entra
en ninguna de sus formulas.

Al exponerlo aparecio un error que llevaba tiempo dormido. El dimensionamiento
por cobertura amortiza `min(saldo, max(0, flujo/RCSD - intereses))`. Con
coberturas altas ese termino da cero, y el saldo sobrevivia hasta el fin de la
concesion **pagando intereses sin devolver nunca el principal**, lo que abarataba
el PPDMO. A RCSD 1.25 no se nota, porque el libro ya repaga entero en 2042
(`Deuda Anual!40`) antes del ultimo PPDI: **validar contra el libro no lo
delata**.

Cerrado cancelando el saldo al vencimiento, que por defecto es el ultimo ano con
pago del PPDI y se puede forzar con `ent["ven"]`. Corregido en los dos motores,
`flujo_sm.py` y `motor_ppdmo_sm.py`, para que no se separen.

Sensibilidad medida en San Martin con los parametros del libro, ya corregida:

```
RCSD    referencia mensual   precio unitario   ultimo repago
1.00        6,177,821.41        4.111662           2038
1.25        5,683,476.23        3.782649           2042   <- el libro
1.50        5,215,461.89        3.471161           2044
2.00+       4,912,411.78        3.269466           2044 (bullet al vencimiento)
```

El pago **baja** al subir la cobertura: amortizar mas lento deja la caja mas
tiempo en el proyecto y el capital propio es mas caro que la deuda. Satura en 2.0
porque desde ahi no amortiza nada ano a ano.

Control: los cinco escenarios de `exportar_sm_estructural.py` salen con desvio
**0.0** contra la corrida previa al cambio.

Los dos libros de San Martin se regeneraron desde el motor **estructural**, no
desde el de reescalado: `PTAR_San_Martin_generado.xlsx` trae ahora referencia
5 451 150.39 y precio 3.628719, y el libro desde plantilla reprodujo el libro
con 5 683 476.226929 y 3.782649. Los dos recalculados con LibreOffice dieron
VAN cero; el segundo ya no esta en la carpeta, ver mas arriba.

## El modo de amortizacion lo fija el esquema de pago

Acordado con el hilo del tablero el 2026-09-15, y ya escrito en la plantilla:
**el usuario no elige como amortiza la deuda**. El pago al final de obra va con
**cuota constante** y sin cobertura, como Cajamarca; el pago por hitos va
**dimensionado por cobertura** con RCSD, como San Martin. La celda "Servicio de
la deuda" de la hoja `Proyecto` dice "lo fija el esquema de pago" y los motores
no la leen; el RCSD y la CRSD llevan la nota "SOLO en la rama por hitos".

El plazo de la deuda de la rama al final de obra son dos fechas de la plantilla,
"Inicio del pago de deuda" y "Fin del pago de deuda" (144 cuotas mensuales en
Cajamarca, 2030-10 a 2042-09), y **no cuelga del PPDI**, que corre hasta 2045-09.
Vale igual en cofinanciada y en autofinanciada: la rama del intangible usa
exactamente la misma deuda, y por eso no necesita un PPDI que ya no existe.

### Una trampa del flag de operacion

`flag_om` vale cero **antes** de la operacion y tambien **despues** de que acaba
la concesion, porque la malla dura mas que el contrato. Capitalizar intereses
por "no esta en operacion" mete la cola de la malla dentro del intangible. Se
capitaliza solo lo anterior al primer mes de operacion, y la hoja
`Activo intangible` lleva una fila propia, "Flag anterior a la operacion", en vez
de `1 - flag_om`. En Cajamarca no muerde porque la deuda ya esta pagada en 2042 y
esos meses valen cero, pero en un proyecto con deuda viva al final si lo haria.

El interes capitalizado de Cajamarca autofinanciada, por ano: 2028 1 809.05,
2029 12 848.35, 2030 16 547.89, total **31 205.30** S/ miles. La serie mensual
esta en `autofinanciada_interes_capitalizado.json`.

## Las cuatro combinaciones del generador

`matriz.py` corre las cuatro en una pasada y escribe los cuatro libros. Si una
deja de cerrar, se ve ahi.

```
regimen \ esquema      al final de obra          por hitos
cofinanciada           generar.correr            generar_sm.correr
autofinanciada         generar.correr_auto       generar_sm.correr(regimen=...)
```

Control con parametros de hoy e IPM 2.67 %:

```
cofinanciada    al final de obra   VAN  0.00000000   PPDI 46,362.15 / tarifa 3.8728067
autofinanciada  al final de obra   VAN  0.00000000   tarifa 9.4608605 / intangible 324,200.32
cofinanciada    por hitos          VAN -0.00000004   PPDI 96,490,727.19 / ref 5,451,150.39
autofinanciada  por hitos          VAN  0.00000001   tarifa 31.109308 / intangible 653,800,042.23
```

(Las dos primeras en S/ miles, las dos de San Martin en soles.)

### Que significa "por hitos" cuando no hay PPDI

En el modelo aprobado de San Martin **los cuatro hitos no escalonan el inicio de
la operacion**: las cuatro patas fijas del PPDMO arrancan el mismo mes, todas
multiplicadas por la misma bandera de operacion (`Ingresos!112:116`). Los hitos
reparten el PPDI y la pata fija en cuatro montos; no adelantan ingresos.

Por eso, sin PPDI, de "por hitos" queda lo que de verdad lo distingue: el perfil
de inversion por hito, los aportes de capital en sus meses, las comisiones y la
**deuda dimensionada por cobertura con cuenta de reserva**, en vez de la cuota
constante. Sobre eso van el intangible y la tarifa al usuario. Si en algun
contrato cada hito empieza a cobrar al ponerse en marcha, hay que escalonar
`flag_op` por hito; hoy no es lo que hace el modelo aprobado.

### La regla que evita contar los intereses dos veces

En la rama autofinanciada por hitos la amortizacion lineal del intangible
**reemplaza** a la depreciacion del CAPEX (`Impuestos!61`) y a la amortizacion en
diez anos de los gastos financieros de construccion (`Impuestos!70`). Los
intereses de obra ya estan dentro del activo por el parrafo 22, asi que
deducirlos tambien por la via de `Impuestos!70` seria contarlos dos veces. En el
motor eso es `gf_am = 0` y `amort_capex` = amortizacion del intangible, y solo
ocurre cuando `ent["regimen"]` es autofinanciada; la rama cofinanciada no se
toca, y los cinco escenarios de San Martin siguen con desvio **0.0**.

## Un tercer proyecto, inventado, como control de generalidad (2026-09-15)

`proyecto_ficticio.py` arma `Plantilla_PTAR_Ficticia.xlsx`: una PTAR que no
existe, con otro cronograma (cierre en 2027-01, obra de 35 meses con perfil de
campana, operacion 2031-04 a 2051-03), otro apalancamiento (70 %), otro spread
(4.00 %), otras comisiones, 48 cuotas de PPDI y una malla de 312 meses contra
los 318 de Cajamarca. Ninguna cifra sale de los dos libros aprobados.

Sirve porque **validar contra Cajamarca y San Martin no demuestra que el
generador sea general**: los motores nacieron de esos dos libros y pueden traer
supuestos suyos pegados. Con el proyecto inventado salieron tres, dos de ellos
en cifras que Oscar habria usado.

**1. La hoja `Deuda` estaba en referencia circular.** La celda de la cuota
constante hacia `PMT(tasa, cuotas, saldo del mes base)` y el saldo de ese mes
dependia, por la cadena servicio -> amortizacion -> saldo, de la propia cuota.
Excel y Calc devuelven error y la hoja entera quedaba en `#VALUE!`: 1 272
celdas en el libro de Cajamarca, 1 248 en el inventado. **Estaba en los libros
entregados y no se habia visto**, porque el VAN del `Resumen` no cuelga de esa
hoja y solo se habia comprobado el VAN. Corregido con una fila propia, "Saldo de
obra capitalizado (base de la cuota)", que acumula `saldo x (1 + tasa) +
desembolso` hasta el mes base y no referencia la cuota. Es identica al saldo de
abajo, porque mientras no hay servicio la amortizacion es el interes con el
signo cambiado. De paso, `_fila` convierte a numero cualquier constante escrita
como texto: una celda con `"0"` sin el `=` delante bastaba para propagar
`#VALUE!` por toda la fila.

**2. El reajuste por IPM corria sobre el calendario de Cajamarca.**
`ipm_cajamarca.factores` acumulaba el IPM contra `FLAG`, la bandera de operacion
que trae el JSON del libro, en vez de la del proyecto que se esta corriendo. El
gatillo del 3 % se disparaba en el mes equivocado: en el proyecto inventado, tres
meses antes. Ahora `factores(ipm, flag)` recibe la bandera; `sombra_cajamarca` le
pasa `FLAG_OM` (la que ya reemplaza `usar_calendario`) e `intangible_caj` le pasa
`cal["flag_om"]`. Movio la tarifa del proyecto inventado **+1.1 %** en
cofinanciada y **+0.63 %** en autofinanciada. En los dos libros aprobados no
mueve nada, porque ahi la bandera derivada de las fechas coincide con la del
libro: los cuatro controles siguen dando las mismas cifras.

**3. Las tasas de tributos eran decorativas.** La plantilla pide IGV, Impuesto a
la Renta, participacion de trabajadores y supervision del regulador, y los
motores usaban las del libro (18 %, 29.5 %, 5 %, 1 %) pasara lo que pasara.
Cambiar las cuatro en la plantilla no movia el PPDI ni una decima. Ahora
`generar._tributos` las reparte a `motor_cajamarca`, `tributos_cajamarca` y
`sombra_cajamarca` al arrancar cada corrida. Prueba: con IR 24 %, IGV 16 % y
participacion 10 %, el PPDI del proyecto inventado pasa de 36 313.30 a
35 881.86 y la tarifa de 2.0930181 a 2.1388389.

**Prueba de que ya no queda nada del libro pegado.** Envenenando en memoria las
series de `cajamarca_primitivos.json` y `caj_sombra_full.json` que los motores
cargan al importarse (costo de obra, fideicomiso, seguros, garantias, reembolso,
estructuracion, comision, gastos financieros, kg, base del fijo), el proyecto
inventado da exactamente el mismo PPDI y la misma tarifa.

Control con parametros de hoy e IPM 2.67 %:

```
cofinanciada    VAN  0.0   PPDI 36 313.30 / tarifa  2.0930181
autofinanciada  VAN -0.0   tarifa 11.5352929 / intangible 232 303.14
```

Los seis libros de salida (los cuatro aprobados y los dos del proyecto
inventado) recalculados con LibreOffice Calc: **sin una sola celda de error** y
VAN entre -3.1e-07 y 2.7e-11.

## La rama por hitos, ahora si desde la plantilla (2026-09-15)

El control del proyecto inventado destapo un hueco mas grande que los tres
errores: **la rama por hitos nunca leyo el CAPEX de la plantilla**. `generar_sm`
recibia `capex`, `otros` e `igv` por parametro y el unico que la llamaba,
`matriz._sm`, los sacaba de los JSON del libro de San Martin. Un proyecto nuevo
pagado por hitos no se podia correr solo con la plantilla, que es justamente lo
que pide el proyecto.

Cerrado con dos piezas nuevas en `generar_sm.py`:

**`construccion_plantilla(d, cal, anio0)`** arma las mallas mensuales de la hoja
`CAPEX` y del bloque de construccion de `Otros`, a precios corrientes con el
indice de CAPEX, y las coloca sobre la malla de `Hitos`. Si algun mes con gasto
cae fuera de esa malla, aborta con el rango en el mensaje en vez de perderlo en
silencio.

**El IGV de construccion va en cero, con evidencia, no por comodidad.** En el
libro de San Martin la necesidad neta de IGV suma 183 377 soles sobre 555
millones de CAPEX (el 0.03 %, unos 518 soles al mes contra 2.9 millones de CAPEX
mensual) y la variacion anual del IGV en el flujo suma exactamente cero. O sea
que el modelo aprobado ya asume recuperacion practicamente contemporanea, el
regimen especial de recuperacion anticipada. Un proyecto con otro regimen tiene
que traer su propia serie por `igv` e `igv_flujo`.

**`correr_plantilla(ruta, ...)`** resuelve ademas la cuenta de reserva, que
hasta hoy tambien salia del libro (30 191 724.16 en San Martin). Es un punto
fijo aparte del de las necesidades: la reserva se dota con `CRSD x servicio de
deuda del primer ano de operacion`, ese servicio depende de la deuda y la deuda
depende de la reserva porque la reserva se financia. Se itera la cadena entera y
converge en pocas vueltas, porque la reserva es un par de puntos del total. En
el proyecto inventado da 6 272.92 S/ miles sobre necesidades de 236 767.42.

**Una trampa de unidades que se veia mal.** La rama por hitos calcula el precio
unitario en la moneda del modelo por kg, sin dividir entre mil como hace la de
"al final de obra". Con el proyecto inventado escrito en S/ miles, el `Resumen`
mostraba 0.0119 y eso son 11.9 soles por kg. La etiqueta ahora lleva la unidad,
tomada de la celda "Moneda" de la plantilla. En los libros de San Martin sigue
diciendo "S/", porque ahi el modelo esta en soles y porque la plantilla
precargada mezcla unidades a proposito (Cajamarca en `Proyecto`, San Martin en
`Hitos`), asi que su "Moneda" solo describe el libro cuando la plantilla es de
un proyecto de verdad.

`proyecto_ficticio.control()` corre ahora **las cuatro combinaciones** sobre el
proyecto inventado, igual que `matriz.py` sobre los dos aprobados:

```
cofinanciada    al final de obra   VAN  0.0   PPDI 36 313.30 / tarifa 2.0930181
autofinanciada  al final de obra   VAN -0.0   tarifa 11.5352929 / intangible 232 303.14
cofinanciada    por hitos          VAN -0.0   PPDI 32 104.87 / referencia 1 528.0081
autofinanciada  por hitos          VAN -0.0   tarifa 0.0119452 / intangible 229 294.50
```

Los cuatro libros recalculados con LibreOffice: sin una celda de error, VAN
entre -3.3e-11 y 8.3e-09.

### Lo que queda abierto en la plantilla

**`OPEX` y `OPEX hitos` son dos hojas independientes y nadie comprueba que
digan lo mismo.** La primera pide los costos por ano de concesion en once
lineas; la segunda los pide por ano calendario repartidos por hito y con sus
versiones con IGV. Un usuario que quiera comparar su proyecto bajo los dos
esquemas de pago tiene que escribirlo dos veces, en dos formas distintas, y si
se equivoca en una las dos corridas no son del mismo proyecto. Se puede derivar
`OPEX hitos` de `OPEX` mas el reparto por hito; no esta hecho.

**El control del proyecto inventado no comprueba nada entre esquemas**, por lo
mismo: sus dos bloques de OPEX no son el mismo proyecto. Cada combinacion cierra
en cero por separado, que es lo que el control busca.

## El OPEX se escribe una sola vez (Oscar, 2026-09-15)

Regla de Oscar, textual: **"El opex por año de concesión debe ser igual a la
suma del opex por hito de ese año"**. Antes la plantilla lo pedía dos veces, en
`OPEX` por año de concesión y en `OPEX hitos` repartido por hito, y nada
comprobaba que dijeran lo mismo.

`opex_consistente.py` trae las dos mitades:

- **`derivar(ruta)`** reescribe `OPEX hitos` desde `OPEX` y el reparto por hito,
  con lo que la igualdad se cumple por construcción y el usuario escribe el OPEX
  una sola vez. Deriva las cuatro patas fijas, sus versiones con IGV —
  conservando la proporción que la hoja ya tuviera escrita, o `1 + IGV` si no
  tenía ninguna—, el costo variable y las reposiciones.
- **`validar(ruta)`** comprueba la igualdad año por año en una plantilla escrita
  a mano y devuelve los desvíos. Detecta también los años que `OPEX hitos`
  cubre y `OPEX` no: ahí lo único admisible es cero.
- **`generar_sm.correr_plantilla` aborta** si las dos hojas no coinciden, con el
  año y el importe del mayor desvío en el mensaje. Se salta con
  `verificar_opex=False` si el desvío es intencional.

**El reparto del O&M por hito es un campo nuevo de la hoja `Hitos`**, no los
porcentajes de CAPEX, porque no son lo mismo. Medido en el libro de San Martín,
año 2031:

```
             O&M        CAPEX
Hito 1    67.4423 %   75.9649 %
Hito 2     4.4200 %    6.2513 %
Hito 3     1.4198 %    2.2825 %
Hito 4    26.7179 %   15.5012 %
```

El hito 4 pesa 26.7 % del O&M y solo 15.5 % de la inversión. En el libro el
reparto se mueve menos de un punto en toda la concesión (67.44 a 67.95 en el
hito 1), así que un reparto constante es una entrada razonable; los cuatro
campos vienen precargados con esos valores.

**Lo que la regla no cubre**, y por qué: `gg_u` (gastos generales y utilidad),
`otros_op` (otros costos de la concesión) e `igv_op` no tienen contrapartida en
la hoja `OPEX`, así que siguen siendo insumos propios de la rama por hitos.

**Unidades.** `OPEX` se escribe en soles y `OPEX hitos` en la moneda del modelo.
El factor sale de la celda "Moneda" de `Proyecto`: con "S/ miles" es mil.

**La plantilla precargada NO cumple la regla, a propósito.** Trae Cajamarca en
`OPEX` y San Martín en `OPEX hitos`, que son dos proyectos distintos y en
unidades distintas; el validador reporta 71 desvíos. Es el ejemplo de las dos
formas, no un proyecto. La cabecera de la hoja ahora lo dice.

**Un resultado que confirma algo ya sabido:** cambiar el reparto por hito de
[45, 20, 20, 15] a [67.4, 4.4, 1.4, 26.7] en el proyecto inventado **no movió
ninguna cifra del cierre** (PPDI 32 104.87 y referencia 1 528.0081 idénticos).
Es lo esperado: los cuatro hitos arrancan la operación el mismo mes, así que el
reparto parte el pago pero no cambia su total ni su calendario. Lo que sí
cambiaría es escalonar `flag_op` por hito, que sigue abierto con Oscar.

Los ocho libros (cuatro de los proyectos aprobados y cuatro del inventado)
recalculados con LibreOffice después del cambio: sin una celda de error, VAN
entre -3.1e-07 y 8.3e-09.

## El mismo error de indexacion, otra vez, en la rama por hitos (2026-09-16)

`ipm_sm.factores` tenia la ventana de reajuste **codificada con las fechas de
San Martin**: `INI = 2025-11`, `FIN = 2049-10`, `N0 = 2025-01`, `NM = 336`, y de
ahi un `FLAG` posicional. Es exactamente el mismo error que ya se habia
corregido en `ipm_cajamarca` el dia anterior, en la otra rama, y se paso por
alto al arreglar aquella.

Aplicado al proyecto inventado, cuya malla arranca en 2027-01, el `FLAG` del
libro caia en el sitio equivocado:

```
ventana que corresponde   2027-02 .. 2051-03   (290 meses)
ventana que se aplicaba   2027-11 .. 2051-10   (288 meses)
```

Nueve meses tarde al arrancar y siete meses despues del fin de la concesion al
terminar. El desvio maximo del factor es 0.83348, en 2051-04: ahi el indice
correcto vuelve a 1 porque la concesion ya acabo y el equivocado seguia en
1.83348.

Ahora es `factores(ipm_anual, flag=None)` y la ventana la arma
`calendario_sm.ventana_reajuste(cal)`, que es la union de `flag_dcpm` y
`flag_op`. **Ojo que arranca en el inicio de la obra, no en el de la
operacion**: es lo que hace `Hip_Mensual` y por eso difiere de Cajamarca, que
acumula desde el inicio de O&M. Derivada de las fechas del libro da **cero
diferencias** contra el `FLAG` codificado, y San Martin sigue reproduciendose
(referencia 5 683 476.2269 y precio 3.782649 con los parametros del libro).

**Lo que movio en el proyecto inventado:**

```
                            antes          despues
cofinanciada  referencia   1 528.0081     1 515.6395    -0.81 %
autofinanciada  tarifa     0.0119452      0.0117794     -1.39 %
PPDI (las dos)             32 104.87      32 104.87      igual
```

El PPDI no se mueve porque cierra contra las necesidades de financiamiento, que
no llevan el indice.

**Y la leccion, que ya estaba escrita y no se aplico:** el control del proyecto
inventado corrio la rama por hitos y cerro en VAN cero con la indexacion mal.
Cerrar en cero no valida la indexacion, y arreglar un motor no arregla su
gemelo. Cuando aparezca un error de esta familia, buscarlo en las dos ramas el
mismo dia.

## Donde esta el costo del financiamiento de la obra en el cierre del PPDI (2026-09-16)

El flujo que cierra el PPDI de Cajamarca (`PPDI!168 = SUM(D149:D159)`, descontado
al WACC en `PPDI!D378 = NPV(D379, D168:LC168)`) **no tiene fila de gastos
financieros**, y eso desconcierta a quien lo lee por primera vez: si el PPDI no
devuelve el interes del periodo de obra, parece que el nivel deberia ser mas
bajo. No es asi, y conviene dejarlo escrito porque el generador reproduce la
misma estructura.

La fila que se sospecha que lo lleva es la 150, y no lo lleva:

```
PPDI!150 "Avances de Inversion" = -D56
PPDI!56  "Costo de Obra"        = SUM(D41:D43)*IF(D$52>Inputs!$G$122,0,1)
PPDI!41  "Total Avance Inversiones" = SUM(D30:D40)
         filas 31..39 -> 'CAPEX proyecto'!D19:D24, D26, D28:D31, D33, D35, D36
PPDI!42  Expediente Tecnico     -> 'CAPEX proyecto'!D32
PPDI!43  Supervision            -> 'CAPEX proyecto'!D34
'CAPEX proyecto'!D19..D36       = CronogramaCAPEX!K...*D$16*bandera
```

`D$16` es el indice de ajuste de precios y `CronogramaCAPEX` el cronograma
fisico: CAPEX a precios corrientes y nada mas, sin una sola referencia a `Deuda`
ni a `Nec_Fin`. La fila 150 suma -278,511.04, que es exactamente la 56. Del
flujo, solo la 151 (`-D61 = Deuda!F46`, estructuracion) y la 152
(`-D62 = Deuda!F45`, comision) tocan la hoja de deuda, y son comisiones. El
interes entra una sola vez, en `PPDI!83 = Deuda!F38`, dentro del estado de
resultados que produce el IR de la fila 158.

**El costo del financiamiento esta en la TASA.** Los egresos de obra caen 48
meses antes de los cobros, asi que cerrar en VAN cero al WACC obliga al PPDI a
devolverlos mas el costo de capital del diferimiento. Medido en el libro,
S/ miles:

```
servicio de construccion, nominal                     292,995.02
capitalizado al ultimo mes de obra al WACC mensual    341,412.71   +16.53 %
   D379 = 0.0076709526 mensual = Tasa!E22 = 9.603614 % anual
interes capitalizado del motor (80 % deuda al Kd)      31,205.30   +10.65 %
```

El uplift del descuento es **mayor** que el interes capitalizado, y tiene que
serlo: el interes capitalizado remunera solo el 80 % de deuda al Kd sobre la
fraccion del plazo en que esta desembolsada (0.3592 en Cajamarca), mientras que
el WACC remunera el 100 % del capital durante todo el diferimiento.

Las dos formulaciones son equivalentes **si cada una capitaliza una sola vez**:
anualizar una base reconocida al fin de obra con el interes adentro, o descontar
los egresos en su mes. Lo que si es doble conteo es hacer las dos cosas. Por eso
`motor_cajamarca.corrida` arma `_sc = _obra + fid + seg + gar + reem + estr + com`
sin termino de interes y `fc = cobro - _sc - ir + igv_neto`: el interes solo
aparece en el activo intangible de la rama autofinanciada (CINIIF 12 p.22), que
es reconocimiento contable, no una linea del flujo.

Salvedad al comparar niveles: el flujo que cierra no es solo construccion.
`PPDI!167 = -SUM(D150:D159)` suma 359,464.80 nominales e incluye fideicomiso,
seguros, garantias, reembolso, Impuesto a la Renta y flujo de IGV, con IR
corriendo toda la operacion.

## El reparto del PPDMO salia del libro, no del proyecto (2026-09-16)

Octava falla que destapa el proyecto inventado, y la mas grande de las que no
mueven el VAN. **El cierre siempre fue correcto; lo que estaba mal era el
reparto de ese cierre.**

En la rama por hitos, el Solver mueve una sola incognita, la referencia mensual,
y el libro la reparte despues entre las cuatro patas fijas y el precio unitario
variable con los VAN de los seis flujos de O&M (`Ingresos!71:76`, de ahi
`D83`, `D84`, `D87`, `D88`). Ese reparto se calculaba con
`motor_ppdmo_sm.repartos`, que lee `INGM = sanmartin_anual.json["ing_m"]`: **las
series del libro de San Martin**. O sea que cualquier proyecto nuevo cobraba con
el perfil fijo/variable y por hito de San Martin, fuera cual fuera su propio
OPEX. Peor: `opex_sm.series` ya calculaba las seis series mensuales del proyecto
y `preparar` se quedaba solo con `["anual"]`, tirando la mitad que hacia falta.

**Por que no lo vio nada.** El total cierra en VAN cero con cualquier reparto:
el reparto parte el pago, no lo cambia. Es la misma leccion que la ventana de
indexacion, en otra forma: *cerrar en cero no valida la composicion del cierre*.

Prueba: envenenando `Q.INGM` en memoria (duplicando las dos filas variables del
libro) el proyecto inventado movio su precio unitario **+54.5 %** y sus patas
fijas **-22.7 %**, con la referencia moviendose solo -1.4 %.

Corregido con `ingresos_sm.repartos(mensual, tasa_anual)`, que hace la misma
cuenta sobre las series `conigv_*` del proyecto. `motor_ppdmo_sm.repartos` se
queda como esta: es la ruta que reproduce el libro y tiene que seguir leyendo
las series del libro.

Lo que movio, con IPM 2.67 %:

```
libro de San Martin (correr_final.py)   sin cambio
    referencia 5,683,476.2269   precio 3.782649   PPDI 96,490,727.1881
San Martin desde la plantilla (matriz)  referencia 5,451,150.39 -> 5,452,029.7992  (+0.016 %)
proyecto inventado                      referencia 1,515.6395  ->  1,500.3721      (-1.007 %)
    precio unitario   0.00157432 -> 0.00219079   (+39.16 %)
    fijo hito 1  742.04 ->   412.93   (-44.35 %)
    fijo hito 2   49.66 ->   183.52  (+269.55 %)
    fijo hito 3   15.62 ->   183.52 (+1074.58 %)
    fijo hito 4  289.54 ->   137.64   (-52.46 %)
    reparto e[]  [0.919133, 0.061514, 0.019353] -> [0.529412, 0.235294, 0.235294]
```

El proyecto inventado reparte su O&M casi parejo entre los tres hitos del
sistema 1 y San Martin lo concentra al 92 % en el primero, asi que el cambio es
enorme en la composicion y casi nulo en el total. **Eso es exactamente lo que
Oscar pide cuando dice "la misma informacion que los Excel tanto a nivel de
resumen como de flujos": el resumen ya estaba bien, los flujos no.**

El residuo contra el libro (0.098 puntos en `kvar`, +0.016 % en la referencia)
no es un error: la plantilla trae el O&M a precios constantes por ano
calendario, plano dentro del ano, y se le aplica un IPM constante de 2.67 %,
mientras el libro trae su propio perfil mensual y su propia proyeccion de
indices. Como las seis series no son proporcionales en el tiempo, el indice no
se cancela del todo en el cociente.

Dos detalles del libro que el reparto obliga a respetar, y que estan en el
docstring de `ingresos_sm.repartos`:

  * **La tasa es el WACC, y la celda engana.** `Ingresos!D79 = D50 = Ke!C25`,
    que se llama "Costo Promedio Ponderado Capital, SOL" = 9.951300 %; el Ke de
    verdad es `Ke!C23` = 11.896982 %. Usar el Ke mueve la participacion variable
    de 27.616432 % a 27.502891 %, 0.11 puntos.
  * **Los pesos van CON IGV y el IGV no es 18 % sobre todo.**
    `Ingresos!62 = Opex!P19 + Opex!P127`, y `Opex!127 = P62*$D$125*$C127` con un
    coeficiente propio por linea: 0.411 en los fijos 1 a 3, 0.4298 en el 4,
    0.283 en el variable del sistema 1 y 0.1771 en el del 2. Las patas variables
    llevan bastante menos IGV que las fijas, asi que repartir sin IGV corre la
    participacion variable de 27.616432 % a 28.120331 %, medio punto.

Los ocho libros vuelven a recalcular en LibreOffice sin una sola celda de error
y con VAN entre -3.1e-07 y 8.1e-09. `proyecto_ficticio.libros()` escribe ahora
los cuatro del proyecto inventado, que antes se armaban a mano: el control no
sirve si solo cierra en memoria y nadie abre el Excel, que es donde aparecieron
la referencia circular de `Deuda` y la trampa de unidades del `Resumen`.

## `OPEX proyecto` tiene dos mallas, y confundirlas triplica el ano (2026-09-16)

Trampa del libro de Cajamarca que costo dos correcciones publicas el mismo dia,
anotada porque no se ve mirando la hoja por encima:

```
filas  19 a  41   MENSUALES     fila 8 = fecha, fila 9 = numero de mes
filas 127 a 200   TRIMESTRALES  fila 129 = "Trimestre", lee 1, 2, 3, 4...
                                exactamente columnas D..DE = 106 = 318/3
```

La fila 179 se llama literalmente "Costo fianza trimestral", y `PPDI!58` lee el
bloque con `HLOOKUP(D$53,'OPEX proyecto'!$D$129:$DE$169,34,FALSE)/3`, donde
`D$53` es el trimestre y el `/3` es lo que lo pasa a mensual. Sumar una fila del
bloque trimestral sobre doce columnas del bloque mensual toma **doce trimestres
en vez de cuatro** y da el triple del ano. Hay ademas una "x" suelta en la
columna LK que hace que `max_column` mienta sobre el ancho real.

**La lectura segura es `EEPPGG`**, que es trimestral, lee
`'OPEX proyecto'!D169` uno a uno y trae su propio ano calendario en la fila 5.
Agregado asi, el O&M del primer ano de operacion (oct-2030 a set-2031, precios
constantes de dic-2025, S/ miles) es **26,401.00**:

```
fijos                    7,930.33   incluye reposiciones 2,134.45
variables               15,109.53   = 14,984.55 x 3/12 + 15,151.19 x 9/12
gastos SPV               1,782.00
seguros                    712.82   178.2048 por trimestre x 4
fianzas                    766.32   191.5790 por trimestre x 4
fideicomiso                100.00    25.0000 por trimestre x 4
```

La ventana de octubre a setiembre es la razon por la que ninguna cifra anual del
libro por ano calendario o por ano de concesion iba a coincidir nunca.

**La serie anual completa quedo en `cajamarca_om_anual.json`**, 25 anos con
fijos, reposiciones, variables, SPV, seguros, fianzas, fideicomiso y supervision,
para que nadie la reconstruya a mano otra vez. El O&M va de 26,442.66 en 2031 a
29,412.95 en 2051, un crecimiento equivalente de 0.5337 % anual: solo se mueven
los variables, que siguen a la demanda, mientras los fijos y la SPV son planos
porque `Parametros!C72` y `C73` estan en cero. Las fianzas bajan por escalones
(766.32, 627.06, 209.29 desde 2033).

Dos cosas que la plantilla ya tenia bien y que este ejercicio confirmo: su hoja
`OPEX` toma las lineas de `Costos` por ano tal cual, y su bloque `Otros` de
operacion trae 712.82, 766.32 y 100.00 al ano. Y la supervision de la SUNASS no
es una serie sino una tasa, "Supervision del regulador" = 1 % en `Proyecto`, que
`sombra_cajamarca` aplica **dentro** del bucle de cierre como
`-SUPERV*(d_ppdi + d_fijo + d_var)`: tiene que ser asi, porque es un porcentaje
del pago y el pago es la incognita.

### El IGV de operacion vale cero en el flujo, pero no por regla

Medido el 2026-09-16 al descartar candidatos para el hilo del tablero.
`M.Sombra!63 "Flujo de caja IGV Neto" = D26 = IGV!D83`, y esa fila es
`IGV!83 = D79 - D82` con `D82 "Pago IGV" = IF(D81<0, 0, D79)`: cuando el IGV del
periodo es positivo lo pagan entero y el flujo queda en cero, y solo cuando es
negativo el saldo queda como **credito acumulado**, nunca como devolucion.

En el libro `IGV!83` suma **0.00** en toda la concesion, con solo 16 trimestres
no nulos, y **los 16 caen en construccion** (`IGV!78 "Recuperacion IGV"`,
51,713.67 en 17 trimestres). El tramo de operacion es cero nominal y cero en
valor presente, aunque los brutos sean enormes: `IGV!73` (IGV del PPDMO
variable) suma 138,793.96 y `IGV!77` (IGV de gastos de O&M) −115,503.38. Se
cancelan periodo a periodo dentro de `D79`.

**Es un resultado de este proyecto, no una regla.** Con un proyecto cuyo IGV neto
se volviera negativo en algun trimestre de operacion, el flujo dejaria de ser
cero y aparecereria un credito arrastrado. Por eso `motor_cajamarca` lo modela con
la asimetria del libro y no con un cero:

```python
acum_igv = dif + credito if t else dif
credito  = min(acum_igv, 0.0)
igv_neto[t] = dif - (0.0 if credito < 0 else acum_igv)
```

### Medir el crecimiento del O&M de extremo a extremo lo sobreestima

Corolario del 2026-09-16, que cambio una cifra del tablero en 1.8 puntos. Lo que
le importa al cierre es el **valor presente** del costo, no donde empieza y donde
termina la serie. La serie del libro **cae** en 2032-33 con la baja de las
fianzas y recien salta en 2037, o sea que los anos flojos son los cercanos, los
que menos se descuentan; un ajuste de extremo a extremo se los come.

```
sobre el O&M completo y los 264 meses que el contrato paga, al WACC mensual
VP real de la serie        255,563.96
VP del ano 1 plano         248,661.62
la serie vale                   +2.78 %
crecimiento constante equivalente  0.3633 %
extremo a extremo 2031-2051        0.5337 %
extremo a extremo 2031-2052        0.5670 %
```

El **+5.25 %** que aparece mas arriba en este documento es otra cosa y no lo
contradice: esta medido sobre `Costos!32`, que no lleva seguros, fianzas ni
fideicomiso y por eso no tiene la caida de 2033, y sobre la ventana 2030-2052.
Sobre el O&M completo la cifra que corresponde es **+2.8 %**.

**Defecto conocido de `cajamarca_om_anual.json`, ya anotado dentro del archivo:**
la fila de 2030 mezcla convenciones. `Costos!17/26/30/32` traen la tasa anual sin
prorratear, mientras seguros, fianzas y fideicomiso salen de `EEPPGG`, que solo
tiene el trimestre de operacion efectivo, porque la operacion arranca en octubre.
2052-2054 tienen el problema simetrico por el cierre de la concesion. Para el
primer ano hay que usar el campo `primer_ano_operacion_oct2030_set2031`, que trae
los 26,401.00 correctos; los anos 2031 a 2051 estan limpios.

### Dos archivos de referencia del libro de Cajamarca (2026-09-16)

Escritos para que nadie los reconstruya a mano, despues de que reconstruirlos a
mano produjera dos correcciones el mismo dia.

**`cajamarca_om_anual.json`** — el O&M del libro por ano, 25 anos, S/ miles a
precios constantes de dic-2025: fijos, reposiciones, variables, gastos SPV,
seguros, fianzas, fideicomiso y supervision, mas la ventana oct-2030 a set-2031
completa como campo aparte. La fila de 2030 mezcla convenciones y no sirve como
ano completo, igual que 2052-2054 por el cierre; esta avisado dentro del archivo.

**`cajamarca_msombra_anual.json`** — las 22 filas de `M.Sombra` (43 a 70)
agregadas por ano calendario, 28 anos, mas el valor presente al Ke de cada una.
**A precios corrientes**, con los signos de la hoja. Trae un control: el VP de la
fila 70 tiene que dar `M.Sombra!D74`, la celda contra la que cierra la tarifa.

El inventario en valor presente, que es lo que la pata variable recupera, con
cada linea en puntos de la propia pata variable (VP 152,865.91, 1 punto =
1,528.66):

```
Costo variable  62.37 %   Supervision OyM  2.48 %   Fideicomiso    0.31 %
Costo fijo      30.42 %   Seguros          2.17 %   Efecto ITAN    0.25 %
Impuesto Renta  15.06 %   Fianzas          1.04 %   DINS           0.00 %
Gastos SPV       6.84 %   Particip. trab.  2.69 %   Promocion      0.00 %
```

`M.Sombra!58 = SUM(D43:D57)` y las tres primeras filas son ingresos, asi que **no
hay ninguna otra linea de costo**. Util para descartar candidatos por tamano
antes de buscarlos.

## Los dos tramos complementarios de Cajamarca (medido el 2026-09-16)

Al buscar en `MODEF_PTAR_Cajamarca.xlsm` el tramo que financia IGV y capital de
trabajo aparecen dos cosas distintas, y conviene no confundirlas.

**El tramo de IGV esta cableado pero no aporta nada.** `M.Sombra!200` calcula la
necesidad de IGV (suma 3,427.97 S/ miles), y `D206` deberia inyectarla en la base
de deuda. No lo hace, por dos comparaciones entre tipos distintos puestas en
serie:

- `D204 = IF(D$191=$D$202,1,0)` compara el **numero** de trimestre (1,2,3...)
  contra `D202 = '7-2028'`, que es una **etiqueta de mes**; nunca coincide, asi
  que `D206 = SUMPRODUCT(D200:CV200,D204:CV204)*D205 = 0`.
- Y aunque `D206` no fuera cero, `Deuda!F12` lo suma bajo
  `IF(F$9=M.Sombra!$D$201,...)`, que compara el **contador de mes** (1..318)
  contra `D201 = 46935`, un **serial de fecha**; tampoco coincide nunca.

Consecuencia: la base de deuda senior es **exactamente** el costo de obra.
`Deuda!D13 = 261,144.81` coincide al centimo con `Σ('CAPEX proyecto'!37 × flag de
obra)`, la linea `D15 = 208,915.85` es el 80 % de eso, y los desembolsos de la
fila 36 suman 208,915.85 exactos. El flag deja fuera 17,366.23 de expediente
tecnico y supervision anteriores al inicio de obras, que si estan en el CAPEX
total (278,511.04): aplicar el 80 % al CAPEX entero da 222,808.83 y sobrestima la
deuda en 13,892.98. `deuda_cajamarca.py` ya toma la base con el flag.

**El complementario que si gira es capital de trabajo, y es de operacion.**
`Inputs!246-254` ("Financiamiento de Capital de Trabajo"): financia el 100 % de
la necesidad (`D250 = 1`), tasa `D251 = D252+D253` = soberano a vida media
5.788788 % + spread 1.00 % = 6.788788 % anual (TET trimestral 1.6556249 %,
`M.Sombra!D150`), repago en 1 trimestre (`D254`). Hay tres bloques de tramo
(`M.Sombra!155-162`, `167-174`, `179-186`) y solo dos tienen formula de
desembolso, en una sola columna cada uno:

| tramo | gira | monto | capitaliza | repaga | principal | interes trim. | servicio |
|---|---|---|---|---|---|---|---|
| T1 | trim. 17 (2030) | 6,314.54 | trim. 18 y 19 (104.55 + 106.28) | trim. 20 | 6,525.36 | 108.04 | 6,633.40 |
| T2 | trim. 18 (2031) | 6,392.03 | trim. 19 y 20 (105.83 + 107.58) | trim. 21 | 6,605.44 | 109.36 | 6,714.80 |
| T3 | cableado, nunca gira | | | | | | |

Total 12,706.57 desembolsado y 641.63 de interes, nominal. **El interes de los dos
trimestres intermedios se CAPITALIZA**, igual que el de obra: la amortizacion sale
negativa (`M.Sombra!158`, `170`) y el principal que se repaga es el girado mas los
dos intereses acumulados. Y `D254 = Trimestres de Repago = 1` significa que el
repago es **bullet en un solo trimestre**, no que venza al trimestre siguiente:
vence al tercero.

**Entra bruto en el flujo de caja financiero, nunca neteado**: el giro a `M.Sombra!31`
(Desembolsos) `= Deuda!F53 + D192` y el servicio a `M.Sombra!32`
`= -Deuda!F56 - D195`, o sea en el bloque de financiamiento, junto al senior. El
flujo operativo (`43:57`) no lo toca. El bloque `111:129` ("Esquema Capital de
Trabajo") solo **dimensiona**: `123 = (costos fijos + variables del trimestre) x
hito`. **Desde el 2026-09-17 esto ya esta modelado en `capital_trabajo.py`**, y no
queda ninguna cifra leida: alimentando la regla con `M.Sombra!121/122` salen los
dos giros al centimo (6,314.54 y 6,392.03), 12,706.57 desembolsados, 641.63 de
interes y 13,348.20 de servicio. **Que sean dos giros no es una regla**: el libro
tiene tres bloques cableados y solo dos con formula, y la necesidad `123` se
sigue calculando y creciendo sin que nadie la gire, asi que el numero de giros es
un input con el 2 del libro por defecto. **Cableado en `flujo_cajamarca` el 2026-09-17**: `des2`/`srv2`/`int2` ya no se
leen del libro, se calculan, y reproducen trimestre a trimestre con desvio maximo
4e-6 (participacion e IR al centimo, FCF 4.3e-6, tarifa 4.3176689717 contra
4.3176689715). Del libro queda **una sola** primitiva, el ITAN. La serie que hay
que pasarle es `costos["costo_fijo"]` y `costos["costo_var"]`, que SON
`M.Sombra!121/122`; **no** `D["fijo"]` y `D["var"]`, que son las dos patas del
PPDMO, o sea ingreso. Efecto: el PPDI no se mueve, porque cierra sobre el flujo
antes de deuda y esto es financiamiento; la tarifa cofinanciada baja de 3.8728067
a 3.8583316, -0.37 %. Tapa el hueco del
devengo: el EEPPGG devenga el PPDMO en su trimestre y la caja lo cobra al
siguiente. Se repaga entero en el primer trimestre con "Recuperacion de Capital
de Trabajo" (`M.Sombra!124`), antes de que el senior empiece a amortizar. La
necesidad se repite todos los trimestres (-6,392, -6,559, -6,823...) y no se
vuelve a financiar: la absorbe el aporte. Entra en el cierre por
`M.Sombra!31 = Deuda!F53+D192` y `32 = -Deuda!F56-D195`, que alimentan las filas
68/69 -> 70 -> `D74`, la celda del Goal Seek.

El generador no modela este tramo. Su huella es 641.63 nominales contra un VP de
la pata variable de 152,865.91, o sea menos de medio punto, y en direccion de
bajar el pago.

### Contra que cierra `M.Sombra!D74`: contra CERO, y los aportes no son una linea

`D74 = SUMPRODUCT(D70:DE70, D77:DE77)`, el VAN al Ke **mensual** (`D73`, derivado
de `Tasa!E19` = 12.8969 % anual) del **FC Financiero**, que es
`70 = FC Economico + Desembolsos - Servicio de deuda`. Valor en cache
**-5.14e-11**: cero.

Los aportes **no son una linea de ese VAN**: son la parte negativa del propio
flujo. Por eso VAN = 0 equivale exactamente a VP(aportes) = VP(excedentes) al Ke.
De ahi la confusion habitual: el VP del aporte *fija el nivel* de la pata
variable, pero no es un objetivo de calibracion, es la misma ecuacion escrita al
reves. Cerrar contra el cero de la fila 70 deja el aporte bien solo. Y el aporte
tampoco es una serie de obra: el tapon sigue disparando en operacion todos los
anos hasta 2052.

### La base que recupera el PPDI, linea por linea

`PPDI!112 Servicio de Construccion = -SUM(D150:D156)`:

```
150 Avances de Inversion (obra)      278,511.04   = 'CAPEX proyecto'!D42
151 Costo de Estructuracion            4,178.32   = Deuda!F46
152 Comision (por no uso)              1,518.56   = Deuda!F45
153 Gastos de Fideicomiso                350.00
154 Seguros                                0.00   linea viva en plantilla, cero aqui
155 Garantias                              0.00   idem
156 Reembolso gasto del proceso        8,437.11
    SERVICIO DE CONSTRUCCION         292,995.02
```

**No entra**: interes de obra (esta en la TASA, capitalizado en el saldo de la
deuda), capital de trabajo, impuesto ni IGV. Y la linea de obra son los
278,511.04 del CAPEX **entero**, no los 261,144.81 de la bandera de obra que
dimensionan la deuda: dos bases distintas en el mismo libro, y la del PPDI es la
ancha.

**En que mes cae cada linea, medido en el libro**:

```
150 obra              43 meses, mes 1 (2026-10) a 48 (2030-09)
151 estructuracion    UN mes: el 22 (2028-07), primer giro de la deuda
152 comision          26 meses, 22 a 47: comision por NO USO, se devenga
153 fideicomiso       42 meses, 8.33 por mes, del 7 (2027-04) al 48
156 reembolso         UN mes: el 1 (2026-10)
154/155 seguros y garantias: cero
```

No van todas al mes 1 aunque colocarlas ahi se acerque: el reembolso (8,437.11)
domina los 14,483.98 y tapa el error. El **primer cobro del PPDI es el mes 51**
(2030-12), 60 cuotas trimestrales de 11,618.14 hasta el mes 228 (2045-09);
colocarlo en el 49 vale 1.5 % en VP. Y el impuesto de `PPDI!158` son **14 pagos en
diciembre, decrecientes**, del mes 75 (2032-12, 1,717.92) al 231 (2045-12,
1,791.82), total 66,469.78. Las series estan en `caj_ppdi_lineas_mensual.csv`.

**Y ese impuesto esta APALANCADO, aunque viva en un flujo antes de deuda.** La
fila 160 es pre-deuda, pero el impuesto sale de un EEPPGG que deduce el interes
entero: `PPDI!158 = -D88`, `D88 = D100`, que busca en el estado anual de `407:428`,
cuya base imponible es `480 = SUM(D413,D421) - SUM(D414:D418, D422:D424)` con
**`D422` = Gastos Financieros = `PPDI!228` = `Deuda!F55` = 178,771.88**, o sea toda
la deuda, interes de obra incluido. Al 29.5 % (`Inputs!D14`) el escudo vale ~52,738
nominales contra un impuesto de 66,469.78, asi que calcular el impuesto del PPDI
sobre el devengo del activo sin el interes de la deuda lo **sobrestima por mas de
la mitad**. Es la cara del doble escudo: el cierre del PPDI **no es autocontenido**,
necesita correr el modulo de deuda antes. La base ademas **deduce el ingreso
financiero** (`481`) y lo **adiciona en cuotas de 1/15** (`482`, `Inputs!D214` = 15),
con arrastre de perdidas en `483:485`.

**Las tres celdas, porque ninguna es un calendario** (medido 2026-09-17):

```
482 = -IF(D481<0, 0, SUM($D481:D481)) / Inputs!$D$214 * IF(D$432>0, 1, 0)
481 = IF(D$411>1, -D$421, 0)
411 = Servicio de Construccion del ano;   432 = PPI cobrado en el ano
```

Se deduce mientras el ANO tenga servicio de construccion, no hasta un mes de
corte (2030 deduce 35,087.69 aunque la obra acabe en el mes 48). El numerador es
el acumulado a la fecha: 64,753.08 / 15 = 4,316.871965. Y lo que apaga el
arranque no es un ano sino el `IF(D481<0, 0, ...)`: el ano que todavia deduce no
puede adicionar, asi que la primera cuota cae en **2031** y la ultima en **2045**.

**Trampa portada: esa formula NO cuenta cuotas.** Emite acumulado/15 en todo ano
con cobro y sin deduccion, indefinidamente; que salgan quince es coincidencia de
este proyecto (60 cuotas trimestrales tocan dieciseis anos y el primero se apaga
solo). Con 80 cuotas adicionaria 133 % de lo deducido. El divisor es un plazo
TRIBUTARIO y el cobro un plazo CONTRACTUAL, y en la plantilla son dos campos
independientes, asi que el tope va explicito en `tributos_cajamarca._deducciones`
y en `motor_cajamarca.corrida`. Control: Cajamarca identico (los catorce anos a
0.0000 contra `PPDI!158`) y un sintetico de 25 anos de cobro devuelve exactamente
lo deducido, donde antes devolvia 173 %.

**Y la perdida arrastrada de cada ano de construccion ES el interes de deuda de
ese ano**, exactamente: como `480` = ingreso - interes y `481` = -ingreso, queda
`483 = -interes`. Acumulan 33,926.13 hasta 2030, se consumen enteros en 2031 y
dejan 5,823.47 gravables en 2032. La base neta de interes, en cambio, es positiva
los veinte anos: el activo nace entero con el servicio de construccion y la deuda
solo apalanca el 80 %.

**El cierre no es contra esa base sino contra un VAN**: `VAN(PPDI!160, WACC
mensual) = 0`, medido -0.0000. La fila 160 ("FC antes de Deuda") es
`SUM(149:159)`: el PPDI cobrado (697,088.20), las siete lineas de arriba, el
**Impuesto a la Renta** (`158`, -66,469.78) y el flujo neto de IGV (`159`).
El impuesto entra en el cierre **como flujo, con su propio calendario**, no como
base.

**El IGV de la fila 159 es cero en NOMINAL y no en valor presente**: +11,563.75
contra -11,563.75 repartidos en 45 meses, del 1 al 49, que al WACC mensual valen
**-317.66**, y del lado de pedir mas PPDI. Netear en nominal no es netear.


`PPDI!D116` ("Celda de control", saldo final del activo, -2.57e-8) **no es el
objetivo**: el activo devenga al `Rendimiento` de `D118 = IRR(D117:LC117)`, la TIR
de su propio flujo (0.8696297 % mensual, 10.9494 % anual, distinta del WACC
mensual 0.7670953 %), asi que amortiza a cero para cualquier nivel de PPDI. Es un
control. Medido: `VAN(160)` = 0 al WACC y -20,011.62 a la implicita; `VAN(117)` =
0 a la implicita y +22,852.83 al WACC.

### El impuesto cae en el ULTIMO trimestre del ano calendario

`EEPPGG!D31 = IF(D$4=0, 0, HLOOKUP(D$5, 'EEFF Anuales'!$D$47:$AE$74, 27, FALSE))`
y la bandera es `D4 = IF(D$7 = HLOOKUP(...), 1, IF(E$5 - D$5 = 1, 1, 0))`: se
enciende en el trimestre cuya **columna siguiente cambia de ano calendario**. El
IR entero del ano y la participacion de trabajadores (`D23`) caen ahi y pasan a
`M.Sombra!21` y `22` sin mas. Trim. 25 (2032) IR 5,093.55 y PT 908.75; trim. 29
(2033) 7,332.16 y 1,308.15; luego 33, 37, 41...

El ano es el **de la etiqueta de EEPPGG**, que no es la de `M.Sombra`. Repartir
el impuesto por trimestre en vez de cargarlo entero en ese uno cuesta 5.53 % en
VP al Ke (30,111 contra 28,534), o sea **0.98 pp** sobre la pata variable, y con
el signo esperable: pagar antes exige mas ingreso.

**San Martin usa la misma convencion, y lo dice explicito.** No es de Cajamarca,
es de la casa: `FC_Trim!35 = -SUMIF(Impuestos!$F$4:$AG$4, FC_Trim!F5,
Impuestos!$F$52:$AG$52)*(MONTH(F3)=12)`, y `FC_Trim!36` igual contra
`Impuestos!$F$77`. Trimestres 25 (2031), 29, 33, 37, 41... 19 anos con impuesto.
Pero ahi es **inerte para el cierre**, porque San Martin cierra sobre la malla
ANUAL (`FC!D80 = VAN FCF = 0.000795`, `FC!D74 TIR = 0.119 = TIR_Objetivo`) y las
filas `FC!42` y `FC!43` leen `-Impuestos!K52` y `-Impuestos!K77` directo, una
cifra por ano. `FC_Trim` es hoja de presentacion.

## El gatillo del 3 % hace una escalera, y el plazo de la deuda senior

**El reajuste de ingresos de Cajamarca no crece: salta.** `PPDMO!16` acumula el
IPM mensual no aplicado y lo libera entero el mes en que alcanza el 3 %
(`Inputs!D37`); `PPDMO!18` lo compone con `TRUNC(...,5)`. Al IPM del libro
(1.1893 % anual, 0.09856810 % mensual) la meseta dura 30 meses y el factor tiene
**nueve peldaños** en los 264 meses de operacion:

```
2030-10  1.00000   2038-06  1.09448   2046-03  1.19789
2033-04  1.03055   2041-01  1.12792   2048-10  1.23449
2035-11  1.06203   2043-08  1.16238   2051-05  1.27221
```

El **año 1 entero corre a factor 1.00000**, y los 30 primeros meses tambien. Al
IPM de Oscar (2.67 %) la meseta baja a 13 meses, son 19 peldaños y el factor
final llega a 1.72553. `ipm_cajamarca.py` lo reproduce con desvio 0.000000000000
contra `PPDMO!18` y toma el flag de operacion **del proyecto**, no el del libro.

Direccion del efecto, que es contraintuitiva y conviene tener a mano al comparar
contra un aproximador que indexe liso: descontando al Ke mensual
(`Tasa!E19` = 12.896919 %), el VP del factor liso queda **+1.518 %** sobre el de
la escalera, y el promedio del año 1 del liso +0.643 %. Como el cierre reparte el
mismo VP, indexar liso da un precio unitario ~1.5 % **mas bajo** que el del
libro. Poner la escalera **sube** el nivel del año 1.

**La cuota senior se dimensiona sobre el saldo, no sobre lo desembolsado.**
`Deuda!D25 = -PMT(tasa mensual, 144, saldo al mes base)` y el saldo al mes base
(2030-09-30, fin de puesta en marcha) es **237,567.72**, que son los 208,915.85
desembolsados mas **28,651.88 de interes capitalizado en obra**. Servicio del
2030-10-31 al 2042-09-30, 144 cuotas constantes de 2,692.2759, amortizacion como
residuo, y el PPDI corre tres años mas que la deuda. Los 8,076.83 de servicio de
2030 son tres cuotas (oct, nov, dic), ya con amortizacion: en octubre 1,764.99 de
interes contra 927.28 de amortizacion.

Si se amortiza lo desembolsado en vez del saldo crecido, la cuota sale **12.06 %
baja cualquiera sea el plazo**: `PMT(0.00742943,144,208915.85) = 2,367.5737`
contra los 2,692.2759 del libro. Acortar el plazo no lo arregla.

## Devengo y cobro del PPDMO: dos convenciones, nunca las dos

El mismo hecho (el PPDMO se devenga antes de cobrarse) esta resuelto de dos
maneras distintas en los dos libros, y aplicar las dos a la vez lo cuenta dos
veces.

**Cajamarca corre la fila.** `EEPPGG!D10 = SUMIFS(PPDMO!$D$23:$LJ$23,...)`
devenga el servicio y `M.Sombra!D10 = SUMIFS(PPDMO!$D$34:$LJ$34,...)` cobra el
pago: dos filas distintas de la misma hoja, con el cobro un trimestre despues. No
hay bloque de capital de trabajo en el flujo; el hueco lo tapa el tramo de deuda
de 12,706.57 de la seccion anterior. Se ve en el pago: 2030 tiene PPDI (11,618.14,
un trimestre exacto) y cero de PPDMO, que arranca en 2031.

**San Martin deja la fila alineada y lleva un saldo.** Devengo y cobro leen las
mismas celdas en la misma columna: `P&G!16 = SUM(Cons_Anual!F18:F21)` contra
`FC!18-21 = Cons_Anual!F18..F21`, y en la malla trimestral `Cons_Trim!19-23` y
`FC_Trim!15-16` hacen `SUMIF` sobre `Ingresos!144:148` con el **mismo** numero de
trimestre, `FC_Trim!F$7`. El desfase vive en `FC!94-107`: `95 Devengo Ingresos`,
`96 CxC (a Balance)` (de `Ingresos!156` + `Ingresos!161`),
`98 Variacion a CF = E96-F96-E99`, y del lado del costo
`102 Periodo medio de pago = Control!G45 = 1 mes` con
`103 CxP = (Costos O&M / meses de operacion) x 1`.

En un año de regimen: devengo 68.7 MM, CxC 41.9 MM (unos 7.3 meses de ingreso),
CxP 4.6 MM.

**Cuidado: el bloque suma cero en nominal y NO en valor presente.** `FC!D107`
suma 5.59e-9, pero el saldo se arma al arrancar la operacion y se suelta quince y
diecinueve años despues (-10.13 MM en 2029 por la dotacion del capital de trabajo
inicial, -36.06 MM en 2030 al armarse las cuentas por cobrar, sueltas de
+24.24 MM en 2045 y +16.22 MM en 2049 por el "Ajuste ultimo año" de las filas 99
y 105, y entre -625 mil y +25 mil al año en el medio). Descontado:

```
                                  VP al Ke 11.896982 %   VP al Ke!C25 9.9513 %
FC!29 Variacion capital de trabajo     -16,143,070            -16,865,194
FC!30 CR capital de trabajo inicial       -614,136               -570,710
      bloque FC!94-107                 -16,757,206            -17,435,905
      VP del PPDMO (FC!18-22)          310,032,387            387,434,272
      bloque / PPDMO                       -5.405 %               -4.500 %
```

Leer el cero nominal como "no cuesta nada" fue un error, corregido el
2026-09-16.

Para el generador: el desfase cuesta en los dos libros, lo que cambia es donde se
ve. **Este motor lleva el bloque**, armado con los datos del propio proyecto:
`flujo_sm.py` construye `cxc` con
`I.caja(ppdi_m, ppdmo_m, cal, desfase_ppdi, desfase_ppdmo, conc)` y
`cxp = costos O&M / meses x 'Periodo medio de pago a proveedores'`, con `aj99` y
`aj105` soltando los saldos al final. Por eso la rama por hitos no necesita
rezago: el desfase esta representado como saldo. Una herramienta **sin balance**
si necesita el rezago como proxy, y ahi va en las dos ramas, porque es una
condicion de facturacion y no una caracteristica del esquema de pago. Lo que no
se puede es llevar las dos piezas a la vez.

## El interes de obra: los dos libros lo tratan al reves

La prueba rapida para cualquier libro es una sola: **el saldo al inicio de la
amortizacion, ¿es igual a la suma de los desembolsos o mayor?** Igual = el
interes se gira; mayor = se capitaliza. Aplicar las dos convenciones a la vez
infla la inversion y adelgaza el servicio **al mismo tiempo**, que es el par de
sintomas que delata el error.

**Cajamarca acumula sobre el saldo.** Servicio cero durante la obra, el interes
se capitaliza, el saldo al mes base (2030-09-30) es **237,567.72** contra
**208,915.85** de desembolsos, o sea **28,651.88** mas, y
`Deuda!D25 = -PMT(tasa, 144, saldo)` amortiza el saldo crecido.
`deuda_cajamarca.py` lo hace asi.

**San Martin lo gira y lo paga.** El interes entra en las necesidades
(`Nec_Fin!17 = Nec_Fin!72 = saldo x tasa mensual`, circular, resuelta por
iteracion) y se financia como parte de ellas:

```
Nec_Fin!21 Total necesidades = Capex + Otros costos constr. + Variacion IGV
                             + Intereses (66,454,727.93) + Comisiones (18,504,126.40)
                             + Dotacion inicial CRSD + Capital de Trabajo Inicial
                             = 698,107,786.82   ->  80 % deuda / 20 % capital

Nec_Fin!D68 Desembolsos        558,486,229.45
Deuda Anual!D22 Desembolsos    558,486,229.45
Deuda Anual!D23 Amortizacion  -558,486,229.45   (check fila 25: OK)
```

El saldo **no capitaliza nada**. El aporte paga el 20 % del interes de obra
porque paga el 20 % de todas las necesidades, no por duplicacion:
`Nec_Fin!51 Check EOAF Construccion` (`D21 - D39 - D48 = 0`) da OK.
`motor_sanmartin.necesidades` lo hace asi (`saldo_d = saldo_d*flag + desemb;
n_i = saldo_d*kd_m`), con el interes realimentado al punto fijo y el saldo
limpio.

Datos de la hoja `Deuda Anual` de San Martin, utiles de contraste: plazo `D38`
15.25 años, primer desembolso 2027-10-01, ultimo repago 2042-12-31, cola de 2.00
años respecto del PPDI, vida media `D44` 8.8366 años, RCSD minimo y medio 1.25,
tasa `D60` 10.5006 %, upfront fee 2 %, commitment fee 1 % anual sobre lo no
girado, management fee cero.

## La serie anual de la deuda de San Martin, y como se dimensiona

Las cuatro lineas que gobiernan la deuda por cobertura:

```
Deuda Anual!14  CFADS   = (FC!50 - 'Deuda Anual'!57) * (flag operacion > 0)
Deuda Anual!16  max SD  = CFADS / RCSD                 (RCSD = Control!J6 = 1.25)
Deuda Anual!28  interes = -tasa * (saldo_ini + desembolsos + amort/4) * flag_op
Deuda Anual!23  amort   = -MIN(saldo_ini, MAX(0, max_SD + interes + comisiones_op))
```

Tres trampas. **`F57` no es de `FC`**, es de la propia hoja
(`'Primera Dotacion de CRSD'`, 30,191,724.16, toda en 2029); `FC!50` va
calificado y el otro no. En este libro no se nota porque 2029 tiene el flag de
operacion en cero, y por eso `Deuda Anual!14` coincide con `FC!45` en los 13 años
de operacion, verificado uno por uno. **La amortizacion es `CFADS/RCSD` menos el
interes**, no `CFADS/RCSD`: sin esa resta la amortizacion se multiplica por ~2.7
y la vida media cae de 8.84 a ~3.9 años, con el cierre absorbiendolo y la
desviacion publicada quieta. Y la base del interes lleva **`amort/4`**, no
`amort/2`.

El RCSD de salida (fila 36) da **1.250 clavado** todos los años menos 2042, donde
sale 1.599 porque muerde el `MIN` con el saldo: el ultimo repago es **salida**, no
plazo impuesto.

```
anio       CFADS      max SD        amort     interes op     servicio   RCSD     saldo fin
2029                                                                           558,486,229
2030  75,479,310  60,383,448   -1,785,927   -58,597,522   60,383,448  1.250    556,700,303
2031 113,218,944  90,575,155  -32,984,167   -57,590,988   90,575,155  1.250    523,716,136
2032 107,893,623  86,314,898  -32,165,967   -54,148,932   86,314,898  1.250    491,550,169
2033 107,251,803  85,801,442  -35,107,346   -50,694,097   85,801,442  1.250    456,442,823
2034 107,731,426  86,185,141  -39,287,255   -46,897,886   86,185,141  1.250    417,155,568
2035 105,609,874  84,487,899  -41,780,872   -42,707,027   84,487,899  1.250    375,374,696
2036 103,001,950  82,401,560  -44,143,806   -38,257,754   82,401,560  1.250    331,230,890
2037 101,915,999  81,532,799  -48,011,954   -33,520,845   81,532,799  1.250    283,218,936
2038  99,770,896  79,816,717  -51,427,067   -28,389,650   79,816,717  1.250    231,791,869
2039  99,364,325  79,491,460  -56,638,776   -22,852,684   79,491,460  1.250    175,153,093
2040  94,457,803  75,566,242  -58,715,486   -16,850,756   75,566,242  1.250    116,437,607
2041  92,551,370  74,041,096  -63,480,918   -10,560,178   74,041,096  1.250     52,956,689
2042  91,350,602  73,080,482  -52,956,689    -4,170,578   57,127,267  1.599             0
```

Interes total en operacion 465,238,896, el **83 % del principal**, que es lo que
estira la vida media a 8.8366 años.

Composicion del CFADS de 2031 (soles): PPDI 97,607,150 + PPDMO fijo 52,432,022 +
variable 14,643,281 + Pago por Obras 6,738,785 - costos fijos 28,657,896 -
variables 10,458,029 - GG+U 6,267,922 - otros 6,107,482 - IGV operacion 3,225,406
- variacion de capital de trabajo 548,801 - IR 2,164,434 - participacion 772,323
= 113,218,944. **El PPDI entra.** La dotacion del CRSD, salvo la primera, no:
vive en `FC!58`, despues del servicio.

`flujo_sm.py` lo reproduce con `serv=(fc_50[i]-prim_dot[i])*(fop[i]>0)`,
`io=-kd*(ini+dis+amort[i]/4)*fop[i]` y `am=-min(ini,max(0,serv/RCSD+io))`.

## La base imponible de San Martin sigue la forma legal, no la CINIIF 12

El libro lleva **dos calculos paralelos a proposito**: el `P&G` presenta el activo
financiero de la CINIIF 12 y la hoja `Impuestos` arma la base gravada por la
forma legal. Confundirlos infla la base al doble. Cadena de 2031, en soles:

```
14 PPD Inversion            +97,607,150   <- el PPDI ENTERO como ingreso, no el
15 PPD MO Fijo              +52,432,022      ingreso financiero de 77,499,726
16 PPD MO Variable          +14,643,281      que muestra el `P&G`
17 Pago por Obra             +6,738,785
18-21 costos e IGV op.      -54,716,735
24 Intereses de operacion   -57,590,988
26 Costo Amortizable        -37,021,590
27 Int. de construccion      -6,645,473
30 Resultado tributable    =15,446,451
32 Participacion (5 %)         -772,323
34 Base despues de part.   =14,674,128
44 Compensacion, tope 50 %   -7,337,064
48 Base ajustada            =7,337,064
52 IR (29.5 %)              =2,164,434
```

Las tres piezas que no estan en el estado de resultados:

1. **El PPDI entra como ingreso gravado.** La presentacion contable no manda.
2. **Dos amortizaciones deducibles.** `Impuestos!61 = D57 x 12/180`: el CAPEX
   entero (555,323,846.25) sobre los **180 meses de pago del PPDI**, no sobre la
   vida del activo, 37,021,590 al año. Y `Impuestos!70 = D68/D69`: los intereses
   de construccion (66,454,728) en **10 años** (`Control!C36`), 6,645,473.
3. **Arrastre de perdidas con tope del 50 %** (`Impuestos!D38 = 0.5`, sistema b
   peruano). En 2031 compensa 7,337,064 y **divide el IR por dos**. El saldo
   viene de la construccion: 36,860,678 al cierre de 2030, 29,523,614 al de 2031.

Tasas: `Control!C34` IR 29.5 %, `C35` participacion 5 %, `C36` 10 años.

Importa mas alla del impuesto, porque el **CFADS que dimensiona la deuda sale
neto de estos impuestos** (`Deuda Anual!14 = FC!50 - Primera Dotacion de CRSD`, y
`FC!50` ya viene despues del IR y de la participacion). Un motor que arme la base
desde el ingreso financiero saca un impuesto varias veces mayor, se queda con un
CFADS chico y dimensiona mal el principal.

Y para la decision tributaria abierta: en el caso **cofinanciado el libro ya
decidio**, presentando activo financiero y deduciendo igual la amortizacion del
CAPEX. Lo que queda abierto es solo la rama **autofinanciada**, donde el
intangible reemplazaria a la depreciacion y el libro no tiene ese caso.
`flujo_sm.py` lleva las tres piezas (`amort_capex`, `gf_am` con `plazo_gf=10.0`,
`arrastre=0.5`) y reproduce el IR total: 188,359,633.52 contra 188,359,633.53.

---

## El activo financiero nace del servicio de construccion, y los dos libros lo arman igual

El hilo del tablero llego a esto midiendo su propio motor, que lo levantaba
sobre `nec + intDC` -- la necesidad de financiamiento --, y eso mete comisiones,
capital de trabajo, IGV, reserva e intereses capitalizados. **No es eso.** La
CINIIF 12 p.16 reconoce una cuenta por cobrar contra el concedente por el
**servicio de construccion prestado**, y los dos libros aprobados lo arman asi,
con la misma mecanica y en distinta malla.

**Cajamarca**, malla mensual. El servicio del periodo es `PPDI!150`: obra mas
fideicomiso, seguros, garantias, reembolso, estructuracion y comision. Nada de
interes capitalizado -- esa es la razon de que `PPDI!150` vaya entero a
`CronogramaCAPEX` sin tocar `Deuda` ni `Nec_Fin`. Total 292,995.02 S/ miles.

**San Martin**, malla trimestral, `Act_Financ TRIM!14:17` agregado a anual en
`Act_Financ!15:20`:

```
14 Capex                        = -SUM(Cons_Trim!36:39)     555,323,846.25
15 Otras inversiones [D+C+PM]   = -Cons_Trim!40              17,316,984.93
16 PPD Inversiones              = -SUM(Cons_Trim!15:18)  -1,464,107,249.13
17 Total                        = SUM(14:16)              -891,466,417.94
19 Tasa Equivalente Trimestral  = IRR(F17:DM17)                  2.942246 %
26 Ingreso financiero           = saldo inicial x D19       891,466,417.94
29 Check AF                     = SUM(23:26) redondeado                 OK
```

Base **572,640,831.19**, que no es el CAPEX solo ni la necesidad de
financiamiento (698,107,786.82). Quedan fuera las comisiones, el IGV, la
reserva, el capital de trabajo, los intereses capitalizados **y** los
`Costos cierre laguna SJS` (6,738,784.79), que el libro paga y no activa.

El ingreso financiero total no es un resultado, es el saldo: sale
`-(capex + otros + PPDI)` cualquiera sea la tasa. Lo que la tasa decide es el
**reparto por anos**. Por eso una base equivocada no se arregla recalibrando la
tasa: la TIR se reacomoda sola y lo que queda torcido es la forma.

### Lo que hace el generador

- **Rama al final de obra**: correcto y medido. `motor_cajamarca.corrida` arma
  `_sc` con las siete piezas de `PPDI!150` y saca la tasa como TIR de
  `-servicio + PPDI cobrado`. En el libro generado la fila "Servicio de
  construccion del periodo" suma **292,995.0198** y la tasa implicita sale
  0.8669497 % mensual = **10.914072 %** anual.
- **Rama por hitos**: la hoja **faltaba**. El flujo nunca la necesito, porque la
  base imponible de San Martin sigue la forma legal y el activo financiero no
  entra en el impuesto, pero el libro aprobado la presenta y el generado no.
  Anadida como `Activo financiero` en `escribir_excel_sm.py`, sobre las filas
  CAPEX, "Otros costos del periodo D+C+PM" y "PPD Inversiones" del propio
  `Flujo`, con formulas vivas y los mismos controles del libro.

La malla del generador es anual y la del libro trimestral. Medido sobre las
propias filas de `Act_Financ`, la tasa anual sale **12.288384 %** contra el
**12.298657 %** de la trimestral llevada al ano: 1.03 puntos base. El ingreso
financiero total calza al 0.000 %, por lo dicho arriba.

Recalculado en LibreOffice, en el libro de San Martin y en el del proyecto
inventado: `Check AF` OK, saldo final -0.0003 sobre un maximo de 652.8 millones
en el primero y -1.6e-10 en el segundo, cero anos con saldo negativo, ningun
`#VALUE!`. Las cuatro combinaciones de `matriz.py` siguen cerrando en 0.00000001
y el proyecto inventado tambien.

**Cuidado con el signo**: la hoja es el negativo de las filas de caja. El CAPEX
sale del flujo como salida y entra al activo como alta; el PPDI entra al flujo
como cobro y sale del activo como amortizacion.

**La rama autofinanciada no lleva esta hoja**: sin PPDI no hay cuenta por cobrar,
la obra es intangible (p.17) y su base **si** incluye los intereses capitalizados
y las comisiones de construccion, por la p.22 y la NIC 23. Son dos bases
distintas a proposito; no unificarlas.

### El bloque tributario de Cajamarca ya trataba bien el ingreso del activo

La otra mitad de lo mismo, verificada de paso. El ingreso financiero del activo
no es renta gravada mientras dura la obra y vuelve en cuotas de 1/15 desde que
empieza a cobrarse el PPDI. El motor lo hace en dos sitios, los dos del libro:

- `motor_cajamarca.corrida`, el cierre del propio PPDI (`PPDI!481:485`):
  `deduccion = -ing_fin si serv_constr > 1`, `adicion = -ded_acum/15` cuando hay
  cobro, arrastre sin tope.
- `tributos_cajamarca.py`, el bloque anual (`EEFF Anuales!82:98`), que
  `flujo_cajamarca.py:98` alimenta con `serv_constr` e `ing_fin` de esa misma
  corrida. Desvio contra el libro 0.00000000 en participacion y en IR, y los
  seis anos sin impuesto (2026-2031) calzan exactos.

`sombra_cajamarca.py` no calcula impuestos; el flujo sombra los recibe de
`flujo_cajamarca.py`.

---

## El monto de la deuda por hitos no sale de la cobertura

Medido el 2026-09-16 en `Modelo_Hitos_Funcionales.xlsm`, a proposito de una
brecha de perfil que el hilo del tablero no lograba cerrar.

```
FC!47 Aportes de Capital     139,621,557.36   = 20.0000 % de las necesidades
FC!48 Financiamiento         558,486,229.45   = 80.0000 % de las necesidades
                             --------------
                             698,107,786.82   = Nec_Fin!21, exacto
```

El 0.8 es `Control!F22`. **La cobertura solo dimensiona la amortizacion ano a
ano**, y por eso el `RCSD (salida)` de `Deuda Anual!36` da 1.250000 clavado en
2030-2041 y 1.599072 en 2042, el ano en que el saldo se acaba antes que la caja.

La prueba de que la cobertura no restringe el monto: `Deuda Anual!16 Max.
servicio de la deuda = 1,266,642,045.86` contra `!35 Servicio de la Deuda
(operacion) = 1,023,725,125.36`. Sobran 243 MM de capacidad sin usar. Un motor
que dimensione el principal por cobertura pondra mas deuda que el libro, y eso
no se ve mirando el perfil: se ve mirando el monto.

Cronograma, con el saldo entrando a operacion en **558,486,229.45** al cierre de
2029. Los desembolsos suman exactamente eso y las amortizaciones tambien, asi que
**no hay interes capitalizado sobre la linea**: los 66,454,727.93 de interes de
obra se financian dentro de las necesidades y se pagan en caja.

```
ano   saldo inicial      amortizacion     saldo final     interes op      CFADS
2027           0.00              0.00   33,115,318.68           0.00
2028  33,115,318.68              0.00  331,808,375.04           0.00
2029 331,808,375.04              0.00  558,486,229.45           0.00
2030 558,486,229.45     -1,785,926.56  556,700,302.89 -58,597,521.76  75,479,310.40
2031 556,700,302.89    -32,984,167.16  523,716,135.73 -57,590,988.14 113,218,944.12
2032 523,716,135.73    -32,165,966.80  491,550,168.93 -54,148,931.67 107,893,623.09
2033 491,550,168.93    -35,107,345.69  456,442,823.24 -50,694,096.55 107,251,802.80
2034 456,442,823.24    -39,287,255.44  417,155,567.80 -46,897,885.71 107,731,426.44
2035 417,155,567.80    -41,780,871.88  375,374,695.92 -42,707,026.99 105,609,873.60
2036 375,374,695.92    -44,143,805.82  331,230,890.10 -38,257,754.20 103,001,950.03
2037 331,230,890.10    -48,011,953.95  283,218,936.14 -33,520,845.04 101,915,998.74
2038 283,218,936.14    -51,427,067.01  231,791,869.13 -28,389,649.96  99,770,896.22
2039 231,791,869.13    -56,638,776.09  175,153,093.04 -22,852,684.18  99,364,325.34
2040 175,153,093.04    -58,715,486.11  116,437,606.93 -16,850,756.10  94,457,802.76
2041 116,437,606.93    -63,480,917.96   52,956,688.97 -10,560,178.04  92,551,369.99
2042  52,956,688.97    -52,956,688.97            0.00  -4,170,577.56  91,350,601.88
```

`!18` tasa 10.5006 %, `!19` management fee 0, `!38` plazo 15.25, `!39` primer
desembolso 2027-10-01, `!40` ultimo repago 2042-12-31, `!43` cola 2.0027 anos
respecto del PPDI, `!44` vida media 8.836634534. Comisiones 18,504,126.40 en
obra y **0 en operacion**.

**El primer ano de operacion casi no amortiza: 1.79 MM sobre 558.5.** Ahi esta
buena parte de la vida media de 8.84, y la razon es el CFADS de 2030, 75.5 MM
contra 113.2 en 2031. Un motor cuyo 2030 amortice decenas de millones se queda
corto de vida media aunque el resto del perfil este bien.

La base del interes lleva la cuota dividida entre cuatro, confirmado:
`(558,486,229.45 + (-1,785,926.56)/4) x 0.105006 = 58,597,521.759` contra
58,597,521.76 del libro.

**CRSD**: objetivo 50 % (`!49`). `!57 Primera Dotacion = 30,191,724.16`, en 2029,
el ultimo ano de obra, exactamente la mitad del servicio de 2030
(`(1,785,926.56 + 58,597,521.76) x 0.5`). Luego 15,095,853.49 en 2030 y
191,849.45 en 2033; el resto de anos la dotacion es cero y el saldo se mueve por
desdotacion.

**El IGV de operacion mueve la caja, no solo la base imponible.**
`FC!28 IGV Operacion = -69,668,080.69` esta **arriba** de `FC!40 FC antes de
impuestos`, asi que baja el CFADS y baja la base. Las dos cosas.

Anclas tributarias del libro: `FC!42 IR = -188,359,633.53`,
`FC!43 Participacion = -35,545,679.50`, razon **5.2991** contra el 5.6050 que
daria la misma base sin tope. Cajamarca da 5.6050 exacto y San Martin no, y esa
diferencia es el tope del 50 %.

`motor_sanmartin.py` ya toma `apalancamiento = 0.8` de `Control!F22` via
`sanmartin_primitivos.json`, y por eso reproduce la vida media del libro exacta.

---

## `Nec_Fin` de San Martin, desglosada, y el pico de capital de trabajo de 2030

Las siete lineas de las necesidades, medidas el 2026-09-16:

```
Nec_Fin!14 Capex                             555,323,846.25
Nec_Fin!15 Otros costos en constr.            17,316,984.93
Nec_Fin!16 Variacion IGV construccion            183,377.14
Nec_Fin!17 Intereses                          66,454,727.93
Nec_Fin!18 Comisiones                         18,504,126.40
Nec_Fin!19 Dotacion inicial CRSD              30,191,724.16
Nec_Fin!20 Capital de Trabajo Inicial         10,133,000.00
                                             --------------
Nec_Fin!21 Total                             698,107,786.82
Nec_Fin!23 Total sin CRSD                    667,916,062.66
Nec_Fin!24 VAN del total sin CRSD            519,739,073.65
Nec_Fin!25 Tasa de descuento mensual            0.793694 %
Nec_Fin!27 Apalancamiento                              0.8
Nec_Fin!28 Capital                           139,621,557.36
Nec_Fin!29 Deuda                             558,486,229.45
```

Aportes de capital: 25 % en el mes 1, 25 % en el 10, 50 % en el 16 (`!32-37`).
**El VAN de `!24` es sobre el total SIN la CRSD**, y es el que cierra contra el
PPDI: la dotacion inicial de la reserva se financia pero no entra en ese VAN.

El capital de trabajo inicial de 10,133,000 es una **linea suelta**, no derivada
del OPEX.

### El primer ano de operacion se lleva un pico de capital de trabajo

`FC!29 Variacion capital de trabajo` por ano, con `FC!30` al lado:

```
2029             0.00   |  FC!30  -10,133,000.00
2030   -36,062,084.13   |  FC!30  +10,133,000.00
2031 a 2044  entre -624,596 y +16,580
2045    24,238,310.69
2049    16,217,233.55
total         5.59e-09
```

El −36 MM de 2030 es el arranque de las cuentas por cobrar: el primer ano de
operacion devenga todo y cobra con desfase, y eso se paga una sola vez. Con la
liberacion del KT inicial el efecto neto de 2030 son −25,929,084.

**La dotacion de la CRSD de 2030 NO sale del CFADS de 2030.** `FC!58` esta debajo
de `FC!50`, y `Deuda Anual!14` copia `FC!50`; solo la **primera** dotacion se
resta, y esa es la de 2029. Medido en la columna 2030: `FC!40` = `FC!45` =
`FC!50` = `Deuda Anual!14` = 75,479,310.40, con `FC!58` = -15,095,853.49 aparte.
Atribuir esos 15.1 MM a la brecha del CFADS de 2030 es el error facil; lo que la
explica es el capital de trabajo (-25.9 MM neto) y el IGV de operacion (-3.2 MM).

### `FC` de San Martin, 2030 y 2031, y la pareja de la laguna

Los subtotales que hacen falta para diagnosticar el primer ano de operacion, que
es el que define la vida media:

```
                                  2030              2031
ingresos (FC!14-23)     162,390,603.67    171,421,237.23
costos O&M (FC!24-27)   -51,212,907.98    -51,491,329.29
                        --------------    --------------
ingreso menos costo     111,177,695.69    119,929,907.94
IGV operacion             -3,213,893.51     -3,225,406.31
variacion de KT          -36,062,084.13       -548,801.02
liberacion del KT ini     10,133,000.00              0.00
FC!32 FC Operacional     82,034,718.05    116,155,700.61
IGV [D + C + PM]            183,377.14              0.00
cierre laguna SJS        -6,738,784.79              0.00
FC!40 antes de impuestos 75,479,310.40    116,155,700.61
```

Los costos de O&M son **planos** entre los dos anos (51.2 y 51.5 MM), asi que una
brecha que se mueva mucho entre 2030 y 2031 esta del lado del ingreso. En 2030 el
**PPDI ya cobra entero** (97,607,150, las cuatro cuotas) y el PPDMO fijo arranca
en 50,876,473 contra 52,432,022 en 2031.

**El cierre de la laguna SJS es una pareja a un ano de distancia.** El libro paga
6,738,784.79 en 2030 (`FC!37`) y cobra exactamente lo mismo en 2031 como
`Pago por Obras` (`FC!23`). Es un pass-through diferido que le quita caja a 2030
justo el ano que define la vida media; si las dos caen el mismo ano se netean y
el efecto se pierde. El generador ya lo reproduce con el desfase correcto
(comprobado en `PTAR_San_Martin_generado.xlsx`, filas Pago por Obras y laguna).

### Las reposiciones de San Martin no son planas

`FC!38 Reposiciones` = -9,520,470.69 sobre toda la concesion, pero en **cinco anos
sueltos**: 2040 -172,574.34, 2041 -135,363.59, 2042 -57,248.59, 2044
-4,014,249.61 y 2046 -5,141,034.55. Cero hasta 2039.

Es lo contrario de Cajamarca, donde `Reposiciones!L88` las nivela plano a
2,134,450 al ano. Aqui el 96 % cae **despues del ultimo repago de la deuda**
(2042), asi que solo los tres golpes chicos de 2040-2042, 365,187 en total,
muerden la cobertura. Nivelarlas a 9.5/20 = 476,024 al ano se come 1.4 MM de
CFADS entre 2030 y 2042 que el libro no tiene, y ahi la cobertura si lo nota.

**Plano o cronograma es por libro, no una convencion del esquema.**

---

## El IGV de operacion: los dos libros lo modelan, y lo que cambia es si se repercute

Verificado hoja por hoja el 2026-09-16, despues de que Oscar corrigiera la nota
que decia que el IGV de operacion de Cajamarca era cero. No es cero: **es
neutro**, que no es lo mismo.

### Cajamarca lo repercute sobre el PPD, y por eso se le lava

Pestana propia `IGV`, con la cadena entera y viva:

```
IGV!71 IGV PPD I                     125,475.88   60 trimestres
IGV!72 IGV PPD MO fijo                27,796.14   83
IGV!73 IGV PPD MO variable (DBO5)    138,793.96   83
IGV!74 IGV Capex                     -50,131.99   15
IGV!75 IGV de Gastos Proceso          -1,518.68    1
IGV!76 IGV Gastos DC                     -63.00   14
IGV!77 IGV Gastos OM                -115,503.38   83
IGV!78 Recuperacion IGV               51,713.67   17
IGV!79 IGV del periodo               176,562.60   98
IGV!82 Pago IGV                      176,562.60   83, de 2030 a 2051
IGV!83 Flujo de Caja IGV S/ Miles          0.00   solo 2026-2030
```

La clave es la ultima fila. **El flujo de caja del IGV solo existe entre 2026 y
2030**, la obra y su recuperacion, y suma cero. De 2030 a 2051 el IGV de
operacion se cobra sobre el PPD y se remite, asi que **no toca la caja del
concesionario**: existe en el modelo y no aparece en el flujo. En `M.Sombra!26` y
`!63` (`Flujo de caja IGV Neto`) la suma nominal es 0.0 y el **VP al Ke de hoy es
-309.79** S/ miles. Nominal cero no es VP cero, otra vez.

### San Martin no lo repercute, y ahi es un costo neto

`FC!28 IGV Operacion = -69,668,080.69`, **arriba** de `FC!40`, asi que baja el
CFADS que sirve la deuda; ademas se deduce en `Impuestos!21` y la variacion de
obra entra en `Nec_Fin!16` (183,377.14). Veinte anos de operacion, entre -3.21 y
-3.87 MM al ano, 2049 corto.

### Que hace el motor hoy

- **Rama al final de obra**: `motor_cajamarca.corrida` lleva la cadena del PPDI y
  de las compras de obra (obra, reembolso, fideicomiso, seguros) con credito
  acumulado y recuperacion a un mes, y **reproduce la fila del libro exacta**:
  VP al Ke **-309.7875** contra **-309.7875**. No lleva el IGV del PPDMO ni el de
  los costos de O&M, y no hace falta mientras se repercuta.
- **Rama por hitos**: al reves. `igv_op` es una **linea de costo de la plantilla**
  (`plantilla.py:223`), sin mecanica: el usuario escribe el numero.

### Lo que deberia ser

Una sola mecanica, con un **interruptor**: repercutido sobre el PPD, soportado
sobre CAPEX y OPEX, credito acumulado y recuperacion. Con el interruptor puesto
sale Cajamarca (neutro en caja); sin el, sale San Martin (costo neto que baja el
CFADS y la base imponible). **No es una constante del esquema de pago**, asi que
no puede colgar de "al final de obra" o "por hitos": es un campo propio.

### La razon del interruptor: la ley de la Amazonia, y lo que se hizo con ella

Oscar lo explico el 2026-09-16: *"Hay una diferencia entre Cajamarca y Tarapoto,
la Zona de Tarapoto esta afecta a la ley de la amazonia donde no se cobra IGV."*
No es una decision de modelacion, es un **dato de la zona del proyecto**.

Y el libro de San Martin lo dice con todas sus letras, en su propia hoja:

```
Opex!143  "IGV no recuperable (a costos)"   69,668,080.69
          = SUM(Opex!127:142), el IGV de los costos fijos por hito,
            de los variables por sistema, del fideicomiso y de los seguros
          = FC!28 IGV Operacion, exacto
```

Sin ventas gravadas no hay contra que acreditar el IGV soportado, asi que se va a
costo. Cajamarca no esta exonerada y por eso su hoja `IGV` tiene las tres filas de
IGV repercutido (`!71:73`) que absorben el soportado (`!74:77`).

**Implementado como un campo de `Proyecto`**, no como una variante del esquema de
pago: `Zona con exoneracion de IGV (ley de la Amazonia)`, 0 por defecto.

- `flujo_sm.py` (las dos ramas por hitos): con exoneracion, `igv_op` entra en
  `costo_om`; sin ella, se lava y no entra.
- `flujo_cajamarca.py` e `intangible_caj.py` (las dos ramas al final de obra):
  con exoneracion se agrega un costo de `IGV x (costo fijo + variable + gastos
  SPV + seguros + fianzas + fideicomiso)`, la misma base que `IGV!77` del libro;
  sin ella la linea vale cero.
- `generar_sm.correr` acepta `exonera_igv` para sobreescribir la plantilla, que
  es lo que usa `matriz._sm`, porque la plantilla trae Cajamarca en `Proyecto` y
  San Martin en `Hitos`.
- Las plantillas viejas, que no traen el campo, se leen como **exoneradas** en la
  rama por hitos, que es como venia comportandose `igv_op`, y como **no
  exoneradas** al final de obra, que es lo que hacia Cajamarca. Asi ninguna
  reproduccion cambia.

**Verificado.** Las cuatro combinaciones siguen cerrando con los mismos numeros de
antes: PPDI 46,362.15 y tarifa 3.8728067; tarifa 9.4608605 e intangible
324,200.32; PPDI 96,490,727.19 y referencia 5,452,029.7992; tarifa 31.109308 e
intangible 653,800,042.23. El proyecto inventado tambien cierra en las cuatro, y
los dos libros generados recalculados en LibreOffice no traen un solo `#VALUE!`.

Y el campo muerde, medido sobre el proyecto inventado:

```
                                   exonera=0    exonera=1     dif
al final de obra, cofinanciada      2.0930181    2.5849554  +23.50 %
al final de obra, autofinanciada   11.5352929   12.0061886   +4.08 %
por hitos, cofinanciada (ref)       1,474.9580   1,500.3721   +1.72 %
```

La tarifa variable del esquema al final de obra se mueve mucho porque es la
incognita del cierre y absorbe sola todo el costo: la pata fija es un
pass-through con margen.

---

## El control contra el libro de San Martin, a los parametros del libro

El escenario `libro` no es una aproximacion: con Ke 11.896982 %, Kd 10.5006 %,
WACC 9.9513 % y el **IPM del propio libro, 1.19 %** (`Control!C31`), el motor
reproduce el aprobado al centimo.

```
                        motor                libro
PPDI anual       97,607,149.9419      97,607,149.94
PPDMO referencia  5,683,476.2269       5,683,476.2269
precio unitario         3.782649            3.782649
interes operacion  -465,238,895.91    -465,238,895.91
amortizacion       -558,486,229.45    -558,486,229.45
vida media               8.836635            8.836635
```

Y no solo los totales: las trece filas de `Deuda Anual!23` y `!28` contra las del
motor dan un **desvio maximo de 0.003 soles**.

**Ojo con el IPM.** El libro reajusta al 1.19 % y el 2.67 % es el parametro que
Oscar fijo para proyectos nuevos, no lo que ese libro hace. Correr el preset del
libro al 2.67 % da referencia 5,542,869.89 (-2.47 %), precio 3.689068 (-2.47 %) e
interes de operacion -474,304,758 (+1.9 %). Medir un motor contra los totales del
libro corriendo a 2.67 % mezcla modelo con parametro.

**Para que sirve.** Cuando un motor reporta una desviacion contra el libro y corre
a otros parametros, esa desviacion no distingue entre una linea que falta y un
nivel de cierre. Este control si, porque aqui el residuo es cero por construccion.

### El PPDI se cierra con una igualdad, no con una tasa

```
Nec_Fin!21 Total necesidades               698,107,786.82
Nec_Fin!23 Total SIN CRSD                  667,916,062.66
Nec_Fin!24 VAN del total sin CRSD          519,739,073.65
Nec_Fin!25 Tasa de descuento mensual         0.7936944542 %  (WACC mensualizado)
```

**VAN(PPDI ; WACC mensual) = VAN(necesidades SIN CRSD ; WACC mensual)**, sobre las
60 cuotas trimestrales. Dos trampas: la **dotacion inicial de la CRSD se financia
pero no entra en ese VAN** (cerrar contra `!21` deja el PPDI 30,191,724 /
667,916,063 = **+4.52 %** alto), y la tasa es el **WACC**, no el Ke.

### Tres cifras de CAPEX de Cajamarca que se parecen y no son lo mismo

Medidas en la corrida del generador, las cuatro exactas contra el libro:

```
CAPEX de la plantilla, precios CONSTANTES   261,496.52
CAPEX corriente total                       278,511.04   = 'CAPEX proyecto'!D42
inversion con BANDERA DE OBRA               261,144.81   = Deuda!D13
deuda desembolsada (80 %)                   208,915.85   = Deuda!D15
```

**261,496.52 y 261,144.81 se parecen por casualidad**, se llevan 351.71, y son
cosas distintas: el total a precios constantes contra el subconjunto de obra a
precios corrientes. El indice implicito es `278,511.04 / 261,496.52 =
1.06506595` y se aplica **mes a mes sobre la malla**, no al total; sin indexar el
CAPEX entra **-6.11 %** bajo. Los 17,366.23 del expediente tecnico y la
supervision se restan de los 278,511.04, no de los 261,496.52.

**Los extras del servicio de construccion son cuatro lineas**, 5.20 % del CAPEX
corriente: fideicomiso 350.00, reembolso 8,437.11, estructuracion 4,178.32 y
comision por no uso 1,518.56, total 14,483.98. Seguros y garantias valen **cero
en Cajamarca**, pero son lineas propias de la plantilla, no cero estructural: en
otro proyecto aparecen. `278,511.04 + 14,483.98 = 292,995.02` = `PPDI!150`.

**No hay ninguna "cuña fiscal" del 2.5 % del CAPEX**, ni en los libros ni en el
motor (`grep` de `cuna`, `gfis` y `wedge`: cero resultados). El IGV de obra se
recupera, asi que lo que queda financiado es su **variacion neta** -- 183,377.14
en San Martin, `Nec_Fin!16` -- y no un porcentaje permanente del CAPEX.

### El calendario del PPDI: 60 cuotas iguales, al cierre del trimestre de OPERACION

```
San Martin (Cons_Trim!15:18)     Cajamarca (M.Sombra!9)
60 cuotas de 24,401,787.49       60 cuotas de 11,618.1366 S/ miles
todas iguales, max - min = 0.0   todas iguales, max - min = 0.0
primera  2030-03-31              primer devengo 2030-10-31
segunda  2030-06-30              primer cobro   2030-12-31
ultima   2044-12-31              ultimo cobro   2045-09-30
total 1,464,107,249.13           = 46,472.55 al ano, el PPDI del libro
```

**La convencion es la misma en los dos**: cobro vencido al cierre del primer
trimestre de operacion, y de ahi cada tres meses. Lo que cambia es el mes en que
arranca la operacion: San Martin en **enero**, asi que sus trimestres coinciden
con los calendario; Cajamarca en **octubre**, asi que van octubre-diciembre,
enero-marzo y asi.

**Anclar las cuotas a marzo/junio/septiembre/diciembre acierta en San Martin por
casualidad y se corre un trimestre en Cajamarca.** Sobre 60 cuotas descontadas al
WACC eso vale uno o dos puntos de anualidad.

Y el descuento es **mensual** (`Nec_Fin!25` = 0.7936944542 %, el WACC
mensualizado), con cada cuota puesta en su mes de cobro. Una tasa trimestral
equivalente sobre 60 flujos da otro numero, porque la primera cuota no cae a los
tres meses exactos del origen del descuento.

### Dos corridas defendibles, y no se pueden mezclar

1. **Reproduccion**: cada caso a los parametros de **su propio libro**, comparado
   contra su libro. Es la unica que mide modelo y no parametro.
2. **Escenario de hoy**: los dos casos a los **mismos parametros de hoy**,
   comparados entre si, no contra los libros.

Correr un caso al WACC de su libro y compararlo contra una corrida a parametros
de hoy mezcla las dos cosas, y la desviacion resultante no distingue una linea
que falta de un nivel de cierre.

### Medir contra el libro: parametros del libro, indice del libro

Oscar fijo el 2026-09-16 que Cajamarca y San Martin son las bases para aprender
como se trabaja, y que hay que recrearlos con la mayor precision para que el
generador sea valido. Eso zanja con que parametros se mide: **cada caso corre con
los de su propio libro** (WACC, Kd, Ke y su propio indice de reajuste,
1.1892506871 % Cajamarca, 1.19 % San Martin) y se compara contra el libro tal
como fue aprobado. El 2.67 % del contrato es para "Proyecto nuevo", que no
reproduce nada, cotiza.

Medido asi, el 2026-09-16, el residuo de este motor es cero en los dos casos:

```
Cajamarca (correr_desde_plantilla.py)  plantilla          libro      desvio
PPDI anual                          46,472.546555  46,472.546555  0.00000004
tarifa variable                          4.317669       4.317669  0.00000000
cuota de deuda mensual               2,692.275886   2,692.275886  0.00000000
interes total de la deuda          178,771.878203 178,771.878203  0.00000000
PPDMO fijo base mensual                555.985681     555.985681  0.00000000
PPDMO fijo y variable trimestrales, desvio maximo         0.00000001

San Martin (correr_generador_sm, escenario "libro", ipm 1.19 %)
PPDI 97,607,149.9419 / referencia 5,683,476.2269 / precio 3.782649, exactos,
y el perfil de deuda ano a ano a 0.003 soles.
```

**Un motor que reporta un desvio contra el libro corriendo a otros parametros no
distingue modelo de parametro.** Las patas del PPDMO se reajustan, asi que el
indice entra en la comparacion; el PPDI no se reajusta, asi que ese si se puede
comparar directo.

### El gatillo del 3 % vale 1.8 puntos de la pata variable

El precio del PPDMO de Cajamarca no sube suave. El libro acumula el IPM mensual y
libera el reajuste entero **solo el mes en que el acumulado cruza 3 %**
(`Inputs!D37`), lo trunca a 5 decimales y reinicia el acumulado (`PPDMO!16` y
`!18`). A 1.1893 % anual eso dispara cada dos anos y medio largo: el factor es
una escalera.

Aplicando el mismo IPM mes a mes, sin gatillo:

```
                        con gatillo (libro)   suave      desvio
factor mes 1 de O&M            1.000000     1.000986
factor ultimo mes              1.272210     1.297049
tarifa variable que cierra     4.3176690    4.2392550   -1.82 %
PPDMO variable ano 1          28,935.33    28,437.83    -1.72 %
PPDMO fijo ano 1               6,671.83     6,678.40    +0.10 %
```

**La firma es inconfundible: la variable se va casi dos puntos abajo y la fija no
se mueve.** Si un motor reporta eso, esta aplicando el indice suave.

Y Cajamarca indexa **ingresos y costos con indices distintos**: ingresos al IPM
1.1893 % con gatillo, costos al IPC de largo plazo 2.00 % (`Inputs!N23`, en
`'OPEX proyecto'!13`), sin gatillo. San Martin no hace esa distincion.

### La curva de la construccion y el cronograma por hitos

Oscar pidio el 2026-09-16 poder **seleccionar como se mueve la curva S en la
etapa de construccion** y un **cronograma que considere los hitos, con la forma
de la hoja `Inputs` de Cajamarca**. Medido antes de disenar nada, los dos pedidos
son una sola cosa.

**Ninguno de los dos libros usa una curva S.** En la ventana de obras mas puesta
en marcha:

```
                         Cajamarca (27 meses)   San Martin (29 meses)
CAPEX en la ventana       244,570.74 = 93.5%    522,934,773 = 94.2%
primer mes                    16.66%                 6.87%
mediana del gasto             mes 10 de 27          mes 12 de 29
mejor ajuste Beta(a,b)      (1.35 , 2.45)          (1.20 , 1.75)
error rms del ajuste           0.046                 0.026
```

Lo que hay en los dos es un **adelanto grande el primer mes de obra** y despues
mesetas planas que escalonan. En Cajamarca el primer mes de obra es 40,748.27
contra 5,933.98 de los cinco siguientes; en San Martin son dos meses de ~35.9 MM
contra ~13.7 MM de los tres siguientes. Y las dos son **adelantadas**, no
simetricas: a < b en las dos.

**Cuanto vale la curva.** Corriendo Cajamarca a los parametros de su libro y
cambiando solo el modo, PPDI anual contra la malla tipeada:

```
malla (el libro)         46,472.55
uniforme                 45,672.98   -1.72 %     tarifa variable +2.20 %
adelantada               46,250.14   -0.48 %                     +0.61 %
S simetrica              45,658.57   -1.75 %                     +2.24 %
atrasada                 45,083.63   -2.99 %                     +3.82 %
beta a=1.35 b=2.45       46,398.55   -0.16 %                     +0.20 %
adelantada + 16.66 %     46,471.41   -0.00 %                     +0.00 %
```

O sea que con el total del CAPEX, el cronograma y dos perillas se llega al PPDI
del libro **sin la malla mensual**, que es justo lo que hace falta en un proyecto
nuevo donde la malla todavia no existe.

**Lo que se agrego.** Hoja **`Cronograma`** con la forma de `Inputs!107:145`: una
fila por etapa con su mes de inicio y su mes de fin contados desde el cierre del
contrato. El mes `k` es el cierre del mes k-esimo de la malla, o sea
`fechas[k-1]`, y el mes 0 es la fecha de cierre; es la convencion del libro,
donde el mes 12 cae en 2027-09-30 con cierre en 2026-10-01. Las etapas **se
solapan** (la certificacion de obra corre dentro de la puesta en marcha), asi que
cada una trae su propio desde y hasta y no alcanza con una lista de duraciones.

Y en `Proyecto`, cuatro campos: `Curva de la construccion`
(`malla` | `uniforme` | `adelantada` | `S simetrica` | `atrasada` | `beta`),
`Parametro a de la curva`, `Parametro b de la curva` y `Desembolso inicial de
obra`.

**Ese campo NO se llama "adelanto de obra", y la razon importa.** Abriendo el
bulto del primer mes en los dos libros resulta que no es la misma cosa:

  - **Cajamarca si paga un adelanto**, y exacto: `'CAPEX proyecto'!21`, la linea
    de la planta de tratamiento, desembolsa **23,217.43 a precios constantes en
    el primer mes de obra sobre un total de linea de 116,087.17, o sea 20.0000 %
    clavado**. Y despues la planta **no factura nada durante cinco meses**:
    vuelve en enero de 2029, en dos mesetas de 8 y 4 meses.
  - **San Martin no paga ningun adelanto.** Su bulto son las `OBRAS
    PRELIMINARES` (`Capex!18` del hito 1 y `!122` del hito 4), una partida real
    de 29,287,212.48, el **5.27 % del CAPEX**, que se ejecuta entera en los dos
    primeros meses de obra y se termina.

Los dos se ven igual en la malla y son cosas distintas: uno es un pago
anticipado contra una partida que despues se detiene, el otro es una partida que
de verdad se ejecuta al principio. Por eso el campo describe la **forma**, que es
lo unico comun: cuanto del CAPEX de la ventana de obra cae entero en su primer
mes. El 16.66 % que reproduce el PPDI de Cajamarca es esa forma, no su contrato.

**`malla` es el valor por defecto y el unico modo que reproduce los libros al
centimo**, verificado: con la plantilla regenerada, `correr_desde_plantilla` da
los mismos ceros de antes contra Cajamarca. La curva redistribuye **solo** el
CAPEX que cae dentro de la ventana de obra y no toca nada fuera de ella, asi que
los estudios tecnicos y la supervision se quedan donde el cronograma los pone.

**Trampa que esto introduce, y su antidoto.** El `Cronograma` MANDA sobre las
fechas sueltas de `Proyecto`, para las etapas que define. Una plantilla nueva que
herede el `Cronograma` de Cajamarca corre el calendario del libro aprobado con
los montos del proyecto nuevo, que es exactamente la trampa de siempre. Por eso
todo escritor de plantillas tiene que llamar a `plantilla.volcar_cronograma`, que
reescribe la hoja desde las fechas del proyecto y **vacia** las etapas que esas
fechas no determinan. `proyecto_ficticio` ya lo hace, y se verifico que corre su
propio calendario (cierre 2027-01-31, obras 2028-04-30, concesion hasta
2051-03-31) y que las cuatro combinaciones siguen cerrando en VAN cero.

### El reparto de la tarifa: cuanto repaga la inversion y cuanto paga la operacion

Oscar lo pidio el 2026-09-16: *"aun siendo autofinanciada se debe proyectar la
necesidad de flujos recaudados por tarifa para que se logre el VAN 0 y estos
flujos tambien deben discriminarse de cuanto va para repagar la inversion y
cuanto para la operacion y mantenimiento. Finalmente en los proyectos
cofinanciados solo se cofinancia el CAPEX via PPDI y el PPDMO se paga con la
tarifa."*

**Lo tercero lo confirma el propio libro de Cajamarca, por su nombre.** La celda
`Resumen!J6` se llama `Tarifa_Media_Vta` en los nombres definidos del libro, y su
valor es 0.004318 S/ miles por kg DBO5, o sea **4.317669 S/ por kg**, que es
exactamente el precio unitario de la pata variable del PPDMO. El libro
cofinanciado ya llama tarifa media de venta a lo que cobra el PPDMO.

**El reparto es exacto y no tiene nada de convencional.** De cada periodo, lo que
se lleva la operacion es su costo de caja, supervision del regulador incluida, y
lo que queda repaga la inversion: servicio de deuda, impuestos y el remanente
del flujo de caja financiero. Las dos partes suman el ingreso por construccion, asi que el libro lo
puede mostrar con un check que da cero.

**Y contrastado contra las dos ramas, el motor ya lo hacia: solo faltaba
mostrarlo.** Es la misma particion que en la rama cofinanciada hacen el PPDMO y
el PPDI:

```
                          cofinanciada     autofinanciada    diferencia
Cajamarca, VAN a cobrar     393,021.32        396,606.08       +0.91 %
  operacion y mantenimiento 166,092.35        166,135.84       +0.03 %
  inversion                 226,928.97        230,470.23       +1.56 %

San Martin, VAN a cobrar  792,166,105.02    787,015,432.07     -0.65 %
  operacion y mantenimiento 313,663,395.75    313,663,395.75    0.00 %
  inversion                 478,502,709.27    473,352,036.32   -1.08 %
```

**Cuidado con esa fila: es el COSTO en las dos columnas, no el PPDMO.** Rotularla
"operacion" en las dos hizo que el hilo del tablero la leyera como el PPDMO y
reportara una discrepancia que no existe. El PPDMO de Cajamarca vale 194,333.51
de VAN contra 166,092.35 de costo: lleva 28,241.16 de margen, 17.0 %.

En San Martin la pata de O&M coincide **al centimo** entre los dos regimenes, y
en Cajamarca a 0.03 %. Toda la diferencia entre regimenes esta en la pata de
inversion, que es donde estan los intereses capitalizados y el escudo fiscal del
intangible, exactamente donde tiene que estar. La pata de inversion cofinanciada
de arriba es el PPDI mas el margen del PPDMO (194,333.51 - 166,092.35 =
28,241.16 en Cajamarca), porque ese margen tampoco paga costos.

**Lo que se agrego**: una hoja `Reparto de la tarifa` en los dos libros
autofinanciados, el del esquema al final de obra y el de hitos, con el ingreso,
el O&M, lo disponible para la inversion, las tres tarifas unitarias, los tres VAN
y el check de que las dos partes suman el total. Y en el `Resumen` del libro al
final de obra, la tarifa partida en sus dos componentes: de los 9.4608605 S/ por
kg de Cajamarca, **3.9630961 pagan la operacion y 5.4977643 repagan la
inversion**. Verificado recalculando los dos libros en LibreOffice: el check da
OK y las cifras calzan con las del motor.

**Oscar lo decidio el 2026-09-16: "va con margen".** La pata de operacion es lo
que se le paga al operador por operar, no lo que cuesta. El factor es el `Margen
del costo fijo` de la plantilla aplicado a **todo** el costo de O&M, porque en la
rama autofinanciada no hay pata fija y pata variable que separar: el operador
opera el servicio entero. Las variantes medidas sobre Cajamarca, VAN al Ke:

```
costo puro                            166,135.84   41.89 % / 58.11 %
+ 15 % sobre el costo fijo            173,306.52   43.70 % / 56.30 %
+ 15 % sobre todo el costo            191,056.22   48.17 % / 51.83 %   <- la del libro
factor del gemelo cofinanciado        194,384.40   49.01 % / 50.99 %
```

**La ultima esta MAL, y se probo antes de descartarla.** Es tentadora porque en
el gemelo cofinanciado el pago al operador existe y tiene nombre, pero el PPDMO
de Cajamarca **no se descompone en costo mas margen**: ese 17.00 % netea cuatro
cosas, y que caiga cerca del 15 % son errores que se compensan.

Medida en VAN al Ke, la pata FIJA vale **0.7685 veces su costo** y la VARIABLE
**1.6064 veces** la suya. La fija se reconstruye entera:

```
la base fija es el promedio de los fijos SIN reposiciones por 1.15
  (`leer_plantilla.py:249`, lista `FIJOS_PPDMO`, `Costos!38`), y las
  reposiciones valen 2,134.45 al ano, 36.83 % de esa base y 26.92 %
  del costo fijo con reposiciones: costo real que la pata no cobra
        1.15 x 5,795.88 / (5,795.88 + 2,134.45)              = 0.8405
el ingreso se reajusta al IPM 1.1893 % y el costo al IPC 2.00 %,
  lo que en VAN al Ke vale                                   = 0.9418
```

**Cuidado con llevar esa razon a un numero medido: se mueve con la base de
precios que se le ponga al costo.** La pata fija arranca de precios constantes de
Dic-2025 mas un mes de IPM, mientras el indice de costos del libro **no arranca
en 1 sino en 1.0986** al inicio de la operacion. Puestas las dos series sobre el
mismo ancla de descuento, la pata fija da 0.9459 veces su costo estrecho, 0.8226
veces ese costo con el 15 % encima y 0.6913 veces el costo fijo entero; corriendo
el costo al mismo punto de partida que la pata, sube a ~0.90. **Ninguna de esas
razones es un dato del libro**, son razones entre dos series que el libro nunca
divide. Lo que si es dato es que **la pata fija escala con el indice de INGRESOS**
(`sombra_cajamarca.pagos`: `fijo_m = fijo_base * f18[m]`, el mismo `f18` =
`PPDMO!18`, IPM con gatillo, que multiplica la variable), no con el IPC de
costos, asi que el 15 % de margen se erosiona en terminos reales a lo largo de
los 25 anos.

El 60.6 % que lleva encima la variable es el **cierre**: esa pata absorbe lo que
el PPDI no recupera. Asi que el factor del gemelo suma +15 % de margen, menos las
reposiciones que quedan fuera de la base, menos el desfase de indices, mas el
cierre entero. Por lo mismo 17.00 % contra 21.54 % de San Martin no mide "el
retorno": San Martin cierra el PPDMO con otro mecanismo, una sola incognita que
escala la pata fija y el precio unitario a la vez. Sacar el factor de ahi mete el
cierre de un regimen dentro de la respuesta del otro y llama "operacion" a parte
de la recuperacion de la inversion cofinanciada. **El margen del operador es un
dato del OPERADOR, no de como se financio la obra.**

Resultado: Cajamarca **48.17 / 51.83**, San Martin **45.83 / 54.17**, con el
margen en 15 %. Los dos libros verificados recalculando en LibreOffice, con el
check del reparto en OK.

## Una biseccion sin guarda devuelve el borde disfrazado de cierre (2026-09-16)

Los tres cierres del motor son bisecciones: `motor_cajamarca.cerrar` (el PPDI),
`sombra_cajamarca.cerrar` (la tarifa variable) y `motor_ppdmo_sm.cerrar` (la
referencia de San Martin). Ninguna comprobaba que el VAN cambiara de signo en el
intervalo. Si la incognita se pega a un extremo, lo que sale **no es un cierre,
es el borde**, y con dos insumos bien distintos puede dar el mismo pago al
centimo. El aviso vino del hilo del tablero, que lo vio probando reposiciones
fuera de rango.

Las tres llevan ahora la misma guarda, agnostica de la direccion, porque el VAN
crece con la incognita en un motor y decrece en otro:

```python
f = lambda m: ...
if f(lo) * f(hi) > 0:
    raise ValueError(...)
```

Dentro del rango util no cambia nada: las cuatro combinaciones de `matriz.py`
siguen cerrando en 0.00000000 con los mismos resultados, la tarifa de Cajamarca
sigue dando 4.31766897 contra el libro, y el proyecto ficticio corre las cuatro.
Fuera de rango revienta con el intervalo y los dos VAN en el mensaje, en vez de
devolver un numero razonable y falso.

## La forma real del O&M de Cajamarca, ano por ano (2026-09-16)

Los CSV exportados de este directorio van con **saltos LF**. `csv.writer` de
Python termina linea en `\r\n` por defecto, y los seis se escribieron asi al
principio: la ultima columna se lee `nombre\r` y da NaN al parsear sin limpiar.
Si se regenera alguno, pasar `lineterminator="\n"` o convertirlo despues.

Exportada a `caj_opex_anual.csv` con `leer_plantilla`, a precios constantes de
Dic-2025 y con el indice de costos aparte. Contra la idea de que la serie es
grumosa, **no lo es**:

```
fijo, reposiciones incluidas   7,930.33   PLANO los 25 anos
gastos de la SPV               1,782.00   PLANO
variable                      14,984.55 -> 18,678.51   +0.9224 % real anual
total                         24,696.88 -> 28,390.84   +0.5825 % real anual
```

Solo la pata variable se mueve, porque sigue al caudal, con un escalon en 2037.
Las reposiciones estan **dentro** del fijo y niveladas (`Reposiciones!L88`), no
son un cronograma como en San Martin.

El indice de costos arranca en **1.09863** y queda plano hasta 2030, despues corre
al IPC 2.00 %: los precios son de Dic-2025 y la operacion empieza en Oct-2030.
Esa base distinta de 1 es la que hace que cualquier razon entre la pata fija y su
costo dependa de donde se la mida.

**Las fianzas, seguros y fideicomiso de la operacion NO estan en el O&M**: viven
en el bloque `Otros` de operacion, que es costo del flujo de caja financiero y no
entra al activo del PPDI. Una serie de O&M que cae en 2032-2033 tiene `Otros`
mezclado adentro, y eso mueve impuestos y cobertura sin deber hacerlo.

## El rezago del PPDMO vive en la FILA, no en el exponente (2026-09-16)

`sombra_cajamarca.descuento` da al trimestre `i` el factor de **su propio cierre**,
`3*(i+1)` meses al Ke mensual, contados desde el mes 1 de la malla, que es
**2026-10-31**, el cierre del contrato, no el inicio de la operacion. El rezago de
un trimestre no esta ahi: esta en la serie, que arranca un trimestre tarde.

```
trimestre 16   2030-10-31 .. 2030-12-31   exponente 51   fijo 0.00      var 0.00
trimestre 17   2031-01-31 .. 2031-03-31   exponente 54   fijo 1,667.96  var 7,233.83
```

La operacion empieza el 2030-09-30, o sea que el primer trimestre de operacion es
Oct-Dic 2030 y **el PPDMO ahi es cero**.

**La trampa**: quien trabaje con la serie SIN correr necesita el exponente
`3*(i+2)` para llegar al mismo valor presente, y quien la tenga corrida necesita
`3*(i+1)`. Hacer las dos cosas mete un trimestre de mas, que al Ke de Cajamarca
(12.8969 %) **vale 3.08 %**, mas que cualquier desvio que se este persiguiendo.

Que el exponente es ese no descansa en calibrar nada: son los mismos factores con
los que `S.cerrar` cierra la tarifa en **4.31766897**, el valor del libro. Con el
exponente corrido un trimestre no cerraria ahi.

## El "ano 1" del libro son dos cosas, y la pata fija no las distingue (2026-09-16)

`Resumen` arma las tres cifras del ano 1 con MINIFS sobre la serie mensual por 12,
o sea **el primer mes de operacion anualizado**, no la suma del ano calendario.
Las dos convenciones dan lo mismo en la pata fija y casi un punto distinto en la
variable, porque el volumen crece dentro del ano y el pago fijo no:

```
                 Resumen (1er mes x12)   ano calendario 2031   diferencia
PPDMO fijo             6,671.8282             6,671.83          +0.0000 %
PPDMO variable        28,935.3250            29,219.07          +0.9806 %
```

**La trampa**: la pata fija es la regla natural para calibrar ventanas y
exponentes, porque es una serie de indice pura sobre una base verificada. Pero es
**ciega a esta convencion**, asi que se puede calibrar con ella, quedar en cero, y
seguir leyendo +0.98 % de convencion en la variable sin ninguna senal de que algo
esta mal. Cualquier lectura del ano 1 de la pata variable tiene que decir contra
cual de las dos se compara.

La serie anual completa del PPDMO devengado del libro quedo exportada en
`caj_ppdmo_anual.csv`, 2031 a 2052. Su crecimiento **no es suave**: va entre
+0.84 % y +4.17 % por el gatillo del 3 %, con promedio 2.34 %. Comparar un modelo
de crecimiento constante contra un ano suelto de esa escalera no mide nada.

## Ajustar un crecimiento contra un VAN deja el nivel suelto (2026-09-16)

Una tasa de crecimiento del O&M ajustada para reproducir el **valor presente** de
la serie del libro no queda determinada: nivel y crecimiento entran juntos, y hay
infinitos pares que dan el mismo VAN. Un crecimiento bajo con el ano 1 alto y uno
alto con el ano 1 bajo son indistinguibles por VAN, y **muy distintos en el ano 1**,
que es donde se leen la mayoria de los desvios.

Sobre la serie real de Cajamarca, O&M total a precios constantes, 25 anos,
descontando al Ke, anclando siempre el ano 1 en el del libro (24,696.88):

```
punta a punta                     +0.5825 %
equivalente en VALOR PRESENTE     +0.6631 %
VAN de la serie real             219,102.52 S/ miles
con g = 0.38 %                   214,573.03   -2.0673 %
con g = 0.58 %                   217,757.82   -0.6137 %
con g = 0.6631 %                 219,102.52    0.0000 %
```

Las dos tasas no son la misma medida: **punta a punta no conserva el VAN**, asi que
no se sustituye una por la otra. Y un motor que ajusto el crecimiento contra el VAN
y llego a 0.38 % esta necesariamente **2 % arriba en el ano 1**, aunque su VAN
coincida dentro de medio punto. La forma correcta de fijarlo es anclar el ano 1 en
el del libro y poner el crecimiento equivalente, no mover la tasa sola.
