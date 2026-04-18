"""
modulev421_skidl.py  —  DIYBMS Cell Monitoring Module v4.21
============================================================
SKiDL script to regenerate the KiCad netlist and grouped BOM for the
diyBMS v4.21 cell monitoring module (Stuart Pittaway, rev 4.2, 2020-01-25).

Key changes vs v4.00:
  - MCU ref     : U4 → ATTINY841 (rescue lib pin order reversed vs standard)
  - Voltage ref : LM4040 → TL432G (adjustable, FB shorted to K = 2.5V fixed)
  - MOSFET      : IRLML6244 → AO3400A (same SOT-23 G/S/D topology)
  - Dump load   : 8×2R2 2512 THT → 20×6R2 1206 SMD in 5 parallel chains of 4
  - Passives    : 0805 → 0603; dump load 2512 → 1206
  - Added C2 (1µF) bypass cap

Schematic source : ModuleV421.sch  (KiCad 5.1.5)
BOM source       : ModuleV421.csv
Netlist source   : ModuleV421.net

Usage:
    python modulev421_skidl.py
Outputs:
    modulev421.net          — KiCad-compatible netlist
    modulev421_BOM.csv      — grouped Bill of Materials
"""

import os
import csv
from collections import defaultdict


# =============================================================================
# 1.  SETUP & PATHS
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
# 2.  POWER RAILS
# =============================================================================
gnd = Net('GND')
vcc = Net('VCC')          # Cell positive = module supply


# =============================================================================
# 3.  SIGNAL NETS  (names match ModuleV421.net labels exactly)
# =============================================================================
two_volt         = Net('2_VOLT')           # TL432G output node (2.5 V reference)
enable           = Net('ENABLE')           # Cell voltage divider top / PA7
txd0             = Net('TXD0')             # ATTINY841 PA1 → U1 LED
rxd0             = Net('RXD0')             # ATTINY841 PA2 ← RX1 connector

net_tx1_e        = Net('Net-(TX1-Pad1)')   # U1 emitter → TX1[1]
net_tx1_c        = Net('Net-(TX1-Pad2)')   # U1 collector → TX1[2]
net_d2_k         = Net('Net-(D2-Pad1)')    # D2 cathode / R23[2]
net_d3_k         = Net('Net-(D3-Pad1)')    # D3 cathode / R17[2]
net_d4_a         = Net('Net-(ATTINY841-Pad7)')   # PA6 / J2-MOSI / D4 anode
net_d4_k         = Net('Net-(D4-Pad1)')    # D4 cathode / R18[2]
net_r5_opto      = Net('Net-(R5-Pad1)')    # R5 / U1 anode
net_r3_mid       = Net('Net-(ATTINY841-Pad5)')   # Voltage divider mid: R3[2]/R4[1]/PB2
net_attiny_p2    = Net('Net-(ATTINY841-Pad2)')   # PB0 / SENSOR1[1] / R21[1]
net_attiny_p3    = Net('Net-(ATTINY841-Pad3)')   # PB1 / SENSOR1[3]
net_attiny_p4    = Net('Net-(ATTINY841-Pad4)')   # ~RST/PB3 / J2[5] / R1[2]
net_attiny_p8    = Net('Net-(ATTINY841-Pad8)')   # PA5 / J2-MISO / D2 anode
net_attiny_p9    = Net('Net-(ATTINY841-Pad9)')   # PA4 / J2-SCK / NTC mid
dump_load_enable = Net('DUMP_LOAD_ENABLE') # PA3 → R14 → Q1 gate
net_q1_gate      = Net('Net-(C3-Pad1)')    # Q1 gate / R14 / R15 / C3
net_q1_drain     = Net('Net-(Q1-Pad3)')    # Q1 drain / dump load bottom / D3/R17

