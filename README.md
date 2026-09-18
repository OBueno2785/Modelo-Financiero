# Modelo financiero de APP — generador de pagos

Genera el modelo financiero de una Asociación Público Privada a partir del CAPEX,
el OPEX y el cronograma de un proyecto nuevo, y calcula los pagos: el **PPDI**
(inversión) y el **PPDMO** (operación y mantenimiento), con la misma información
que entregan los modelos ya aprobados.

El motor está escrito en Python, sin Excel y sin Buscar Objetivo. Escribe un libro
de salida con fórmulas vivas: resumen, malla completa, flujo de caja, estados
financieros proyectados y CTI.

## Qué cubre

Cuatro combinaciones, todas cerrando:

|                      | Pago al final de obra   | Pago por hitos funcionales        |
|----------------------|-------------------------|-----------------------------------|
| **Cofinanciada**     | `generar.correr`        | `generar_sm.correr`               |
| **Autofinanciada**   | `generar.correr_auto`   | `generar_sm.correr(regimen=...)`  |

`matriz.py` las corre las cuatro de una pasada y sirve de control: si una deja de
cerrar, se ve ahí.

Los dos regímenes de la CINIIF 12 están modelados: la cofinanciada como **activo
financiero** (interés efectivo a la TIR de sus propios flujos) y la autofinanciada
como **activo intangible** (cierra contra la tarifa, con el interés de construcción
capitalizado).

## Cómo correrlo

```
pip install -r requirements.txt
python matriz.py                  # las cuatro combinaciones
python generar.py                 # proyecto nuevo, pago al final de obra
python generar_sm.py              # proyecto nuevo, pago por hitos
```

La entrada es `Plantilla_Proyecto_Nuevo.xlsx`: hojas `Proyecto` (fechas, esquema de
pago, financiamiento, tributos), `CAPEX` (malla mensual), `OPEX` (costos por año de
concesión, fijos y variables) y `Otros`. **Todo a precios constantes**: el reajuste
por IPM y por IPC lo pone el motor, no quien llena la plantilla. Viene precargada
con un caso real para que se vea la forma esperada.

## Qué hay acá

- **Motor y cierres**: `motor_cajamarca.py`, `motor_sanmartin.py`, `motor_ppdmo_sm.py`,
  `sombra_cajamarca.py`, `intangible_caj.py`, `activo_financiero.py`, `deuda_cajamarca.py`,
  `capital_trabajo.py`, `tributos_*.py`, `ipm_*.py`, `calendario_*.py`.
- **Entrada y salida**: `plantilla.py` y `leer_plantilla.py` (la plantilla),
  `escribir_excel.py` y `escribir_excel_sm.py` (el libro de salida), `eeff.py`
  (estados financieros proyectados), `cti.py` (Costo Total de la Inversión),
  `malla_obra.py` (la malla mensual de obra por ventanas de partida).
- **Controles**: `proyecto_ficticio.py` arma un proyecto inventado de punta a punta,
  que es como se prueba el generador; los modelos aprobados no son un banco de
  pruebas. `validar_caj_var.py` y `VALIDACION_cierre_variable_cajamarca.md` documentan
  la validación del cierre de la tarifa variable.
- **Series exportadas** (`.csv` y `.json`): las primitivas y los resultados intermedios
  ya extraídos, para que nadie los vuelva a armar a mano.
- **Libros generados** (`PTAR_*.xlsx`): la salida del motor, incluida la del proyecto
  ficticio de control.
- **`fuentes/`**: datos de mercado en caché — betas de Damodaran, curva cupón cero de
  la SBS y el cuadro del MMM 2027–2030 del MEF, cada uno con su fecha y su fuente
  declaradas dentro del archivo.
- **`normas/`**: las NIIF y CINIIF en PDF y en texto plano, tal como las publica el
  organismo, subidas a pedido de Oscar el 18-set-2026. Son la referencia contable del
  modelo, sobre todo la CINIIF 12, que define los dos regímenes.
- **`LEEME.md`**: el registro completo del trabajo, entrada por entrada, con lo que se
  midió, lo que falló y por qué. Es la referencia larga; este README es sólo la puerta.

## Qué NO está en este repositorio

- **Los dos modelos aprobados** (`MODEF_PTAR_Cajamarca.xlsm` y
  `Modelo_Hitos_Funcionales.xlsm`). Son modelos oficiales de terceros y no son obra de
  este proyecto. Varios scripts los leen desde el mismo directorio
  (`extraer_primitivos.py`, `extract_sm.py`): para esos hay que poner el archivo al
  lado. Las series que de ahí salen ya están exportadas en los `.json` del repositorio,
  así que el motor corre sin ellos.

## Una limitación conocida

Dieciséis módulos abren sus archivos con la ruta absoluta
`/mnt/project-files/generador/...`, que es donde vive hoy el proyecto. Clonado en otro
directorio, esos módulos no encuentran sus datos hasta que la ruta se parametrice.
