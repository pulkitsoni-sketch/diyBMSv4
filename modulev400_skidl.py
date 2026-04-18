"""
modulev400_skidl.py  —  DIYBMS Cell Monitoring Module v4.00
============================================================
SKiDL script to regenerate the KiCad netlist and grouped BOM for the
diyBMS v4 cell monitoring module (Stuart Pittaway, rev 4, 2019-04-30).

Hardware overview:
  Cell voltage  : Up to ~5 V (LiPo / LFP)
  Balancing     : 8 × 2R2 1W dump resistors (two parallel chains of 4)
                  switched by N-MOSFET Q1 (IRLML6244)
  Voltage ref   : LM4040 2.048 V shunt (D1) on 2_VOLT rail
  MCU           : ATtiny841-SSU (SOIC-14)
  Comms TX      : HMHA2801 optocoupler (U1) isolating USART0 TX
  Comms RX      : Direct UART RX via R16 pull-down
  Temperature   : NTC thermistor R19 (47K) + R20 divider; external SENSOR1 header
  LEDs          : D2 Blue (TXD1 activity), D3 Red (dump active), D4 Green (ISP/PA5)

Schematic source : circuit.pdf  (KiCad 5.1.0, v4.sch)
BOM source       : CellModules_LCSC_BillOfMaterials.xlsx
Netlist source   : v4.net

Usage:
    python modulev400_skidl.py
Outputs:
    modulev400.net          — KiCad-compatible netlist
    modulev400_BOM.csv      — grouped Bill of Materials
"""

import os
import csv
from collections import defaultdict


# =============================================================================
# 1.  SETUP & PATHS  (edit to match your KiCad installation)
# =============================================================================
app_symbols    = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
app_footprints = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
user_config    = '/Users/user/Documents/KiCad/9.0'

os.environ['KICAD_SYMBOL_DIR']  = app_symbols
os.environ['KICAD6_SYMBOL_DIR'] = app_symbols
os.environ['KICAD7_SYMBOL_DIR'] = app_symbols
os.environ['KICAD8_SYMBOL_DIR'] = app_symbols
os.environ['KICAD9_SYMBOL_DIR'] = app_symbols

os.environ['KICAD_FOOTPRINT_DIR']  = app_footprints
os.environ['KICAD8_FOOTPRINT_DIR'] = app_footprints

from skidl import *  # noqa: E402

lib_search_paths[KICAD].extend([app_symbols, user_config])
footprint_search_paths[KICAD].append(app_footprints)
set_default_tool(KICAD)


# =============================================================================
# 2.  GLOBAL / POWER RAIL NETS
# =============================================================================
gnd  = Net('GND')
vcc  = Net('VCC')          # Cell positive terminal = module supply


# =============================================================================
# 3.  SIGNAL NETS  (names match v4.net labels exactly)
# =============================================================================
two_volt          = Net('2_VOLT')            # LM4040 2.048 V reference output
enable            = Net('ENABLE')            # Cell voltage measurement node (ADC chain top)
txd0              = Net('TXD0')              # ATtiny841 USART0 TX → U1 optocoupler
rxd0              = Net('RXD0')              # ATtiny841 USART0 RX ← RX1 connector
txd1              = Net('TXD1')              # ATtiny841 PA6 (USART1 TX / Blue LED)
rxd1              = Net('RXD1')              # ATtiny841 PA7 (ADC / temp divider mid)
dump_load_enable  = Net('DUMP_LOAD_ENABLE')  # PB3 → Q1 gate (dump load control)