# Dump load chain internal nodes — 5 chains × 4 × 6R2 1206
# Chain A: VCC→R6→R8→R10→R12→drain
net_r6_2   = Net('Net-(R6-Pad2)')
net_r8_2   = Net('Net-(R10-Pad1)')
net_r10_2  = Net('Net-(R10-Pad2)')
# Chain B: VCC→R7→R9→R11→R13→drain
net_r7_2   = Net('Net-(R7-Pad2)')
net_r9_2   = Net('Net-(R11-Pad1)')
net_r11_2  = Net('Net-(R11-Pad2)')
# Chain C: VCC→R22→R25→R27→R29→drain
net_r22_2  = Net('Net-(R22-Pad2)')
net_r25_2  = Net('Net-(R25-Pad2)')
net_r27_2  = Net('Net-(R27-Pad2)')
# Chain D: VCC→R24→R26→R28→R30→drain
net_r24_2  = Net('Net-(R24-Pad2)')
net_r26_2  = Net('Net-(R26-Pad2)')
net_r28_2  = Net('Net-(R28-Pad2)')
# Chain E: VCC→R31→R32→R33→R34→drain
net_r31_2  = Net('Net-(R31-Pad2)')
net_r32_2  = Net('Net-(R32-Pad2)')
net_r33_2  = Net('Net-(R33-Pad2)')


# =============================================================================
# 4.  FOOTPRINT CONSTANTS & FACTORIES
# =============================================================================
FP_R0603     = 'Resistors_SMD:R_0603'
FP_R1206     = 'Resistors_SMD:R_1206'
FP_R0402     = 'Resistors_SMD:R_0402'
FP_C0805     = 'Capacitors_SMD:C_0805'
FP_C0603     = 'Capacitors_SMD:C_0603'
FP_LED0805   = 'LEDs:LED_0805'
FP_SOT23     = 'TO_SOT_Packages_SMD:SOT-23'
FP_SOIC14    = 'Housings_SOIC:SOIC-14_3.9x8.7mm_Pitch1.27mm'
FP_SOP4      = 'Housings_SSOP:SOP-4_4.4x2.8mm_Pitch1.27mm'
FP_JST_PH2   = 'Connectors_JST:JST_PH_S2B-PH-K_02x2.00mm_Angled'
FP_HDR_2x03  = 'Pin_Headers:Pin_Header_Straight_2x03_Pitch2.54mm'
FP_HDR_1x05  = 'Pin_Headers:Pin_Header_Straight_1x05_Pitch2.54mm'


def make_res(ref, value, net_1, net_2, footprint=FP_R0603):
    r = Part('Device', 'R', value=value, footprint=footprint)
    r.ref = ref
    r[1] += net_1
    r[2] += net_2
    return r


def make_cap(ref, value, net_pos, net_neg=None, footprint=FP_C0805):
    c = Part('Device', 'C', value=value, footprint=footprint)
    c.ref = ref
    c[1] += net_pos
    c[2] += (net_neg if net_neg is not None else gnd)
    return c


# =============================================================================
# 5.  ATTINY841 — ATtiny841-SSU  (SOIC-14, rescue lib pin order)
#
#     IMPORTANT: v4.21 rescue library reverses the physical pin order vs
#     standard KiCad ATtiny841. Pins are mapped as follows:
#       1=VCC  2=XTAL1/PB0  3=XTAL2/PB1  4=~RST/PB3  5=PB2
#       6=PA7  7=PA6        8=PA5        9=PA4       10=PA3
#      11=PA2 12=PA1       13=AREF/PA0  14=GND
# =============================================================================
attiny_t = Part('Device', 'R', dest=TEMPLATE)
attiny_t.name, attiny_t.ref_prefix = 'ATtiny841-SSU', 'U'
attiny_t.footprint = FP_SOIC14
attiny_t.pins = [
    Pin(num='1',  name='VCC'),
    Pin(num='2',  name='XTAL1/PB0'),
    Pin(num='3',  name='XTAL2/PB1'),
    Pin(num='4',  name='~RESET~/PB3'),
    Pin(num='5',  name='PB2'),
    Pin(num='6',  name='PA7'),
    Pin(num='7',  name='PA6'),
    Pin(num='8',  name='PA5'),
    Pin(num='9',  name='PA4'),
    Pin(num='10', name='PA3'),
    Pin(num='11', name='PA2'),
    Pin(num='12', name='PA1'),
    Pin(num='13', name='AREF/PA0'),
    Pin(num='14', name='GND'),
]

attiny841 = attiny_t()
attiny841.ref   = 'ATTINY841'
attiny841.value = 'ATtiny841-SSU'

