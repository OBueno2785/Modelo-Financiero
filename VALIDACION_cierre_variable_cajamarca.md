# Validación de `cerrar_caj_var.py` (cierre de la tarifa variable de Cajamarca)

Revisado el 2026-09-14 contra `MODEF_PTAR_Cajamarca.xlsm`, hoja `M.Sombra`.
Script de contraste: `validar_caj_var.py`.

## Veredicto

**El método es válido** como aproximación mientras no exista el modelo sombra
propio. Reescalar los flujos en caché es legítimo aquí porque la tarifa variable
toca muy pocas líneas del flujo, y las verifiqué una por una.

## Lo que se comprobó bien

1. **La extracción es fiel.** El VAN de los flujos en caché descontados al Ke del
   propio libro da −0.000000. Reproduce el cierre del libro.
2. **El factor de descuento replica `M.Sombra!D77`**, incluido el `IF(D76>0,1,0)`
   que anula los trimestres no vivos.
3. **`inte` son intereses y nada más**: suma 178 771.878, que es exactamente la
   primitiva `gastos_fin` de `motor_cajamarca.py`, separada de amortización y
   servicio.
4. **τ = 0.05 + 0.295 × 0.95 = 0.33025** está bien construido, y las dos patas
   —participación de trabajadores (`M.Sombra!21`) e Impuesto a la Renta
   (`M.Sombra!22`)— comparten el mismo calendario anual, así que un solo factor
   las cubre.
5. **Ninguna otra línea del flujo responde a la tarifa variable**, y esto era lo
   que había que descartar:
   - `Deducciones (DINS)` (`M.Sombra!12`) es **cero en toda la concesión**
     (`'Concepto de Pago'!T35 × Resumen!$J$14`): el libro no modela penalidades.
   - `Flujo de caja IGV Neto` (`M.Sombra!26` = `IGV!83`) sí depende del ingreso
     variable por `IGV!73`, pero es **cero en todos los trimestres con ingreso
     variable**: el crédito fiscal ya está agotado cuando empieza la operación.
   - `Efecto ITAN` (`M.Sombra!23`) **suma cero**: paga y recupera, es puro calce.
   - Servicio de deuda y CAPEX no dependen del ingreso.

## Los dos refinamientos, ambos inmateriales

| Escenario | k | Tarifa | PPDMO variable anual | vs libro |
|---|---|---|---|---|
| Original del tablero | 1.028175 | 0.0044393 | 29 750.57 | +2.82 % |
| + IR con su desfase anual real | 1.027430 | 0.0044361 | 29 729.03 | +2.74 % |
| + delta de PPDI gravado igual que el resto | 1.027239 | 0.0044353 | 29 723.49 | +2.72 % |

El script aplica `(1 − τ)` en el mismo trimestre del ingreso, pero el libro carga
el IR una vez al año: 21 cargos espaciados exactamente 4 trimestres, el primero
en el índice 24, cuando el ingreso variable empieza en el 17. Son 7 trimestres y
51 361.94 S/ miles de ingreso que corren antes del primer cargo. Adelantar el
impuesto sobrestima su valor presente y por tanto el k. El efecto son 27 S/ miles
al año, 0.09 %. **No amerita cambiar el número publicado.**

## El error que sí importa: la banda

La pata de "intereses congelados" quedó emparejada con `PPDI_N = 46 457.92`, que
es el PPDI del escenario **opuesto**. En `cajamarca_actualizado.json` los dos
valores son las dos caras de la misma disyuntiva:

- gastos financieros escalados por Kd_nuevo/Kd_libro → PPDI 46 457.92
- gastos financieros congelados en el valor del libro → PPDI 47 008.30

Emparejado como corresponde, el escenario de intereses congelados da
**k = 0.964177 → tarifa 0.0041630 → 27 898.77 S/ miles al año, −3.58 %**, no
−1.44 %.

**Banda corregida: −3.6 % a +2.7 %, es decir 27 899 a 29 723 S/ miles al año**,
contra 28 935.33 del libro. Es más ancha que la reportada y está centrada más
abajo.

## Lo que la banda realmente mide

No mide incertidumbre de mercado: mide que **Cajamarca no tiene módulo de deuda**
y sus gastos financieros siguen entrando como primitiva del libro. Con Kd subiendo
de 9.2888 % a 10.0930 %, un dimensionamiento real por cobertura reduciría la deuda
en lugar de dejar el saldo fijo, así que el extremo "escalado" sobrestima el alza
de intereses y el "congelado" la ignora. La verdad está dentro, y la forma de
cerrarla es construir el módulo, no afinar el reescalado.