net_d4_a     = Net('Net-(D4-Pad2)')    # PA5 / J2-MOSI / D4 anode
net_d4_k     = Net('Net-(D4-Pad1)')    # D4 cathode / R18 pin 2
net_d3_k     = Net('Net-(D3-Pad1)')    # D3 cathode / R17 pin 2
net_d2_k     = Net('Net-(D2-Pad1)')    # D2 cathode / R23 pin 2
net_q1_gate  = Net('Net-(C3-Pad1)')    # Q1 gate / R14 / R15 / C3
net_q1_drain = Net('Net-(Q1-Pad3)')    # Q1 drain / dump load bottom / R17 / R22
net_r3_mid   = Net('Net-(R3-Pad2)')    # Voltage divider mid-point: R3[2]/R4[1]/PA3
net_r5_opto  = Net('Net-(R5-Pad1)')    # R5 / U1 anode
net_r21_ref  = Net('Net-(R21-Pad1)')   # PA0 / R21 / SENSOR1 pin1
net_sensor3  = Net('Net-(SENSOR1-Pad3)')  # PA1 / SENSOR1 pin3
net_tx1_e    = Net('Net-(TX1-Pad1)')   # U1 emitter / TX1 pin1
net_tx1_c    = Net('Net-(TX1-Pad2)')   # U1 collector / TX1 pin2
net_j2_rst   = Net('Net-(J2-Pad5)')    # PA2 / J2 ~RST / R1

# Dump load chain internal nodes (chain A: R6→R8→R10→R12; chain B: R7→R9→R11→R13)
net_r6_2   = Net('Net-(R6-Pad2)')    # R6[2] / R8[1]
net_r8_2   = Net('Net-(R10-Pad1)')   # R8[2] / R10[1]
net_r10_2  = Net('Net-(R10-Pad2)')   # R10[2] / R12[1]
net_r7_2   = Net('Net-(R7-Pad2)')    # R7[2] / R9[1]
net_r9_2   = Net('Net-(R11-Pad1)')   # R9[2] / R11[1]
net_r11_2  = Net('Net-(R11-Pad2)')   # R11[2] / R13[1]


# =============================================================================
# 4.  FOOTPRINT CONSTANTS & COMPONENT FACTORIES
# =============================================================================
FP_R0805_HS  = 'Resistors_SMD:R_0805_HandSoldering'
FP_R0805     = 'Resistors_SMD:R_0805'
FP_R2512     = 'Resistors_SMD:R_2512'
FP_R_THT_5W  = 'Resistors_THT:R_Axial_Power_L25.0mm_W9.0mm_P27.94mm'
FP_C0805_HS  = 'Capacitors_SMD:C_0805_HandSoldering'
FP_LED0805_HS = 'LEDs:LED_0805_HandSoldering'
FP_LED0805   = 'LEDs:LED_0805'
FP_SOT23     = 'TO_SOT_Packages_SMD:SOT-23'
FP_SOIC14    = 'Housings_SOIC:SOIC-14_3.9x8.7mm_Pitch1.27mm'
FP_SOP4      = 'Housings_SSOP:SOP-4_4.4x2.8mm_Pitch1.27mm'
FP_JST_PH2   = 'Connectors_JST:JST_PH_S2B-PH-K_02x2.00mm_Angled'
FP_HDR_2x03  = 'Pin_Headers:Pin_Header_Straight_2x03_Pitch2.54mm'
FP_HDR_1x05  = 'Pin_Headers:Pin_Header_Straight_1x05_Pitch2.54mm'


def make_res(ref, value, net_1, net_2, footprint=FP_R0805_HS):
    r = Part('Device', 'R', value=value, footprint=footprint)
    r.ref = ref
    r[1] += net_1
    r[2] += net_2
    return r


def make_cap(ref, value, net_pos, net_neg=None, footprint=FP_C0805_HS):
    c = Part('Device', 'C', value=value, footprint=footprint)
    c.ref = ref
    c[1] += net_pos
    c[2] += (net_neg if net_neg is not None else gnd)
    return c


# =============================================================================
# 5.  U4 — ATtiny841-SSU  (SOIC-14)
#     USART0: PB1(TX)/PB2(RX); USART1: PA4(RX)/PA5(TX)
#     ADC: PA0(ADC0), PA3(ADC3), PA4(ADC4), PA7(ADC7), PB0(ADC11)
# =============================================================================
u4_t = Part('Device', 'R', dest=TEMPLATE)
u4_t.name, u4_t.ref_prefix = 'ATtiny841-SSU', 'U'
u4_t.footprint = FP_SOIC14
u4_t.pins = [
    Pin(num='1',  name='VCC'),
    Pin(num='2',  name='PA0'),
    Pin(num='3',  name='PA1'),
    Pin(num='4',  name='PA2'),
    Pin(num='5',  name='PA3'),
    Pin(num='6',  name='PA4'),
    Pin(num='7',  name='PA5'),
    Pin(num='8',  name='PA6'),
    Pin(num='9',  name='PA7'),
    Pin(num='10', name='PB3'),   # RESET (repurposed as DUMP_LOAD_ENABLE via fuse)
    Pin(num='11', name='PB2'),
    Pin(num='12', name='PB1'),
    Pin(num='13', name='PB0'),
    Pin(num='14', name='GND'),
]