attiny841['VCC']         += vcc
attiny841['GND']         += gnd
attiny841['XTAL1/PB0']   += net_attiny_p2    # SENSOR1[1] / R21
attiny841['XTAL2/PB1']   += net_attiny_p3    # SENSOR1[3]
attiny841['~RESET~/PB3'] += net_attiny_p4    # J2 ~RST / R1 pull-up
attiny841['PB2']         += net_r3_mid       # Voltage divider mid (R3/R4)
attiny841['PA7']         += enable           # Voltage divider top / R2 / SENSOR1[4]
attiny841['PA6']         += net_d4_a         # D4 anode / J2-MOSI
attiny841['PA5']         += net_attiny_p8    # D2 anode / J2-MISO
attiny841['PA4']         += net_attiny_p9    # NTC divider mid / J2-SCK
attiny841['PA3']         += dump_load_enable # Q1 gate drive (via R14)
attiny841['PA2']         += rxd0             # USART RX ← RX1 (via R16)
attiny841['PA1']         += txd0             # USART TX → U1 opto (via R5)
attiny841['AREF/PA0']    += two_volt         # TL432G reference output

# MCU decoupling
make_cap('C1', '100nF', vcc)
make_cap('C2', '1uF',   vcc)


# =============================================================================
# 6.  POWER1 — Battery Connector  (JST PH S2B)
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
# 7.  CELL VOLTAGE MEASUREMENT  (R3, R4, D1, R2)
#     Divider: ENABLE(PA7) → R3(68K) → PB2 → R4(27K) → GND
#     D1 (TL432G) adjustable reference: FB=K=2_VOLT → 2.5V fixed; A→GND
#     R2 (1K): ENABLE → 2_VOLT (bias current for TL432G shunt)
# =============================================================================
make_res('R3', '68KOHMS', enable, net_r3_mid)
make_res('R4', '27KOHMS', net_r3_mid, gnd)
make_res('R2', '1KOHMS',  enable, two_volt)

# D1 (TL432G-A-AE3-R): adjustable shunt reference (LM385Z-ADJ symbol)
#   Pin 1: FB (feedback) → 2_VOLT  (shorted to K → fixed ~2.5V)
#   Pin 2: K  (cathode)  → 2_VOLT
#   Pin 3: A  (anode)    → GND
d1_t = Part('Device', 'R', dest=TEMPLATE)
d1_t.name, d1_t.ref_prefix = 'LM385Z-ADJ', 'D'
d1_t.footprint = FP_SOT23
d1_t.pins = [
    Pin(num='1', name='FB'),
    Pin(num='2', name='K'),
    Pin(num='3', name='A'),
]

d1 = d1_t()
d1.ref   = 'D1'
d1.value = 'TL432G-A-AE3-R'
d1['FB'] += two_volt   # FB shorted to K → fixed reference mode
d1['K']  += two_volt
d1['A']  += gnd


# =============================================================================
# 8.  DUMP LOAD  (20 × 6R2 1206 in 5 parallel chains of 4, Q1 AO3400A)
#
#     Chain A: VCC → R6  → R8  → R10 → R12 → Q1_drain
#     Chain B: VCC → R7  → R9  → R11 → R13 → Q1_drain
#     Chain C: VCC → R22 → R25 → R27 → R29 → Q1_drain
#     Chain D: VCC → R24 → R26 → R28 → R30 → Q1_drain
#     Chain E: VCC → R31 → R32 → R33 → R34 → Q1_drain
#
#     Q1 gate: DUMP_LOAD_ENABLE → R14(510R) → gate; R15(47K) pull-down; C3(10µF) filter
#     D3 (Red LED): VCC → D3 → R17(2K2) → Q1_drain (dump active indicator)
# =============================================================================
_DL = '6.2OHMS'

make_res('R6',  _DL, vcc,       net_r6_2,    footprint=FP_R1206)
make_res('R8',  _DL, net_r6_2,  net_r8_2,    footprint=FP_R1206)
make_res('R10', _DL, net_r8_2,  net_r10_2,   footprint=FP_R1206)
make_res('R12', _DL, net_r10_2, net_q1_drain, footprint=FP_R1206)

make_res('R7',  _DL, vcc,       net_r7_2,    footprint=FP_R1206)
make_res('R9',  _DL, net_r7_2,  net_r9_2,    footprint=FP_R1206)
make_res('R11', _DL, net_r9_2,  net_r11_2,   footprint=FP_R1206)
make_res('R13', _DL, net_r11_2, net_q1_drain, footprint=FP_R1206)

