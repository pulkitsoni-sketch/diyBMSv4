"""
modulev440_skidl.py  —  DIYBMS Cell Monitoring Module v4.40
============================================================
SKiDL script to regenerate the KiCad netlist and grouped BOM for the
diyBMS v4.40 cell monitoring module (Stuart Pittaway, rev 4.4, 2021-03-03).

Key changes vs v4.21:
  - Added F1  : mSMD150 polyfuse (1812) between POWER1+ and VCC
  - Added D2  : SMBJ5.0A unidirectional 5V TVS (VCC↔GND ESD clamp)
  - Added Y1  : 8MHz ceramic resonator + C4/C5 (22pF) load caps on XTAL pins
  - Voltage ref: TL432G → AZ432ANTR-E1 (same SOT-23 FB/K/A topology)
  - Two NTC sensors: R19 (on PA4/SCK) + R23 (on PA5/MISO) both vs VREF
  - Added EXTTEMP1 (JST PH horizontal) + REMOTE1 (pin header) for external NTC
  - Removed SENSOR1 5-pin header
  - Dump load: 4 chains × 4 pads but only 3 chains × 3 resistors populated
      Populated (9 × 3.3Ω 2010): R6, R8, R12, R22, R25, R29, R24, R26, R30
      DNP in JLCPCB BOM: R7, R9, R10, R11, R13 (chain B + chain-A mid)
                          R27 (chain-C mid), R28 (chain-D mid)
  - DUMP_LOAD_ENABLE moved: PA3(pin10) → PB2(pin5)
  - PA3(pin10) now used as voltage-divider ADC input
  - R3: 68K→6.8K; R4: 27K→2.7K (voltage divider for lower supply range)
  - RXD0 pull-down: R16 2.2K (was 4.7K)
  - D3/D4 drive resistors: R17/R18 2.2K each (consolidated)

Schematic source : ModuleV440.sch  (KiCad 5.1.9)
BOM source       : ModuleV440_bom_jlc.csv
Netlist source   : ModuleV440.net

Usage:
    python modulev440_skidl.py
Outputs:
    modulev440.net          — KiCad-compatible netlist
    modulev440_BOM.csv      — grouped Bill of Materials
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
vcc = Net('VCC')          # Cell positive (after polyfuse F1)


# =============================================================================
# 3.  SIGNAL NETS  (names match ModuleV440.net labels exactly)
# =============================================================================
vref             = Net('VREF')             # AZ432 reference output (~1.25V)
enable           = Net('ENABLE')           # Cell voltage divider top / PA7
miso             = Net('MISO')             # PA5 / ADC5 / NTC-2 mid / ext temp
sck              = Net('SCK')              # PA4 / ADC4 / NTC-1 mid / J2-SCK
txd0             = Net('TXD0')             # PA1 → U1 optocoupler LED
rxd0             = Net('RXD0')             # PA2 ← RX1 connector
dump_load_enable = Net('DUMP_LOAD_ENABLE') # PB2(pin5) → Q1 gate drive

net_f1_bat       = Net('Net-(F1-Pad2)')    # POWER1[2] / F1[2]  (pre-fuse battery+)
net_tx1_e        = Net('Net-(TX1-Pad1)')   # U1 emitter → TX1[1]
net_tx1_c        = Net('Net-(TX1-Pad2)')   # U1 collector → TX1[2]
net_r5_opto      = Net('Net-(R5-Pad1)')    # R5 / U1 anode
net_q1_gate      = Net('Net-(Q1-Pad1)')    # Q1 gate / R14 / R15
net_q1_drain     = Net('Net-(Q1-Pad3)')    # Q1 drain / dump load bottom / D3/R17
net_d3_k         = Net('Net-(D3-Pad1)')    # D3 cathode / R17[2]
net_d4_k         = Net('Net-(D4-Pad1)')    # D4 cathode / R18[2]
net_d4_a         = Net('Net-(ATTINY841-Pad7)')   # PA6 / J2-MOSI / D4 anode
net_attiny_p2    = Net('Net-(ATTINY841-Pad2)')   # XTAL1/PB0 / C4 / Y1[2]
net_attiny_p3    = Net('Net-(ATTINY841-Pad3)')   # XTAL2/PB1 / C5 / Y1[1]
net_attiny_p4    = Net('Net-(ATTINY841-Pad4)')   # ~RST/PB3 / R1 / J2[5]
net_attiny_p10   = Net('Net-(ATTINY841-Pad10)')  # PA3 / voltage divider mid (R3/R4)

# Dump load chain internal nodes (all 4 chains from netlist; Chain B + mids DNP)
# Chain A (populated: R6,R8,R12; R10=DNP): VCC→R6→R8→R10→R12→drain
net_r6_2   = Net('Net-(R6-Pad2)')
net_r10_a  = Net('Net-(R10-Pad1)')    # R8[2]/R10[1]
net_r10_b  = Net('Net-(R10-Pad2)')    # R10[2]/R12[1]
# Chain B (all DNP: R7,R9,R11,R13): VCC→R7→R9→R11→R13→drain
net_r7_2   = Net('Net-(R7-Pad2)')
net_r11_a  = Net('Net-(R11-Pad1)')    # R9[2]/R11[1]
net_r11_b  = Net('Net-(R11-Pad2)')    # R11[2]/R13[1]
# Chain C (populated: R22,R25,R29; R27=DNP): VCC→R22→R25→R27→R29→drain
net_r22_2  = Net('Net-(R22-Pad2)')
net_r25_2  = Net('Net-(R25-Pad2)')    # R25[2]/R27[1]
net_r27_2  = Net('Net-(R27-Pad2)')    # R27[2]/R29[1]
# Chain D (populated: R24,R26,R30; R28=DNP): VCC→R24→R26→R28→R30→drain
net_r24_2  = Net('Net-(R24-Pad2)')
net_r26_2  = Net('Net-(R26-Pad2)')    # R26[2]/R28[1]
net_r28_2  = Net('Net-(R28-Pad2)')    # R28[2]/R30[1]


# =============================================================================
# 4.  FOOTPRINT CONSTANTS & FACTORIES
# =============================================================================
FP_R0805     = 'Resistors_SMD:R_0805_2012Metric'
FP_R2010     = 'Resistors_SMD:R_2010_5025Metric'
FP_C0805     = 'Capacitors_SMD:C_0805_2012Metric'
FP_LED0805   = 'LEDs:LED_0805_2012Metric'
FP_SOT23     = 'TO_SOT_Packages_SMD:SOT-23'
FP_D_SMB     = 'Diode_SMD:D_SMB'
FP_SOIC14    = 'Housings_SOIC:SOIC-14_3.9x8.7mm_Pitch1.27mm'
FP_SOP4      = 'Housings_SSOP:SOP-4_4.4x2.6mm_P1.27mm'
FP_JST_PH2H  = 'Connectors_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal'
FP_HDR_1x02  = 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'
FP_HDR_2x03  = 'Pin_Headers:Pin_Header_Straight_2x03_Pitch2.54mm'
FP_FUSE_1812 = 'Fuse:Fuse_1812_4532Metric'
FP_XTAL_5032 = 'Crystal:Crystal_SMD_5032-2pin_5.0x3.2mm'


def make_res(ref, value, net_1, net_2, footprint=FP_R0805):
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
# 5.  ATTINY841 — ATtiny841-SSU  (SOIC-14, rescue-lib pin order)
#     Same reversed pin order as v4.21 rescue lib:
#       1=VCC  2=XTAL1/PB0  3=XTAL2/PB1  4=RESET/PB3  5=PB2
#       6=PA7  7=PA6        8=PA5        9=PA4        10=PA3
#      11=PA2 12=PA1       13=AREF/PA0  14=GND
# =============================================================================
attiny_t = Part('Device', 'R', dest=TEMPLATE)
attiny_t.name, attiny_t.ref_prefix = 'ATtiny841-SSU', 'U'
attiny_t.footprint = FP_SOIC14
attiny_t.pins = [
    Pin(num='1',  name='VCC'),
    Pin(num='2',  name='XTAL1/PB0'),
    Pin(num='3',  name='XTAL2/PB1'),
    Pin(num='4',  name='RESET/PB3'),
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

attiny841['VCC']        += vcc
attiny841['GND']        += gnd
attiny841['XTAL1/PB0']  += net_attiny_p2    # C4 / Y1[2]
attiny841['XTAL2/PB1']  += net_attiny_p3    # C5 / Y1[1]
attiny841['RESET/PB3']  += net_attiny_p4    # R1 pull-up / J2 ~RST
attiny841['PB2']        += dump_load_enable  # Q1 gate drive (via R14)
attiny841['PA7']        += enable            # Voltage divider top / R2 / R3
attiny841['PA6']        += net_d4_a          # D4 anode / J2-MOSI
attiny841['PA5']        += miso              # ADC5 / NTC-2 mid / J2-MISO / EXTTEMP1
attiny841['PA4']        += sck               # ADC4 / NTC-1 mid / J2-SCK
attiny841['PA3']        += net_attiny_p10    # Voltage divider mid (R3/R4)
attiny841['PA2']        += rxd0              # USART RX ← RX1
attiny841['PA1']        += txd0              # USART TX → U1 opto
attiny841['AREF/PA0']   += vref              # AZ432 reference output

# MCU decoupling
make_cap('C1', '100nF', vcc)
make_cap('C2', '1uF',   vcc)


# =============================================================================
# 6.  POWER1 / F1 / D2
#     POWER1+ → F1(mSMD150, 1.5A hold) → VCC
#     D2 (SMBJ5.0A TVS): A=GND, K=VCC — 5V unidirectional ESD clamp
# =============================================================================
power1_t = Part('Device', 'R', dest=TEMPLATE)
power1_t.name, power1_t.ref_prefix = 'Conn_01x02_Male', 'POWER'
power1_t.footprint = FP_JST_PH2H
power1_t.pins = [Pin(num='1', name='-'), Pin(num='2', name='+')]

power1 = power1_t()
power1.ref   = 'POWER1'
power1.value = 'Battery'
power1[1] += gnd
power1[2] += net_f1_bat

# F1 (mSMD150 1812 polyfuse): battery+ → F1[2] → F1[1] → VCC
f1_t = Part('Device', 'R', dest=TEMPLATE)
f1_t.name, f1_t.ref_prefix = 'mSMD150', 'F'
f1_t.footprint = FP_FUSE_1812
f1_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='K')]

f1 = f1_t()
f1.ref   = 'F1'
f1.value = 'mSMD150'
f1[1] += vcc
f1[2] += net_f1_bat

# D2 (SMBJ5.0A unidirectional TVS): A=GND, K=VCC
d2_t = Part('Device', 'R', dest=TEMPLATE)
d2_t.name, d2_t.ref_prefix = 'SMBJ5.0A', 'D'
d2_t.footprint = FP_D_SMB
d2_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='K')]

d2 = d2_t()
d2.ref   = 'D2'
d2.value = 'SMBJ5.0A'
d2[1] += gnd
d2[2] += vcc


# =============================================================================
# 7.  CRYSTAL  Y1 (8MHz ceramic resonator) + C4, C5 (22pF load caps)
#     Y1[1] → XTAL2/PB1; Y1[2] → XTAL1/PB0
# =============================================================================
y1_t = Part('Device', 'R', dest=TEMPLATE)
y1_t.name, y1_t.ref_prefix = 'Crystal', 'Y'
y1_t.footprint = FP_XTAL_5032
y1_t.pins = [Pin(num='1', name='XIN'), Pin(num='2', name='XOUT')]

y1 = y1_t()
y1.ref   = 'Y1'
y1.value = '8MHZ Ceramic Resonator'
y1['XIN']  += net_attiny_p3    # XTAL2/PB1
y1['XOUT'] += net_attiny_p2    # XTAL1/PB0

make_cap('C4', '22pF', net_attiny_p2)   # XTAL1 load cap
make_cap('C5', '22pF', net_attiny_p3)   # XTAL2 load cap


# =============================================================================
# 8.  CELL VOLTAGE MEASUREMENT  (R3, R4, D1, R2)
#     Divider: ENABLE(PA7) → R3(6.8K) → PA3 → R4(2.7K) → GND
#     D1 (AZ432ANTR-E1): FB shorted to K → fixed ~1.25V on VREF
#     R2 (1K): ENABLE → VREF (bias current for D1 shunt ref)
# =============================================================================
make_res('R3', '6.8K',   enable, net_attiny_p10)
make_res('R4', '2.7K',   net_attiny_p10, gnd)
make_res('R2', '1KOHMS', enable, vref)

# D1 (AZ432ANTR-E1, SOT-23): adjustable shunt reference (LM385Z-ADJ symbol)
#   Pin 1: FB → VREF (shorted to K → fixed 1.25V reference mode)
#   Pin 2: K  → VREF
#   Pin 3: A  → GND
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
d1.value = 'AZ432ANTR-E1'
d1['FB'] += vref
d1['K']  += vref
d1['A']  += gnd


# =============================================================================
# 9.  TEMPERATURE SENSING  (two on-board NTCs + two external connectors)
#     NTC-1 (R19, PA4/SCK/ADC4): VREF → R19 → SCK; R20(10K) → GND
#     NTC-2 (R23, PA5/MISO/ADC5): VREF → R23 → MISO; R21(10K) → GND
#     EXTTEMP1 (JST PH horizontal): pin1=MISO, pin2=VREF (external NTC)
#     REMOTE1  (pin header 1×2):    pin1=MISO, pin2=VREF (remote NTC)
# =============================================================================
r19_t = Part('Device', 'R', dest=TEMPLATE)
r19_t.name, r19_t.ref_prefix = 'Thermistor', 'R'
r19_t.footprint = FP_R0805
r19_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]

r19 = r19_t()
r19.ref   = 'R19'
r19.value = 'CMFB103F3950FANT'
r19[1] += vref
r19[2] += sck

make_res('R20', '10KOHMS', sck, gnd)           # NTC-1 lower divider

r23_t = Part('Device', 'R', dest=TEMPLATE)
r23_t.name, r23_t.ref_prefix = 'Thermistor', 'R'
r23_t.footprint = FP_R0805
r23_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]

r23 = r23_t()
r23.ref   = 'R23'
r23.value = 'CMFB103F3950FANT'
r23[1] += vref
r23[2] += miso

make_res('R21', '10KOHMS', miso, gnd)          # NTC-2 lower divider

# EXTTEMP1 (JST PH 2.0mm horizontal)
exttemp1_t = Part('Device', 'R', dest=TEMPLATE)
exttemp1_t.name, exttemp1_t.ref_prefix = 'Conn_01x02_Male', 'CONN'
exttemp1_t.footprint = FP_JST_PH2H
exttemp1_t.pins = [Pin(num='1', name='P1'), Pin(num='2', name='P2')]

exttemp1 = exttemp1_t()
exttemp1.ref   = 'EXTTEMP1'
exttemp1.value = 'Ext Temp Sensor'
exttemp1[1] += miso   # ADC5 / NTC mid
exttemp1[2] += vref   # Reference supply

# REMOTE1 (2.54mm pin header)
remote1_t = Part('Device', 'R', dest=TEMPLATE)
remote1_t.name, remote1_t.ref_prefix = 'Conn_01x02_Male', 'CONN'
remote1_t.footprint = FP_HDR_1x02
remote1_t.pins = [Pin(num='1', name='P1'), Pin(num='2', name='P2')]

remote1 = remote1_t()
remote1.ref   = 'REMOTE1'
remote1.value = 'Ext Temp Sensor'
remote1[1] += miso
remote1[2] += vref


# =============================================================================
# 10. DUMP LOAD  (4 chains × 4 pads; 3 chains × 3 × 3.3Ω 2010 populated)
#
#  Chain A — populated (R6, R8, R12); R10 = DNP (pad acts as PCB trace)
#     VCC → R6 → R8 → R10(DNP) → R12 → Q1_drain
#  Chain B — fully DNP (R7, R9, R11, R13)
#     VCC → R7(DNP) → R9(DNP) → R11(DNP) → R13(DNP) → Q1_drain
#  Chain C — populated (R22, R25, R29); R27 = DNP
#     VCC → R22 → R25 → R27(DNP) → R29 → Q1_drain
#  Chain D — populated (R24, R26, R30); R28 = DNP
#     VCC → R24 → R26 → R28(DNP) → R30 → Q1_drain
#
#  3 active chains × 3 × 3.3Ω = 3.3Ω equivalent @ 6.75W max
#
#  Q1 (AO3400A): gate=net_q1_gate, source=GND, drain=net_q1_drain
#  Gate drive: DUMP_LOAD_ENABLE → R14(510Ω) → gate; R15(10K) pull-down
#  D3 (Red LED): VCC → D3 → R17(2.2K) → Q1_drain (dump active indicator)
# =============================================================================
_DL = '3.3OHM 3/4W'

# Chain A
make_res('R6',  _DL, vcc,      net_r6_2,   footprint=FP_R2010)
make_res('R8',  _DL, net_r6_2, net_r10_a,  footprint=FP_R2010)
make_res('R10', _DL, net_r10_a, net_r10_b, footprint=FP_R2010)  # DNP in JLCPCB BOM
make_res('R12', _DL, net_r10_b, net_q1_drain, footprint=FP_R2010)

# Chain B — all DNP in JLCPCB BOM
make_res('R7',  _DL, vcc,      net_r7_2,   footprint=FP_R2010)  # DNP
make_res('R9',  _DL, net_r7_2, net_r11_a,  footprint=FP_R2010)  # DNP
make_res('R11', _DL, net_r11_a, net_r11_b, footprint=FP_R2010)  # DNP
make_res('R13', _DL, net_r11_b, net_q1_drain, footprint=FP_R2010)  # DNP

# Chain C
make_res('R22', _DL, vcc,      net_r22_2,  footprint=FP_R2010)
make_res('R25', _DL, net_r22_2, net_r25_2, footprint=FP_R2010)
make_res('R27', _DL, net_r25_2, net_r27_2, footprint=FP_R2010)  # DNP in JLCPCB BOM
make_res('R29', _DL, net_r27_2, net_q1_drain, footprint=FP_R2010)

# Chain D
make_res('R24', _DL, vcc,      net_r24_2,  footprint=FP_R2010)
make_res('R26', _DL, net_r24_2, net_r26_2, footprint=FP_R2010)
make_res('R28', _DL, net_r26_2, net_r28_2, footprint=FP_R2010)  # DNP in JLCPCB BOM
make_res('R30', _DL, net_r28_2, net_q1_drain, footprint=FP_R2010)

# Q1 (AO3400A, N-MOSFET SOT-23)
q1_t = Part('Device', 'R', dest=TEMPLATE)
q1_t.name, q1_t.ref_prefix = 'AO3400A', 'Q'
q1_t.footprint = FP_SOT23
q1_t.pins = [Pin(num='1', name='G'), Pin(num='2', name='S'), Pin(num='3', name='D')]

q1 = q1_t()
q1.ref   = 'Q1'
q1.value = 'AO3400A'
q1['G'] += net_q1_gate
q1['S'] += gnd
q1['D'] += net_q1_drain

make_res('R14', '510OHMS', dump_load_enable, net_q1_gate)
make_res('R15', '10KOHMS', net_q1_gate, gnd)

# D3 (Red LED): dump active indicator — VCC → D3 → R17 → Q1_drain
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
# 11. OPTOCOUPLER TX  (U1 EL3H7, R5)
#     PA1(TXD0) → R5(220Ω) → U1 anode → cathode → GND
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

make_res('R5', '220 OHMS', net_r5_opto, txd0)


# =============================================================================
# 12. TX1 / RX1 — UART Daisy-Chain Connectors  (JST PH S2B horizontal)
# =============================================================================
jst2h_t = Part('Device', 'R', dest=TEMPLATE)
jst2h_t.name, jst2h_t.ref_prefix = 'Conn_01x02_Male', 'CONN'
jst2h_t.footprint = FP_JST_PH2H
jst2h_t.pins = [Pin(num='1', name='P1'), Pin(num='2', name='P2')]

tx1 = jst2h_t()
tx1.ref   = 'TX1'
tx1.value = 'TX Connector'
tx1[1] += net_tx1_e
tx1[2] += net_tx1_c

rx1 = jst2h_t()
rx1.ref   = 'RX1'
rx1.value = 'RX Connector'
rx1[1] += rxd0
rx1[2] += vcc

make_res('R16', '2.2KOHMS', gnd, rxd0)   # RXD0 pull-down


# =============================================================================
# 13. J2 — AVR ISP-6 Programming Header  (2×3, 2.54mm)
#      Pin 1: MISO  → PA5 / MISO net
#      Pin 2: VCC   → VCC
#      Pin 3: SCK   → PA4 / SCK net
#      Pin 4: MOSI  → PA6 / D4 anode
#      Pin 5: ~RST  → ~RST/PB3
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
j2['MISO'] += miso
j2['VCC']  += vcc
j2['SCK']  += sck
j2['MOSI'] += net_d4_a
j2['~RST'] += net_attiny_p4
j2['GND']  += gnd

make_res('R1', '10KOHMS', vcc, net_attiny_p4)   # ~RST pull-up


# =============================================================================
# 14. STATUS LED  D4 (Blue): PA6 → D4_A → D4_K → R18(2.2K) → GND
# =============================================================================
d4_t = Part('Device', 'R', dest=TEMPLATE)
d4_t.name, d4_t.ref_prefix = 'LED', 'D'
d4_t.footprint = FP_LED0805
d4_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]

d4 = d4_t()
d4.ref   = 'D4'
d4.value = 'Blue'
d4['A'] += net_d4_a
d4['K'] += net_d4_k

make_res('R18', '2.2KOHMS', gnd, net_d4_k)


# =============================================================================
# 15. OUTPUT: KiCad netlist  +  CSV BOM
# =============================================================================

def generate_csv_bom(filename: str = 'modulev440_BOM.csv') -> None:
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


generate_netlist(filename='modulev440.net')
print('✅  Netlist saved  →  modulev440.net')
generate_csv_bom(filename='modulev440_BOM.csv')