u4 = u4_t()
u4.ref   = 'U4'
u4.value = 'ATtiny841-SSU'

u4['VCC'] += vcc
u4['GND'] += gnd

u4['PA0'] += net_r21_ref       # ADC0     → R21 divider / SENSOR1-1
u4['PA1'] += net_sensor3       # ADC1     → SENSOR1-3 (external NTC mid)
u4['PA2'] += net_j2_rst        # GPIO     → J2 ~RST header / R1 pull-up
u4['PA3'] += net_r3_mid        # ADC3     → voltage divider mid (R3/R4)
u4['PA4'] += enable            # ADC4     → voltage divider top / R2 / SENSOR1-4
u4['PA5'] += net_d4_a          # TXD1/PA5 → D4 anode / J2-MOSI
u4['PA6'] += txd1              # PA6      → TXD1 / D2 anode
u4['PA7'] += rxd1              # ADC7     → NTC divider mid (R19/R20)
u4['PB3'] += dump_load_enable  # ~RST/PB3 → Q1 gate drive (R14)
u4['PB2'] += rxd0              # RXD0     → RX1 connector (via R16)
u4['PB1'] += txd0              # TXD0     → U1 optocoupler anode (via R5)
u4['PB0'] += two_volt          # ADC11    → LM4040 reference output (2.048V)

# MCU decoupling
make_cap('C1', '100nF', vcc)


# =============================================================================
# 6.  POWER1 — Battery / Cell Connector  (JST PH S2B, 2-pin angled)
#     Pin 1: Cell negative (GND)
#     Pin 2: Cell positive (VCC)
# =============================================================================
power1_t = Part('Device', 'R', dest=TEMPLATE)
power1_t.name, power1_t.ref_prefix = 'Conn_01x02_Male', 'POWER'
power1_t.footprint = FP_JST_PH2
power1_t.pins = [Pin(num='1', name='-'), Pin(num='2', name='+')]

power1 = power1_t()
power1.ref   = 'POWER1'
power1.value = 'Battery'
power1[1] += gnd
power1[2] += vcc


# =============================================================================
# 7.  CELL VOLTAGE MEASUREMENT  (R3, R4, D1, R2, C2)
#     Divider: ENABLE(PA4) → R3(475K) → PA3 → R4(402K) → GND
#     D1 (LM4040 2.048V) sets ENABLE = 2.048V (shunt ref across R4 output node)
#     R2 (1K) supplies bias current to D1; C2 (2.2µF) output bypass
#
#     Chain: VCC → ... → ENABLE --[R3]--> Net-R3-Pad2 --[R4]--> GND
#            D1 cathode = 2_VOLT = PB0;  D1 anode = GND
#            R2: ENABLE → 2_VOLT (bias current resistor for shunt ref D1)
# =============================================================================

# R3 (475K): upper resistor of voltage measurement divider
make_res('R3', '475K', enable, net_r3_mid)

# R4 (402K): lower resistor of voltage measurement divider
make_res('R4', '402K', net_r3_mid, gnd)

# R2 (1K): D1 bias current supply — ENABLE → R2 → 2_VOLT (D1 cathode)
make_res('R2', '1K', enable, two_volt)

# D1 (LM4040BIM3-2.0/NOPB): 2.048V precision shunt voltage reference (SOT-23)
#   Pin 1: K (Cathode = +, 2.048V output) → 2_VOLT
#   Pin 2: A (Anode  = -, lower) → GND
d1_t = Part('Device', 'R', dest=TEMPLATE)
d1_t.name, d1_t.ref_prefix = 'LM4040DBZ-2.0', 'D'
d1_t.footprint = FP_SOT23
d1_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]