make_res('R22', _DL, vcc,       net_r22_2,   footprint=FP_R1206)
make_res('R25', _DL, net_r22_2, net_r25_2,   footprint=FP_R1206)
make_res('R27', _DL, net_r25_2, net_r27_2,   footprint=FP_R1206)
make_res('R29', _DL, net_r27_2, net_q1_drain, footprint=FP_R1206)

make_res('R24', _DL, vcc,       net_r24_2,   footprint=FP_R1206)
make_res('R26', _DL, net_r24_2, net_r26_2,   footprint=FP_R1206)
make_res('R28', _DL, net_r26_2, net_r28_2,   footprint=FP_R1206)
make_res('R30', _DL, net_r28_2, net_q1_drain, footprint=FP_R1206)

make_res('R31', _DL, vcc,       net_r31_2,   footprint=FP_R1206)
make_res('R32', _DL, net_r31_2, net_r32_2,   footprint=FP_R1206)
make_res('R33', _DL, net_r32_2, net_r33_2,   footprint=FP_R1206)
make_res('R34', _DL, net_r33_2, net_q1_drain, footprint=FP_R1206)

# Q1 (AO3400A, N-MOSFET SOT-23): G=1, S=2, D=3
q1_t = Part('Device', 'R', dest=TEMPLATE)
q1_t.name, q1_t.ref_prefix = 'AO3400A', 'Q'
q1_t.footprint = FP_SOT23
q1_t.pins = [
    Pin(num='1', name='G'),
    Pin(num='2', name='S'),
    Pin(num='3', name='D'),
]

q1 = q1_t()
q1.ref   = 'Q1'
q1.value = 'AO3400A'
q1['G'] += net_q1_gate
q1['S'] += gnd
q1['D'] += net_q1_drain

make_res('R14', '510OHMS', dump_load_enable, net_q1_gate)
make_res('R15', '47KOHMS', net_q1_gate, gnd)
make_cap('C3',  '10uF X5R', net_q1_gate, footprint=FP_C0603)

# D3 (Red LED): dump load active indicator — VCC → D3 → R17 → Q1_drain
d3_t = Part('Device', 'R', dest=TEMPLATE)
d3_t.name, d3_t.ref_prefix = 'LED', 'D'
d3_t.footprint = FP_LED0805
d3_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]

d3 = d3_t()
d3.ref   = 'D3'
d3.value = 'Red'
d3['A'] += vcc
d3['K'] += net_d3_k

make_res('R17', '2.2KOHMS', net_q1_drain, net_d3_k)


# =============================================================================
# 9.  OPTOCOUPLER TX  (U1 EL3H7, R5)
#     PA1(TXD0) → R5(220R) → U1 anode → cathode → GND
#     U1 emitter → TX1[1]; U1 collector → TX1[2]
# =============================================================================
u1_t = Part('Device', 'R', dest=TEMPLATE)
u1_t.name, u1_t.ref_prefix = 'EL3H7', 'U'
u1_t.footprint = FP_SOP4
u1_t.pins = [
    Pin(num='1', name='A'),
    Pin(num='2', name='K'),
    Pin(num='3', name='E'),
    Pin(num='4', name='C'),
]

u1 = u1_t()
u1.ref   = 'U1'
u1.value = 'EL3H7(B)(TA)-G'
u1['A'] += net_r5_opto
u1['K'] += gnd
u1['E'] += net_tx1_e
u1['C'] += net_tx1_c

make_res('R5', '220OHMS', net_r5_opto, txd0)


# =============================================================================
# 10.  TX1 / RX1 — UART Daisy-Chain Connectors  (JST PH S2B)
# =============================================================================
jst2_t = Part('Device', 'R', dest=TEMPLATE)
jst2_t.name, jst2_t.ref_prefix = 'Conn_01x02_Male', 'CONN'
jst2_t.footprint = FP_JST_PH2
jst2_t.pins = [Pin(num='1', name='P1'), Pin(num='2', name='P2')]

tx1 = jst2_t()
tx1.ref   = 'TX1'
tx1.value = 'TX Connector'
tx1[1] += net_tx1_e
tx1[2] += net_tx1_c

rx1 = jst2_t()
rx1.ref   = 'RX1'
rx1.value = 'RX Connector'
rx1[1] += rxd0
rx1[2] += vcc

make_res('R16', '4.7KOHMS', gnd, rxd0)


