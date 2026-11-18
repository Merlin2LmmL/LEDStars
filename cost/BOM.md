# Bill of materials and cost

Everything needed to build 10 LEDStar boards. The components come from LCSC, the PCBs from JLCPCB and the solder paste
from AliExpress. JLCPCB's Economic assembly wasn't available for this board (see the [journal](../JOURNAL.md)), so the
boards are assembled by hand. The parts list is also available as a spreadsheet: [`BOM.csv`](BOM.csv).

## Parts (per board and for 10 boards)

| Refs | What | MPN | LCSC | Per board | ×10 | Unit $ | ×10 $ |
|---|---|---|---|---|---|---|---|
| U1 | Microcontroller, RISC-V, TSSOP-20 | CH32V003F4P6 | [C5187096](https://www.lcsc.com/product-detail/C5187096.html) | 1 | 10 | 0.3085 | 3.08 |
| BT1 | CR2032 battery holder, SMD | BS-10-B2AA010 | [C964798](https://www.lcsc.com/product-detail/C964798.html) | 1 | 10 | 0.4598 | 4.60 |
| D1, D5, D9, D13, D17 | White LED, reverse-mount 1206 | XL-3216UWC-FB | [C3646935](https://www.lcsc.com/product-detail/C3646935.html) | 5 | 50 | 0.0165 | 0.83 |
| D21, D22, D23, D24, D25 | Yellow LED, reverse-mount 1206 | XL-3216UYC-FB | [C3646939](https://www.lcsc.com/product-detail/C3646939.html) | 5 | 50 | 0.0159 | 0.80 |
| D2, D6, D10, D14, D18 | Red LED, reverse-mount 1206 | XL-3216SURC-FB | [C3646938](https://www.lcsc.com/product-detail/C3646938.html) | 5 | 50 | 0.0105 | 0.53 |
| D3, D7, D11, D15, D19 | Green LED, reverse-mount 1206 | XL-3216UGC-FB | [C3646937](https://www.lcsc.com/product-detail/C3646937.html) | 5 | 50 | 0.0101 | 0.51 |
| D4, D8, D12, D16, D20 | Blue LED, reverse-mount 1206 | XL-3216UBC-FB | [C3646941](https://www.lcsc.com/product-detail/C3646941.html) | 5 | 50 | 0.0146 | 0.73 |
| SW2 | 3-position slide switch (ON / OFF / CLOCK) | MSK13C02 | [C2681567](https://www.lcsc.com/product-detail/C2681567.html) | 1 | 10 | 0.1169 | 1.17 |
| SW1 | Tactile button (mode), 3x4 mm | HX 3x4x2-2P-1.6N TACTILE SWITCH | [C49234124](https://www.lcsc.com/product-detail/C49234124.html) | 1 | 10 | 0.0254 | 0.25 |
| D26 | Schottky diode 40 V 1 A (CLOCK position power) | B5819W SL | [C8598](https://www.lcsc.com/product-detail/C8598.html) | 1 | 10 | 0.0262 | 0.26 |
| C1 | 100 nF 50 V X7R 0603 capacitor (Samsung, replaces the out-of-stock Yageo C14663) | CL10B104KB8NNNC | [C1591](https://www.lcsc.com/product-detail/C1591.html) | 1 | 10 | 0.0071 | 0.07 |
| R1, R4 | 22 Ω 0603 resistor | 0603WAF220JT5E | [C23345](https://www.lcsc.com/product-detail/C23345.html) | 2 | 20 | 0.0017 | 0.03 |
| R3 | 100 Ω 0603 resistor | 0603WAF1000T5E | [C22775](https://www.lcsc.com/product-detail/C22775.html) | 1 | 10 | 0.0023 | 0.02 |
| R2, R5 | 330 Ω 0603 resistor | 0603WAF3300T5E | [C23138](https://www.lcsc.com/product-detail/C23138.html) | 2 | 20 | 0.0020 | 0.04 |
| R6 | 1 kΩ 0603 resistor | 0603WAF1001T5E | [C21190](https://www.lcsc.com/product-detail/C21190.html) | 1 | 10 | 0.0017 | 0.02 |

`J1` (the three SWIO programming pads) is just copper on the board, there is nothing to buy for it.

Unit prices in the table are single-piece catalogue prices and only a rough guide. The carts below have the real prices.
Adding up the ×10 column gives about $12.95.

## Total cost

The three orders, with screenshots of each cart (the shipping address and account name are blacked out).

| Order | What | Items | Shipping and fees | Total |
|---|---|---|---|---|
| [LCSC](LCSC_cart.png) | all the components | $13.81 (after a $0.41 discount) | $10.97 shipping + $3 handling | **$27.37** |
| [JLCPCB](JLCPCB_cart.png) | 10 PCBs, white, 1.6 mm, OSP | $15.00 | $14.61 shipping (estimate) | **$29.61** |
| [AliExpress](Aliexpress_cart.png) | solder paste (Sn99Ag0.3Cu0.7) and flux | €11.19 | free shipping, €5.95 import duties | **€17.14** |

The total is **$56.98 + €17.14**, which is about $5.70 + €1.71 per board. At roughly 0.9 € per dollar (the real rate
will differ) that is about **€68 in total, or €6.80 per board**.

Notes:
- **Shipping:** shipping and fees are about half of both the LCSC and the JLCPCB total. The JLCPCB shipping is the estimate for this order alone and can be lower if it ships together with another order.
- **Currency:** the JLCPCB cart is in dollars, so the PCBs cost $15.00.
- **Capacitor:** the Yageo `C14663` from the schematic was out of stock at LCSC in small quantities, so the order uses the Samsung `C1591` (100 nF, 50 V, X7R, 0603) instead. The footprint is the same.