d1 = d1_t()
d1.ref   = 'D1'
d1.value = 'LM4040BIM3-2.0/NOPB, 2.048V, SOT-23-3'
d1['K'] += two_volt
d1['A'] += gnd

# C2 (2.2µF): LM4040 output bypass / noise filter
make_cap('C2', '2.2uF', two_volt)


# =============================================================================
# 8.  DUMP LOAD  (R6–R13, Q1, R14, R15, C3, R22, D3, R17)
#     Two parallel chains of 4 × 2R2 1W from VCC → Q1 drain
#     Chain A: VCC → R6 → R8 → R10 → R12 → Q1_drain
#     Chain B: VCC → R7 → R9 → R11 → R13 → Q1_drain
#     R22 (10R 5W THT) from VCC to Q1_drain as minimum current path
#     Q1 (IRLML6244, SOT-23 N-MOSFET): drain=net_q1_drain, source=GND
#     Gate drive: U4 PB3 → R14(510R) → Q1_gate; R15(47K) pulls gate low; C3(10µF) filters
#     D3 (Red LED): VCC → D3 → R17(2K2) → Q1_drain (lights when Q1 conducting)
# =============================================================================

# Dump load resistor chains (2R2 1W, R_2512)
make_res('R6',  '2R2 1W', vcc,       net_r6_2,  footprint=FP_R2512)
make_res('R8',  '2R2 1W', net_r6_2,  net_r8_2,  footprint=FP_R2512)
make_res('R10', '2R2 1W', net_r8_2,  net_r10_2, footprint=FP_R2512)
make_res('R12', '2R2 1W', net_r10_2, net_q1_drain, footprint=FP_R2512)

make_res('R7',  '2R2 1W', vcc,       net_r7_2,  footprint=FP_R2512)
make_res('R9',  '2R2 1W', net_r7_2,  net_r9_2,  footprint=FP_R2512)
make_res('R11', '2R2 1W', net_r9_2,  net_r11_2, footprint=FP_R2512)
make_res('R13', '2R2 1W', net_r11_2, net_q1_drain, footprint=FP_R2512)

# R22 (10R 5W, THT): bypass / minimum load from VCC to Q1 drain
make_res('R22', '10R', net_q1_drain, vcc, footprint=FP_R_THT_5W)

# Q1 (IRLML6244TRPBF, N-MOSFET SOT-23): G=1, S=2, D=3
q1_t = Part('Device', 'R', dest=TEMPLATE)
q1_t.name, q1_t.ref_prefix = 'IRLML6244TRPBF', 'Q'
q1_t.footprint = FP_SOT23
q1_t.pins = [
    Pin(num='1', name='G'),
    Pin(num='2', name='S'),
    Pin(num='3', name='D'),
]

q1 = q1_t()
q1.ref   = 'Q1'
q1.value = 'IRLML6244TRPBF'
q1['G'] += net_q1_gate
q1['S'] += gnd
q1['D'] += net_q1_drain

# R14 (510R): gate drive series resistor — DUMP_LOAD_ENABLE → Q1 gate
make_res('R14', '510R', dump_load_enable, net_q1_gate)

# R15 (47K): Q1 gate pull-down to GND (prevents spurious turn-on)
make_res('R15', '47K', net_q1_gate, gnd)

# C3 (10µF 10V): Q1 gate filter cap (slows switching to reduce EMI)
make_cap('C3', '10uF 10V', net_q1_gate)

# D3 (Red LED, 0805): dump load active indicator
#   Anode → VCC via D3; Cathode → R17 → Q1_drain (lights when Q1 on)
d3_t = Part('Device', 'R', dest=TEMPLATE)
d3_t.name, d3_t.ref_prefix = 'LED', 'D'
d3_t.footprint = FP_LED0805_HS
d3_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]

d3 = d3_t()
d3.ref   = 'D3'
d3.value = 'RED LED'
d3['A'] += vcc
d3['K'] += net_d3_k

make_res('R17', '2K2', net_q1_drain, net_d3_k)