# =============================================================================
# 11.  J2 — AVR ISP-6 Header  (2×3, 2.54mm)
#      Pin 1: MISO → Net-(ATTINY841-Pad8) = PA5
#      Pin 2: VCC  → VCC
#      Pin 3: SCK  → Net-(ATTINY841-Pad9) = PA4 / NTC mid
#      Pin 4: MOSI → Net-(ATTINY841-Pad7) = PA6 / D4 anode
#      Pin 5: ~RST → Net-(ATTINY841-Pad4) = ~RST/PB3
#      Pin 6: GND  → GND
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
j2['MISO'] += net_attiny_p8
j2['VCC']  += vcc
j2['SCK']  += net_attiny_p9
j2['MOSI'] += net_d4_a
j2['~RST'] += net_attiny_p4
j2['GND']  += gnd

make_res('R1', '10KOHMS', vcc, net_attiny_p4)


# =============================================================================
# 12.  STATUS LEDs
#      D2 (Blue):  PA5 → D2_A → D2_K → R23(1K8) → GND
#      D4 (Green): PA6 → D4_A → D4_K → R18(2K2) → GND
# =============================================================================
d2_t = Part('Device', 'R', dest=TEMPLATE)
d2_t.name, d2_t.ref_prefix = 'LED', 'D'
d2_t.footprint = FP_LED0805
d2_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]

d2 = d2_t()
d2.ref   = 'D2'
d2.value = 'Blue'
d2['A'] += net_attiny_p8
d2['K'] += net_d2_k

make_res('R23', '1.8KOHMS', net_d2_k, gnd)

d4_t = Part('Device', 'R', dest=TEMPLATE)
d4_t.name, d4_t.ref_prefix = 'LED', 'D'
d4_t.footprint = FP_LED0805
d4_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]

d4 = d4_t()
d4.ref   = 'D4'
d4.value = 'Green'
d4['A'] += net_d4_a
d4['K'] += net_d4_k

make_res('R18', '2.2KOHMS', gnd, net_d4_k)


# =============================================================================
# 13.  TEMPERATURE SENSING  (R19 NTC 0402, R20, R21, SENSOR1)
#      On-board NTC: 2_VOLT → R19(47K NTC) → PA4 → R20(47K) → GND
#      SENSOR1 reference divider: PB0 → R21(47K) → GND
#      SENSOR1 5-pin header:
#        Pin 1 → PB0 / R21
#        Pin 2 → 2_VOLT
#        Pin 3 → PB1
#        Pin 4 → ENABLE
#        Pin 5 → GND
# =============================================================================
r19_t = Part('Device', 'R', dest=TEMPLATE)
r19_t.name, r19_t.ref_prefix = 'Thermistor', 'R'
r19_t.footprint = FP_R0402
r19_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]

r19 = r19_t()
r19.ref   = 'R19'
r19.value = 'NTC THERMISTOR 47KOHMS 4050K'
r19[1] += two_volt
r19[2] += net_attiny_p9

make_res('R20', '47KOHMS', net_attiny_p9, gnd)
make_res('R21', '47KOHMS', net_attiny_p2, gnd)

sensor1_t = Part('Device', 'R', dest=TEMPLATE)
sensor1_t.name, sensor1_t.ref_prefix = 'Conn_01x05_Male', 'SENSOR'
sensor1_t.footprint = FP_HDR_1x05
sensor1_t.pins = [
    Pin(num='1', name='Pin_1'),
    Pin(num='2', name='Pin_2'),
    Pin(num='3', name='Pin_3'),
    Pin(num='4', name='Pin_4'),
    Pin(num='5', name='Pin_5'),
]

sensor1 = sensor1_t()
sensor1.ref   = 'SENSOR1'
sensor1.value = 'Remote temp input 47K @ 25oC'
sensor1[1] += net_attiny_p2   # PB0 / R21
sensor1[2] += two_volt         # 2.5V reference supply
sensor1[3] += net_attiny_p3   # PB1 ADC
sensor1[4] += enable           # ENABLE node
sensor1[5] += gnd


# =============================================================================
# 14.  OUTPUT: KiCad netlist  +  CSV BOM
# =============================================================================

def generate_csv_bom(filename: str = 'modulev421_BOM.csv') -> None:
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


generate_netlist(filename='modulev421.net')
print('✅  Netlist saved  →  modulev421.net')
generate_csv_bom(filename='modulev421_BOM.csv')