# =============================================================================
# 9.  OPTOCOUPLER TX  (U1, R5)
#     ATtiny PB1(TXD0) → R5(220R) → U1 LED anode → cathode → GND
#     U1 phototransistor emitter → TX1[1]; collector → TX1[2]
# =============================================================================
u1_t = Part('Device', 'R', dest=TEMPLATE)
u1_t.name, u1_t.ref_prefix = 'HMHA2801', 'U'
u1_t.footprint = FP_SOP4
u1_t.pins = [
    Pin(num='1', name='A'),    # LED Anode
    Pin(num='2', name='K'),    # LED Cathode
    Pin(num='3', name='E'),    # Phototransistor Emitter
    Pin(num='4', name='C'),    # Phototransistor Collector
]

u1 = u1_t()
u1.ref   = 'U1'
u1.value = 'HMHA2801'
u1['A'] += net_r5_opto
u1['K'] += gnd
u1['E'] += net_tx1_e
u1['C'] += net_tx1_c

# R5 (220R): optocoupler LED current limiter — TXD0 → R5 → U1 anode
make_res('R5', '220R', net_r5_opto, txd0)


# =============================================================================
# 10.  TX1 / RX1 — UART Daisy-Chain Connectors  (JST PH S2B)
#      TX1 pin1 → U1 emitter; TX1 pin2 → U1 collector
#      RX1 pin1 → RXD0 (U4 PB2); RX1 pin2 → VCC
# =============================================================================
jst2_t = Part('Device', 'R', dest=TEMPLATE)
jst2_t.name, jst2_t.ref_prefix = 'Conn_01x02_Male', 'CONN'
jst2_t.footprint = FP_JST_PH2
jst2_t.pins = [Pin(num='1', name='P1'), Pin(num='2', name='P2')]

tx1 = jst2_t()
tx1.ref   = 'TX1'
tx1.value = 'TX Connector'
tx1[1] += net_tx1_e      # U1 emitter
tx1[2] += net_tx1_c      # U1 collector

rx1 = jst2_t()
rx1.ref   = 'RX1'
rx1.value = 'RX Connector'
rx1[1] += rxd0            # → U4 PB2 via R16
rx1[2] += vcc             # RX1 pin2 pull-up to VCC

# R16 (4K7): pull-down / filter on RXD0 line
make_res('R16', '4K7', gnd, rxd0)


# =============================================================================
# 11.  J2 — AVR ISP-6 Programming Header  (2×3, 2.54mm pitch)
#      Pin 1: MISO  → TXD1 (PA6)
#      Pin 2: VCC   → VCC
#      Pin 3: SCK   → RXD1 (PA7)
#      Pin 4: MOSI  → Net-(D4-Pad2) = PA5
#      Pin 5: ~RST  → Net-(J2-Pad5) = PA2
#      Pin 6: GND   → GND
# =============================================================================
j2_t = Part('Device', 'R', dest=TEMPLATE)
j2_t.name, j2_t.ref_prefix = 'AVR-ISP-6', 'J'
j2_t.footprint = FP_HDR_2x03
j2_t.pins = [
    Pin(num='1', name='MISO'),
    Pin(num='2', name='VCC'),
    Pin(num='3', name='SCK'),
    Pin(num='4', name='MOSI'),
    Pin(num='5', name='~RST'),
    Pin(num='6', name='GND'),
]

j2 = j2_t()
j2.ref   = 'J2'
j2.value = 'AVR-ISP-6'
j2['MISO'] += txd1
j2['VCC']  += vcc
j2['SCK']  += rxd1
j2['MOSI'] += net_d4_a
j2['~RST'] += net_j2_rst
j2['GND']  += gnd

# R1 (10K): pull-up on PA2 / J2 ~RST line
make_res('R1', '10K', vcc, net_j2_rst)


# =============================================================================
# 12.  STATUS LEDs
#      D2 (Blue, LED_0805): TXD1 activity — PA6 → D2_A → D2_K → R23 → GND
#      D4 (Green, LED_0805): PA5/MOSI indicator — PA5 → D4_A → D4_K → R18 → GND
# =============================================================================
d2_t = Part('Device', 'R', dest=TEMPLATE)
d2_t.name, d2_t.ref_prefix = 'LED', 'D'
d2_t.footprint = FP_LED0805
d2_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]

d2 = d2_t()
d2.ref   = 'D2'
d2.value = 'Blue'
d2['A'] += txd1
d2['K'] += net_d2_k

make_res('R23', '2K2', net_d2_k, gnd, footprint=FP_R0805)

d4_t = Part('Device', 'R', dest=TEMPLATE)
d4_t.name, d4_t.ref_prefix = 'LED', 'D'
d4_t.footprint = FP_LED0805_HS
d4_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]

d4 = d4_t()
d4.ref   = 'D4'
d4.value = 'Green'
d4['A'] += net_d4_a
d4['K'] += net_d4_k

make_res('R18', '2K2', gnd, net_d4_k)


# =============================================================================
# 13.  TEMPERATURE SENSING  (R19 NTC, R20, R21, SENSOR1)
#      On-board NTC: 2_VOLT → R19(NTC 47K) → RXD1(PA7) → R20(47K) → GND
#      Reference divider for SENSOR1: PA0 → R21(47K) → GND
#      SENSOR1 (5-pin header): remote NTC input
#        Pin 1 → PA0 / R21 node
#        Pin 2 → 2_VOLT (reference supply for external NTC divider)
#        Pin 3 → PA1 (ADC1, external NTC mid-point)
#        Pin 4 → ENABLE (cell voltage measurement reference)
#        Pin 5 → GND
# =============================================================================
# On-board NTC divider
r19_t = Part('Device', 'R', dest=TEMPLATE)
r19_t.name, r19_t.ref_prefix = 'Thermistor', 'R'
r19_t.footprint = FP_R0805_HS
r19_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]

r19 = r19_t()
r19.ref   = 'R19'
r19.value = 'SDNT2012X473F4150FTF'
r19[1] += two_volt
r19[2] += rxd1

make_res('R20', '47K', rxd1, gnd)                  # NTC lower divider
make_res('R21', '47K', net_r21_ref, gnd)            # SENSOR1 reference pull-down

# SENSOR1 (1×5 pin header, 2.54mm pitch)
sensor1_t = Part('Device', 'R', dest=TEMPLATE)
sensor1_t.name, sensor1_t.ref_prefix = 'Conn_01x05_Male', 'SENSOR'
sensor1_t.footprint = FP_HDR_1x05
sensor1_t.pins = [
    Pin(num='1', name='P1'),
    Pin(num='2', name='P2'),
    Pin(num='3', name='P3'),
    Pin(num='4', name='P4'),
    Pin(num='5', name='P5'),
]

sensor1 = sensor1_t()
sensor1.ref   = 'SENSOR1'
sensor1.value = 'Remote temp input 47K @ 25oC'
sensor1[1] += net_r21_ref   # PA0 / R21 node
sensor1[2] += two_volt       # 2.048V reference supply
sensor1[3] += net_sensor3    # PA1 ADC input
sensor1[4] += enable         # ENABLE (cell voltage measurement node)
sensor1[5] += gnd


# =============================================================================
# 14.  OUTPUT: KiCad netlist  +  CSV BOM
# =============================================================================

def generate_csv_bom(filename: str = 'modulev400_BOM.csv') -> None:
    """
    Walk every instantiated (non-template) part, group by
    (name, value, footprint), sort refs naturally, write CSV.
    """
    bom_groups: dict = defaultdict(list)

    for part in default_circuit.parts:  # type: ignore[attr-defined]
        if getattr(part, 'dest', None) == TEMPLATE:  # type: ignore[name-defined]
            continue
        ref = getattr(part, 'ref', None)
        if not ref:
            continue
        key = (
            getattr(part, 'name',      ''),
            getattr(part, 'value',     ''),
            getattr(part, 'footprint', ''),
        )
        bom_groups[key].append(ref)

    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Quantity', 'Reference(s)', 'Value', 'Part Name', 'Footprint'])
        for (name, value, footprint), refs in sorted(bom_groups.items()):
            refs.sort()
            writer.writerow([len(refs), ', '.join(refs), value, name, footprint])

    print(f'✅  BOM   saved  →  {filename}')


generate_netlist(filename='modulev400.net')
print('✅  Netlist saved  →  modulev400.net')
generate_csv_bom(filename='modulev400_BOM.csv')
