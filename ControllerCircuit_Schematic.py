"""
ControllerCircuit_Schematic.py  —  DIYBMS ESP32 Controller  Rev 1.1
====================================================================
SKiDL script to regenerate the KiCad netlist and a grouped BOM for
the DIYBMS ESP32 Controller designed by Stuart Pittaway.

Connectivity source:  ControllerCircuit.net  (KiCad 5 / Eeschema export,
                       schematic date 2021-04-08, rev 1.1)
Component reference:  ComponentListBOM.md  (Rev 4.61 BOM)

All components aligned to Rev 4.61 BOM (ComponentListBOM.md).
Previous Rev 1.1 values have been corrected:
  R1/R17/R21/R25 → 220R | R4/R10/R14 → 560R | R8 → 120R
  R11/R15 → 51K | R20 → 1M | R22/R29/R31/R32 → 10K (active)
  R23/R30 → 10R | R24 → 22K
  U1 → TXS0102DCU (level translator) | U3 → TCA6416APWR
  U7 → SN65HVD1050D (CAN transceiver, new) | U8 → INA229
  U9/U12 → AQY282SX | C5 → 22uF 1206 | J5 → 2-pin terminal
  C8/C9/J9 → active (removed DNP) | C12/C13/C14/Q4 added
  D6 → MHPC3528CRGBCT (DNP)

Usage:
    python ControllerCircuit_Schematic.py
Outputs:
    ControllerCircuit_skidl.net  — KiCad-compatible netlist
    ControllerCircuit_BOM.csv   — grouped Bill of Materials
"""

import os
import csv
from collections import defaultdict

# ==========================================
# 1.  SETUP & PATHS  (edit to match your KiCad install)
# ==========================================
app_symbols    = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
app_footprints = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
user_config    = '/Users/user/Documents/KiCad/8.0'   # adjust as needed

os.environ['KICAD_SYMBOL_DIR']  = app_symbols
os.environ['KICAD6_SYMBOL_DIR'] = app_symbols
os.environ['KICAD7_SYMBOL_DIR'] = app_symbols
os.environ['KICAD8_SYMBOL_DIR'] = app_symbols

os.environ['KICAD_FOOTPRINT_DIR'] = app_footprints
os.environ['KICAD8_FOOTPRINT_DIR'] = app_footprints

from skidl import *   # noqa: E402

lib_search_paths[KICAD].extend([app_symbols, user_config])
footprint_search_paths[KICAD].append(app_footprints)
set_default_tool(KICAD)


# ==========================================
# 2.  POWER RAILS
# ==========================================
gnd     = Net('GND')
v3v3    = Net('+3V3')      # 3.3 V output of U6 AMS1117-3.3
v5      = Net('+5V')       # raw 5 V input (from J5)
fused5v = Net('FUSED5V')   # 5 V after fuse + reverse-polarity FET


# ==========================================
# 3.  ALL SIGNAL NETS  (names match the .net file exactly)
# ==========================================
# Reset
reset_net     = Net('/RESET')

# ESP32 I/O  ─  all names match netlist signal names
io2           = Net('/IO2')
io4           = Net('/IO4')
io5           = Net('/IO5')
io21          = Net('/IO21')
io22          = Net('/IO22')
io25          = Net('/IO25')
io26          = Net('/IO26')   # i2c SDA (per schematic labelling)
io27          = Net('/IO27')   # i2c SCL
io32          = Net('/IO32')
io33          = Net('/IO33')
io34_in       = Net('/IO34_INPUT')
io35_in       = Net('/IO35_INPUT')
io36_in       = Net('/IO36_INPUT')
io39_in       = Net('/IO39_INPUT')
esp3v3        = Net('/ESP3V3')  # ESP32 3V3 pin (internal)
avrisp_reset  = Net('/AVRISP_RESET')

# SPI buses
vspi_mosi     = Net('/VSPI_MOSI')   # IO23
vspi_miso     = Net('/VSPI_MISO')   # IO19
vspi_clk      = Net('/VSPI_CLK')    # IO18
hspi_mosi     = Net('/HSPI_MOSI')   # IO13
hspi_miso     = Net('/HSPI_MISO')   # IO12
hspi_clk      = Net('/HSPI_CLK')    # IO14

# Display
display_dc    = Net('/DISPLAY_DC')  # IO15
display_led   = Net('/DISPLAY_LED') # backlight PWM via U8

# CAN bus
canbus_tx     = Net('/CANBUS_TX')   # IO16
canbus_rx     = Net('/CANBUS_RX')   # IO17
canbus_s      = Net('/CANBUS_S')    # silent mode control

# RS-485
# (IO21 = RS485 RX output, IO22 = RS485 TX input, IO25 = RE/DE combined)

# I/O expander outputs (U3 TCA6408)
relay1        = Net('/RELAY1')      # U3 P4 → relay K1 driver
relay2        = Net('/RELAY2')      # U3 P5 → relay K2 driver
relay3_ssr    = Net('/RELAY3_SSR')  # U3 P6 → SSR U9
relay4_ssr    = Net('/RELAY4_SSR')  # U3 P7 → SSR U12
ext_io_a      = Net('/EXT_IO_A')    # U3 P0 → J4 pin 1
ext_io_b      = Net('/EXT_IO_B')    # U3 P1 → J4 pin 2
ext_io_c      = Net('/EXT_IO_C')    # U3 P2 → J4 pin 3
ext_io_d      = Net('/EXT_IO_D')    # U3 P3 → J4 pin 4

# I/O expander outputs (U8 TCA9534)
blue_led      = Net('/BLUE_LED')    # U8 P0
red_led       = Net('/RED_LED')     # U8 P1
green_led     = Net('/GREEN_LED')   # U8 P2
display_led_n = display_led         # reuse net — U8 P3
sw1out        = Net('/SW1OUTPUT')   # U8 P4 (SW1 debounced)
sw2out        = Net('/SW2OUTPUT')   # U8 P6 (SW2 debounced)
# U8 P5 = /CANBUS_S

# ── Internal / intermediate nets ──────────────────────────────────────
# Power path
net_f1_q3     = Net('Net-(F1-Pad1)')     # fuse → Q3 drain
net_c2_1      = Net('Net-(C2-Pad1)')     # CAN VCC bypass + JP5 select

# CAN bus lines
net_canl      = Net('Net-(D8-Pad1)')     # CANL (U1 CANL, D8 K1, JP1 pin 1, J7 pin 4)
net_canh      = Net('Net-(D8-Pad2)')     # CANH (U1 CANH, D8 K2, R6 pin 2, J7 pin 3)
net_jp1_2     = Net('Net-(JP1-Pad2)')    # R6 low side → CAN termination enable

# RS-485 lines
net_rs485_a   = Net('Net-(J1-Pad2)')     # RS-485 A (U5 A, R9 pin 1, J1 pin 2)
net_rs485_b   = Net('Net-(J1-Pad3)')     # RS-485 B (U5 B, JP4 pin 1, J1 pin 3)
net_jp4_2     = Net('Net-(JP4-Pad2)')    # R9 high side → RS-485 term enable

# Relay 1 (K1) nodes
net_q1_g      = Net('Net-(Q1-Pad1)')     # Q1 gate, R10 pin 1, R11 pin 2
net_d2_2      = Net('Net-(D2-Pad2)')     # Q1 drain, K1 A2, D2 anode, D3 cathode
net_d3_2      = Net('Net-(D3-Pad2)')     # D3 anode → R12 → FUSED5V

# Relay 2 (K2) nodes
net_q2_g      = Net('Net-(Q2-Pad1)')     # Q2 gate, R14 pin 1, R15 pin 2
net_d4_1      = Net('Net-(D4-Pad1)')     # Q2 drain, K2 A2, D4 cathode, D5 anode
net_d4_2      = Net('Net-(D4-Pad2)')     # D4 anode → R13 → FUSED5V

# Relay J2 / J3 terminal nodes
net_j2_1      = Net('Net-(J2-Pad1)')     # K1 COM ↔ J2 pin 1
net_j2_2      = Net('Net-(J2-Pad2)')     # K1 NC  ↔ J2 pin 2
net_j2_3      = Net('Net-(J2-Pad3)')     # K1 NO  ↔ J2 pin 3
net_j3_1      = Net('Net-(J3-Pad1)')     # K2 COM ↔ J3 pin 1
net_j3_2      = Net('Net-(J3-Pad2)')     # K2 NC  ↔ J3 pin 2
net_j3_3      = Net('Net-(J3-Pad3)')     # K2 NO  ↔ J3 pin 3

# SSR J12 nodes
net_j12_1     = Net('Net-(J12-Pad1)')    # U9 pin 3 ↔ J12 pin 1
net_j12_2     = Net('Net-(J12-Pad2)')    # U9 pin 4 ↔ J12 pin 2
net_j12_3     = Net('Net-(J12-Pad3)')    # U12 pin 3 ↔ J12 pin 3
net_j12_4     = Net('Net-(J12-Pad4)')    # U12 pin 4 ↔ J12 pin 4

# SSR drive nodes
net_r18_1     = Net('Net-(R18-Pad1)')    # U9 LED+ ← R18 ← /RELAY3_SSR
net_r25_1     = Net('Net-(R25-Pad1)')    # U12 LED+ ← R25 ← /RELAY4_SSR

# Optocoupler U2 nodes
net_r3_1      = Net('Net-(R3-Pad1)')     # U2 LED anode, R3 pin 1
net_tx1_1     = Net('Net-(TX1-Pad1)')    # U2 collector, TX1 pin 1
net_tx1_2     = Net('Net-(TX1-Pad2)')    # U2 emitter,   TX1 pin 2

# RGB LED D1 intermediate nodes
net_d1_rk     = Net('Net-(D1-Pad1)')     # D1 pin 1 (RK) → R17 → /GREEN_LED
net_d1_gk     = Net('Net-(D1-Pad2)')     # D1 pin 2 (GK) → R4  → /RED_LED
net_d1_bk     = Net('Net-(D1-Pad3)')     # D1 pin 3 (BK) → R1  → /BLUE_LED
#   NOTE: red/green intentionally swapped on schematic to match component
#         footprint — per Stuart Pittaway's design note.

# ESTOP pull-up
net_j10_1     = Net('Net-(J10-Pad1)')    # U8 P7, R24 pin 1, J10 pin 1

# LCD backlight
net_lcd_led   = Net('Net-(LCD1-Pad7)')   # LCD LED pin → R21 → /DISPLAY_LED

# microSD DAT1/DAT2 (not used, single-wire SPI mode)
net_j15_1     = Net('Net-(J15-Pad1)')    # SD DAT2 — NC
net_j15_8     = Net('Net-(J15-Pad8)')    # SD DAT1 — NC

# Button debounce mid-points
net_sw1_node  = Net('Net-(R26-Pad2)')    # R7 pin 1, R26 pin 2, SW1 pin 1
net_sw2_node  = Net('Net-(R27-Pad1)')    # R27 pin 1, R28 pin 2, SW2 pin 1

# DNP: ATtiny841 + associated connector/components
net_d7_2      = Net('Net-(D7-Pad2)')     # D7 anode (DNP), R8 pin 1, Q3 gate
net_d6_2      = Net('Net-(D6-Pad2)')     # D6 anode (DNP), R22 pin 1
net_r22_2     = Net('Net-(R22-Pad2)')    # R22 pin 2 (DNP), U10 PA6
net_j6_1      = Net('Net-(J6-Pad1)')     # J6 pin 1 (DNP), U10 PA5
net_j6_5      = Net('Net-(J6-Pad5)')     # J6 pin 5 (DNP), R23 pin 2, U10 RESET
net_j9_1      = Net('Net-(J9-Pad1)')     # ATtiny PA0/AREF (DNP)
net_j9_2      = Net('Net-(J9-Pad2)')     # ATtiny PA1 (DNP)
net_j9_4      = Net('Net-(J9-Pad4)')     # ATtiny PB0 (DNP)
net_j9_5      = Net('Net-(J9-Pad5)')     # ATtiny PB2 (DNP)
net_j9_6      = Net('Net-(J9-Pad6)')     # ATtiny PA4 (DNP)

# ESP32 floating pins (not connected to anything in this design)
net_u4_23     = Net('Net-(U4-Pad23)')    # TXD0 — NC
net_u4_24     = Net('Net-(U4-Pad24)')    # RXD0 — NC
net_u4_16     = Net('Net-(U4-Pad16)')    # SD2  — NC
net_u4_17     = Net('Net-(U4-Pad17)')    # SD3  — NC
net_u4_18     = Net('Net-(U4-Pad18)')    # CMD  — NC
net_u4_36     = Net('Net-(U4-Pad36)')    # SD1  — NC
net_u4_37     = Net('Net-(U4-Pad37)')    # SD0  — NC
net_u4_38     = Net('Net-(U4-Pad38)')    # CLK  — NC


# ==========================================
# 4.  HELPER FACTORIES
# ==========================================
FP_R0805 = 'Resistor_SMD:R_0805_2012Metric'
FP_C0805 = 'Capacitor_SMD:C_0805_2012Metric'
FP_LED0603 = 'LED_SMD:LED_0603_1608Metric_Pad1.05x0.95mm_HandSolder'


def make_res(ref, value, net_1, net_2):
    """Create an 0805 resistor with an explicit reference designator."""
    r = Part('Device', 'R', value=value, footprint=FP_R0805)
    r.ref   = ref
    r.value = value
    r[1] += net_1
    r[2] += net_2
    return r


def make_cap(ref, value, net_pos, net_neg=None, footprint=FP_C0805):
    """Create a capacitor with an explicit reference designator."""
    c = Part('Device', 'C', value=value, footprint=footprint)
    c.ref   = ref
    c.value = value
    c[1] += net_pos
    c[2] += (net_neg if net_neg is not None else gnd)
    return c


def make_diode(ref, value, net_anode, net_cathode,
               footprint='Diode_SMD:D_MiniMELF'):
    """Create a diode. Pin 1 = Cathode, Pin 2 = Anode (Device:D convention)."""
    d = Part('Device', 'D', value=value, footprint=footprint)
    d.ref   = ref
    d.value = value
    d[1] += net_cathode   # K
    d[2] += net_anode     # A
    return d


def make_led(ref, value, net_anode, net_cathode, footprint=FP_LED0603):
    """Create an LED. Pin 1 = Cathode (K), Pin 2 = Anode (A)."""
    d = Part('Device', 'LED', value=value, footprint=footprint)
    d.ref   = ref
    d.value = value
    d[1] += net_cathode   # K
    d[2] += net_anode     # A
    return d


# ==========================================
# 5.  PASSIVE COMPONENTS — CAPACITORS  (C1–C11, +DNP C8,C9)
#
#  Values from .net file:
#  C1,C2,C5,C6 = 100nF / C3,C4 = 22uF 6.3V / C7,C10,C11 = 1uF
#  C8=100nF (DNP), C9=1uF (DNP)
#  NOTE: C5 = 100nF in .net vs 22uF in the Rev 4.61 BOM.
# ==========================================
make_cap('C1',  '100nF',     v3v3)          # +3V3 bulk decoupling
make_cap('C2',  '100nF',     net_c2_1)      # CAN VCC bypass
make_cap('C3',  '22uF 6.3V', fused5v,       # LDO input bulk cap
         footprint='Capacitor_Tantalum_SMD:CP_EIA-3216-18_Kemet-A_Pad1.58x1.35mm_HandSolder')
make_cap('C4',  '22uF 6.3V', v3v3,          # LDO output bulk cap
         footprint='Capacitor_Tantalum_SMD:CP_EIA-3216-18_Kemet-A_Pad1.58x1.35mm_HandSolder')
make_cap('C5',  '22uF',      v3v3,
         footprint='Capacitor_SMD:C_1206_3216Metric')   # bulk decoupling
make_cap('C6',  '100nF',     v3v3)          # U3 TCA6408 decoupling
make_cap('C7',  '1uF',       sw1out)        # SW1 debounce filter cap
make_cap('C10', '1uF',       v3v3)          # general +3V3 decoupling
make_cap('C11', '1uF',       sw2out)        # SW2 debounce filter cap
make_cap('C12', '0.1uF-100V', v3v3,
         footprint='Capacitor_SMD:C_0805_2012Metric')   # 100V rated bypass
make_cap('C13', '1uF',       v3v3)   # additional +3V3 decoupling
make_cap('C14', '100nF',     v3v3)   # additional +3V3 decoupling

make_cap('C8',  '100nF', v3v3)   # Rev 4.61: active decoupling cap
make_cap('C9',  '100nF', v3v3)   # Rev 4.61: active decoupling cap


# ==========================================
# 6.  POWER INPUT & SUPPLY CHAIN
#     J5 (+5V,GND) → F1 (polyfuse) → Q3 (P-FET, reverse polarity) → FUSED5V
#     FUSED5V → U6 (AMS1117-3.3) → +3V3
# ==========================================

# --- J5: 2-pin power input screw terminal (LCSC C395878)
j5_t = Part('Device', 'R', dest=TEMPLATE)
j5_t.name, j5_t.ref_prefix = 'ScrewTerminal', 'J'
j5_t.footprint = 'ControllerCircuit:Terminal-Block_3.81_2P-LCSC_C395878'
j5_t.pins = [Pin(num='1', name='Pin_1'), Pin(num='2', name='Pin_2')]
j5 = j5_t()
j5.ref   = 'J5'
j5.value = 'ScrewTerminal'
j5['Pin_1'] += v5
j5['Pin_2'] += gnd

# --- F1: Polyfuse 1.85A
f1_t = Part('Device', 'R', dest=TEMPLATE)
f1_t.name, f1_t.ref_prefix = 'Polyfuse', 'F'
f1_t.footprint = 'Fuse:Fuse_2920_7451Metric'
f1_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='B')]
f1 = f1_t()
f1.ref   = 'F1'
f1.value = 'Fuse, 1.85A'
f1['A'] += net_f1_q3   # to Q3 drain
f1['B'] += v5           # from +5V input (net +5V connects F1[2] and J5[1,2])

# --- Q3: AO3401A P-channel MOSFET (reverse-polarity protection)
q3_t = Part('Device', 'R', dest=TEMPLATE)
q3_t.name, q3_t.ref_prefix = 'AO3401A', 'Q'
q3_t.footprint = 'Package_TO_SOT_SMD:SOT-23'
q3_t.pins = [
    Pin(num='1', name='G'),   # Gate
    Pin(num='2', name='S'),   # Source
    Pin(num='3', name='D'),   # Drain
]
q3 = q3_t()
q3.ref   = 'Q3'
q3.value = 'AO3401A'
q3['G'] += net_d7_2    # gate driven by D7 (DNP zener) + R8 pulldown
q3['S'] += fused5v     # source → FUSED5V (properly forward biased in normal use)
q3['D'] += net_f1_q3   # drain ← fuse output

# --- D7 (DNP): Zener clamp on Q3 gate — DONOTPLACE
d7_t = Part('Device', 'R', dest=TEMPLATE)
d7_t.name, d7_t.ref_prefix = 'D_Zener_Small', 'D'
d7_t.footprint = 'Diode_THT:D_5W_P10.16mm_Horizontal'
d7_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]
d7 = d7_t()   # DNP
d7.ref   = 'D7'
d7.value = 'D_Zener_Small'
d7['K'] += fused5v    # cathode → FUSED5V
d7['A'] += net_d7_2   # anode  → Q3 gate

# --- R8: 100R pull-down on Q3 gate (between gate node and GND)
#     NOTE: R8 = 100R in .net vs 120R in Rev 4.61 BOM
make_res('R8', '120R', net_d7_2, gnd)

# --- U6: AMS1117-3.3 LDO (SOT-223)
u6_t = Part('Device', 'R', dest=TEMPLATE)
u6_t.name, u6_t.ref_prefix = 'AMS1117-3.3', 'U'
u6_t.footprint = 'Package_TO_SOT_SMD:SOT-223-3_TabPin2'
u6_t.pins = [
    Pin(num='1', name='GND'),
    Pin(num='2', name='VO'),
    Pin(num='3', name='VI'),
]
u6 = u6_t()
u6.ref   = 'U6'
u6.value = 'AMS1117-3.3'
u6['GND'] += gnd
u6['VO']  += v3v3
u6['VI']  += fused5v


# ==========================================
# 7.  ESP32-DEVKITC-32D  (U4) — all 38 pins
# ==========================================
u4_t = Part('Device', 'R', dest=TEMPLATE)
u4_t.name, u4_t.ref_prefix = 'ESP32-DEVKITC-32D', 'U'
u4_t.footprint = 'ControllerCircuit:MODULE_ESP32-DEVKITC-32D'
u4_t.pins = [
    Pin(num='1',  name='3V3'),       Pin(num='2',  name='EN'),
    Pin(num='3',  name='SENSOR_VP'), Pin(num='4',  name='SENSOR_VN'),
    Pin(num='5',  name='IO34'),      Pin(num='6',  name='IO35'),
    Pin(num='7',  name='IO32'),      Pin(num='8',  name='IO33'),
    Pin(num='9',  name='IO25'),      Pin(num='10', name='IO26'),
    Pin(num='11', name='IO27'),      Pin(num='12', name='IO14'),
    Pin(num='13', name='IO12'),      Pin(num='14', name='GND1'),
    Pin(num='15', name='IO13'),      Pin(num='16', name='SD2'),
    Pin(num='17', name='SD3'),       Pin(num='18', name='CMD'),
    Pin(num='19', name='EXT_5V'),    Pin(num='20', name='GND3'),
    Pin(num='21', name='IO23'),      Pin(num='22', name='IO22'),
    Pin(num='23', name='TXD0'),      Pin(num='24', name='RXD0'),
    Pin(num='25', name='IO21'),      Pin(num='26', name='GND2'),
    Pin(num='27', name='IO19'),      Pin(num='28', name='IO18'),
    Pin(num='29', name='IO5'),       Pin(num='30', name='IO17'),
    Pin(num='31', name='IO16'),      Pin(num='32', name='IO4'),
    Pin(num='33', name='IO0'),       Pin(num='34', name='IO2'),
    Pin(num='35', name='IO15'),      Pin(num='36', name='SD1'),
    Pin(num='37', name='SD0'),       Pin(num='38', name='CLK'),
]
u4 = u4_t()
u4.ref   = 'U4'
u4.value = 'ESP32-DEVKITC-32D'

# Power
u4['3V3']    += esp3v3    # internal 3V3 (not connected to external +3V3 rail)
u4['GND1']   += gnd
u4['GND2']   += gnd
u4['GND3']   += gnd
u4['EXT_5V'] += fused5v   # powers the ESP module from FUSED5V

# Reset / enable
u4['EN'] += reset_net

# SPI buses
u4['IO23'] += vspi_mosi   # VSPI MOSI
u4['IO19'] += vspi_miso   # VSPI MISO
u4['IO18'] += vspi_clk    # VSPI CLK
u4['IO13'] += hspi_mosi   # HSPI MOSI
u4['IO12'] += hspi_miso   # HSPI MISO
u4['IO14'] += hspi_clk    # HSPI CLK

# Display
u4['IO15'] += display_dc
u4['IO4']  += io4           # Touch CS (T_CS)
u4['IO5']  += io5           # SD CS (SD_CS)

# CAN bus
u4['IO16'] += canbus_tx
u4['IO17'] += canbus_rx

# RS-485 (using IO21 = receive, IO22 = transmit, IO25 = RE+DE combined)
u4['IO21'] += io21    # RS485 R  (receive data output)
u4['IO22'] += io22    # RS485 D  (transmit data input)
u4['IO25'] += io25    # RS485 RE/DE combined

# I2C bus
u4['IO26'] += io26    # i2c SDA
u4['IO27'] += io27    # i2c SCL

# GPIO inputs
u4['SENSOR_VP'] += io36_in    # T_IRQ (LCD touch interrupt)
u4['SENSOR_VN'] += io39_in    # TCA6408 ~INT~
u4['IO34']      += io34_in    # TCA9534 ~INT~
u4['IO35']      += io35_in    # J14 header debug pin
u4['IO32']      += io32       # IO32 (optocoupler drive + ATtiny TXD)
u4['IO33']      += io33       # J14 header debug pin
u4['IO2']       += io2        # RX1 receive data
u4['IO0']       += avrisp_reset   # AVRISP reset / boot mode

# Misc GPIO
u4['IO25'] += io25    # (already assigned above — RE/DE)

# Floating pins (no connection in this design)
u4['TXD0']  += net_u4_23
u4['RXD0']  += net_u4_24
u4['SD2']   += net_u4_16
u4['SD3']   += net_u4_17
u4['CMD']   += net_u4_18
u4['SD1']   += net_u4_36
u4['SD0']   += net_u4_37
u4['CLK']   += net_u4_38

# Pull-up resistors on inputs
# R19 pull-up defined in section 15 (Q4 block)
make_res('R20', '10K', io34_in, v3v3)  # TCA9534 ~INT~ pull-up


# ==========================================
# 8.  CAN BUS TRANSCEIVER: TJA1057GT/3  (U1)
#     NOTE: Rev 4.61 BOM lists SN65HVD1050D — different IC, same function.
#     Wiring matches the .net TJA1051T-3 libpart pinout.
# ==========================================
# U1: TXS0102DCU — 2-ch bidirectional voltage-level translator (VSSOP-8)
# Used to level-shift I2C between ESP32 (3.3V) and U3 TCA6416APWR (5V port side)
u1_t = Part('Device', 'R', dest=TEMPLATE)
u1_t.name, u1_t.ref_prefix = 'TXS0102DCU', 'U'
u1_t.footprint = 'Package_SO:VSSOP-8_2.3x2mm_P0.5mm'
u1_t.pins = [
    Pin(num='1', name='VCCA'),  Pin(num='2', name='A1'),
    Pin(num='3', name='A2'),    Pin(num='4', name='OE'),
    Pin(num='5', name='B2'),    Pin(num='6', name='B1'),
    Pin(num='7', name='VCCB'),  Pin(num='8', name='GND'),
]
# New net names for 5V-side I2C (post-translator, to U3 port supply domain)
i2c_sda_5v = Net('/I2C_SDA_5V')
i2c_scl_5v = Net('/I2C_SCL_5V')
u1 = u1_t()
u1.ref   = 'U1'
u1.value = 'TXS0102DCU'
u1['VCCA'] += v3v3       # 3.3V side supply
u1['VCCB'] += fused5v    # 5V side supply
u1['GND']  += gnd
u1['OE']   += v3v3       # always enabled
u1['A1']   += io26       # SDA 3.3V side
u1['A2']   += io27       # SCL 3.3V side
u1['B1']   += i2c_sda_5v # SDA 5V side → U3
u1['B2']   += i2c_scl_5v # SCL 5V side → U3

# --- D8: NUP2105LT1G CAN bus ESD protector (SOT-23, dual TVS)
d8_t = Part('Device', 'R', dest=TEMPLATE)
d8_t.name, d8_t.ref_prefix = 'NUP2105LT1G', 'D'
d8_t.footprint = 'Package_TO_SOT_SMD:SOT-23'
d8_t.pins = [
    Pin(num='1', name='K1'),  # CANL side
    Pin(num='2', name='K2'),  # CANH side
    Pin(num='3', name='A'),   # common anode → GND
]
d8 = d8_t()
d8.ref   = 'D8'
d8.value = 'NUP2105LT1G'
d8['K1'] += net_canl
d8['K2'] += net_canh
d8['A']  += gnd

# --- U7: SN65HVD1050D — CAN transceiver (SOIC-8)  [Rev 4.61: moved from U1]
u7_t = Part('Device', 'R', dest=TEMPLATE)
u7_t.name, u7_t.ref_prefix = 'SN65HVD1050D', 'U'
u7_t.footprint = 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
u7_t.pins = [
    Pin(num='1', name='D'),     # TXD input
    Pin(num='2', name='GND'),
    Pin(num='3', name='VCC'),
    Pin(num='4', name='R'),     # RXD output
    Pin(num='5', name='Vref'),  # reference voltage output
    Pin(num='6', name='CANL'),
    Pin(num='7', name='CANH'),
    Pin(num='8', name='RS'),    # slope/silent control
]
u7 = u7_t()
u7.ref   = 'U7'
u7.value = 'SN65HVD1050D'
u7['D']    += canbus_tx
u7['GND']  += gnd
u7['VCC']  += net_c2_1    # CAN VCC (via JP5 selector)
u7['R']    += canbus_rx
u7['Vref'] += v3v3
u7['CANL'] += net_canl
u7['CANH'] += net_canh
u7['RS']   += canbus_s

# --- JP1: CAN termination solder jumper (normally open — bridge to add 120R)
jp1_t = Part('Device', 'R', dest=TEMPLATE)
jp1_t.name, jp1_t.ref_prefix = 'OptTermination', 'JP'
jp1_t.footprint = 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm'
jp1_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='B')]
jp1 = jp1_t()
jp1.ref   = 'JP1'
jp1.value = 'OptTermination'
jp1['A'] += net_canl
jp1['B'] += net_jp1_2

# --- R6: 120R CAN termination resistor (in series with JP1)
make_res('R6', '120R', net_jp1_2, net_canh)

# --- JP5: CAN voltage selector (3-pin jumper, default pins 1+2 = FUSED5V)
jp5_t = Part('Device', 'R', dest=TEMPLATE)
jp5_t.name, jp5_t.ref_prefix = 'CANBUS Volt Select', 'JP'
jp5_t.footprint = 'Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm'
jp5_t.pins = [
    Pin(num='1', name='A'),    # FUSED5V (default selected)
    Pin(num='2', name='C'),    # to CAN VCC (net_c2_1)
    Pin(num='3', name='B'),    # +3V3 (alternative)
]
jp5 = jp5_t()
jp5.ref   = 'JP5'
jp5.value = 'CANBUS Volt Select'
jp5['A'] += fused5v
jp5['C'] += net_c2_1
jp5['B'] += v3v3

# --- J7: 4-pin CAN bus terminal (1=FUSED5V, 2=GND, 3=CANH, 4=CANL)
j7_t = Part('Device', 'R', dest=TEMPLATE)
j7_t.name, j7_t.ref_prefix = 'ScrewTerminal', 'J'
j7_t.footprint = 'ControllerCircuit:Terminal-Block_3.81_4P_LCSC_C395880'
j7_t.pins = [Pin(num=str(i), name=f'Pin_{i}') for i in range(1, 5)]
j7 = j7_t()
j7.ref   = 'J7'
j7.value = 'ScrewTerminal'
j7['Pin_1'] += fused5v
j7['Pin_2'] += gnd
j7['Pin_3'] += net_canh
j7['Pin_4'] += net_canl


# ==========================================
# 9.  RS-485 TRANSCEIVER: SN65HVD75DR  (U5)
# ==========================================
u5_t = Part('Device', 'R', dest=TEMPLATE)
u5_t.name, u5_t.ref_prefix = 'SN65HVD75DR', 'U'
u5_t.footprint = 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
u5_t.pins = [
    Pin(num='1', name='R'),    # receive output
    Pin(num='2', name='RE'),   # receive enable (active low)
    Pin(num='3', name='DE'),   # driver enable (active high)
    Pin(num='4', name='D'),    # data input (transmit)
    Pin(num='5', name='GND'),
    Pin(num='6', name='A'),    # RS-485 A (non-inverting)
    Pin(num='7', name='B'),    # RS-485 B (inverting)
    Pin(num='8', name='VCC'),
]
u5 = u5_t()
u5.ref   = 'U5'
u5.value = 'SN65HVD75DR'
u5['R']   += io21         # receive data → ESP32 IO21
u5['RE']  += io25         # RE+DE tied together for half-duplex
u5['DE']  += io25
u5['D']   += io22         # transmit data ← ESP32 IO22
u5['GND'] += gnd
u5['A']   += net_rs485_a
u5['B']   += net_rs485_b
u5['VCC'] += v3v3

# --- JP4: RS-485 termination solder jumper
jp4_t = Part('Device', 'R', dest=TEMPLATE)
jp4_t.name, jp4_t.ref_prefix = 'OptTermination', 'JP'
jp4_t.footprint = 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm'
jp4_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='B')]
jp4 = jp4_t()
jp4.ref   = 'JP4'
jp4.value = 'OptTermination'
jp4['A'] += net_rs485_b
jp4['B'] += net_jp4_2

# --- R9: 120R RS-485 termination resistor (in series with JP4)
make_res('R9', '120R', net_jp4_2, net_rs485_a)

# --- J1: 4-pin RS-485 terminal (1=FUSED5V, 2=RS485-A, 3=RS485-B, 4=GND)
j1_t = Part('Device', 'R', dest=TEMPLATE)
j1_t.name, j1_t.ref_prefix = 'ScrewTerminal', 'J'
j1_t.footprint = 'ControllerCircuit:Terminal-Block_3.81_4P_LCSC_C395880'
j1_t.pins = [Pin(num=str(i), name=f'Pin_{i}') for i in range(1, 5)]
j1 = j1_t()
j1.ref   = 'J1'
j1.value = 'ScrewTerminal'
j1['Pin_1'] += fused5v
j1['Pin_2'] += net_rs485_a
j1['Pin_3'] += net_rs485_b
j1['Pin_4'] += gnd

# --- R2: 2K2 pull-down on ESP32 IO2 (RS485 RX module)
make_res('R2', '2K2', gnd, io2)

# --- RX1: JST PH receive connector (IO2 = module RX input)
rx1_t = Part('Device', 'R', dest=TEMPLATE)
rx1_t.name, rx1_t.ref_prefix = 'Receive', 'RX'
rx1_t.footprint = 'Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal'
rx1_t.pins = [Pin(num='1', name='Pin_1'), Pin(num='2', name='Pin_2')]
rx1 = rx1_t()
rx1.ref   = 'RX1'
rx1.value = 'Receive'
rx1['Pin_1'] += io2
rx1['Pin_2'] += v3v3   # +3V3 supply to external module


# ==========================================
# 10.  OPTOCOUPLER: EL3H7(B)(TA)-G  (U2)  [PC817 pinout]
#      Drives TX1 output connector from ESP32 IO32 via R3.
# ==========================================
u2_t = Part('Device', 'R', dest=TEMPLATE)
u2_t.name, u2_t.ref_prefix = 'EL3H7(B)(TA)-G', 'U'
u2_t.footprint = 'Package_SO:SOP-4_4.4x2.6mm_P1.27mm'
u2_t.pins = [
    Pin(num='1', name='A'),    # LED anode
    Pin(num='2', name='K'),    # LED cathode → GND
    Pin(num='3', name='C'),    # transistor collector
    Pin(num='4', name='E'),    # transistor emitter
]
u2 = u2_t()
u2.ref   = 'U2'
u2.value = 'EL3H7(B)(TA)-G'
u2['A'] += net_r3_1   # anode ← R3 ← IO32
u2['K'] += gnd
u2['C'] += net_tx1_1  # collector → TX1 pin 1
u2['E'] += net_tx1_2  # emitter  → TX1 pin 2

# --- R3: 180R current-limit resistor for U2 LED (IO32 → R3 → U2 LED anode)
make_res('R3', '180R', io32, net_r3_1)

# --- TX1: JST PH transmit connector
tx1_t = Part('Device', 'R', dest=TEMPLATE)
tx1_t.name, tx1_t.ref_prefix = 'Transmit', 'TX'
tx1_t.footprint = 'Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal'
tx1_t.pins = [Pin(num='1', name='Pin_1'), Pin(num='2', name='Pin_2')]
tx1 = tx1_t()
tx1.ref   = 'TX1'
tx1.value = 'Transmit'
tx1['Pin_1'] += net_tx1_1
tx1['Pin_2'] += net_tx1_2


# ==========================================
# 11.  I2C EXPANDER: TCA6408APWR  (U3, 16-pin TSSOP)
#      Controls relay drivers, SSR drives, and external I/O pins.
#      NOTE: Rev 4.61 BOM uses TCA6416APWR (16-bit version, same family).
#      Address: ADDR=GND → 0x20.
# ==========================================
u3_t = Part('Device', 'R', dest=TEMPLATE)
u3_t.name, u3_t.ref_prefix = 'TCA6416APWR', 'U'
u3_t.footprint = 'Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm'
u3_t.pins = [
    Pin(num='1',  name='VCCP1'),    # Port 0 supply
    Pin(num='2',  name='P00'),      # EXT_IO_A
    Pin(num='3',  name='P01'),      # EXT_IO_B
    Pin(num='4',  name='P02'),      # EXT_IO_C
    Pin(num='5',  name='P03'),      # EXT_IO_D
    Pin(num='6',  name='P04'),      # RELAY1
    Pin(num='7',  name='P05'),      # RELAY2
    Pin(num='8',  name='P06'),      # RELAY3_SSR
    Pin(num='9',  name='P07'),      # RELAY4_SSR
    Pin(num='10', name='GND'),
    Pin(num='11', name='~INT~'),    # interrupt output
    Pin(num='12', name='SCL'),
    Pin(num='13', name='SDA'),
    Pin(num='14', name='ADDR'),     # address select
    Pin(num='15', name='~RESET~'),  # active-low reset
    Pin(num='16', name='VCCP2'),    # Port 1 supply
    Pin(num='17', name='P10'),
    Pin(num='18', name='P11'),
    Pin(num='19', name='P12'),
    Pin(num='20', name='P13'),
    Pin(num='21', name='P14'),
    Pin(num='22', name='P15'),
    Pin(num='23', name='P16'),
    Pin(num='24', name='P17'),
]
u3 = u3_t()
u3.ref   = 'U3'
u3.value = 'TCA6416APWR'
u3['VCCP1']   += fused5v    # Port 0 at 5V
u3['VCCP2']   += fused5v    # Port 1 at 5V
u3['ADDR']    += gnd        # I2C address 0x20
u3['~RESET~'] += reset_net
u3['P00']     += ext_io_a
u3['P01']     += ext_io_b
u3['P02']     += ext_io_c
u3['P03']     += ext_io_d
u3['P04']     += relay1
u3['P05']     += relay2
u3['P06']     += relay3_ssr
u3['P07']     += relay4_ssr
u3['GND']     += gnd
u3['~INT~']   += io39_in
u3['SCL']     += i2c_scl_5v   # 5V-side I2C via TXS0102DCU U1
u3['SDA']     += i2c_sda_5v
# Port 1 pins — connected to additional I/O (tie to GND if unused)
for pin in ['P10','P11','P12','P13','P14','P15','P16','P17']:
    u3[pin] += gnd

# Decoupling for U3 is C6 (100nF, already wired to +3V3 above)
make_res('R5', '2K2', io26, v3v3)   # i2c SDA pull-up (3.3V side)
make_res('R16', '2K2', io27, v3v3)  # i2c SCL pullup


# ==========================================
# 12.  CURRENT/POWER MONITOR: INA229  (U8, VSSOP-10)
#      Rev 4.61: replaces TCA9534A I/O expander with INA229 shunt monitor.
#      Monitors current via J9 (Shunt) and reports over I2C.
# ==========================================
u8_t = Part('Device', 'R', dest=TEMPLATE)
u8_t.name, u8_t.ref_prefix = 'INA229', 'U'
u8_t.footprint = 'Package_SO:VSSOP-10_3x3mm_P0.5mm'
u8_t.pins = [
    Pin(num='1',  name='ALERT'),
    Pin(num='2',  name='VS'),    # supply voltage input (for bus voltage meas.)
    Pin(num='3',  name='GND'),
    Pin(num='4',  name='IN+'),   # shunt positive
    Pin(num='5',  name='IN-'),   # shunt negative
    Pin(num='6',  name='SDA'),
    Pin(num='7',  name='SCL'),
    Pin(num='8',  name='A0'),    # I2C address bit 0
    Pin(num='9',  name='A1'),    # I2C address bit 1
    Pin(num='10', name='VDD'),
]
# Shunt node nets (connected to J9 Shunt connector)
net_shunt_p = Net('Net-(U8-INP)')   # shunt +
net_shunt_n = Net('Net-(U8-INN)')   # shunt -
u8 = u8_t()
u8.ref   = 'U8'
u8.value = 'INA229'
u8['VDD']   += v3v3
u8['GND']   += gnd
u8['VS']    += fused5v     # bus voltage measurement
u8['IN+']   += net_shunt_p
u8['IN-']   += net_shunt_n
u8['SDA']   += io26
u8['SCL']   += io27
u8['ALERT'] += io34_in     # alert/interrupt → ESP32 IO34
u8['A0']    += gnd         # I2C address 0x40
u8['A1']    += gnd

# ESTOP pull-up resistor and header
make_res('R24', '10K', net_j10_1, v3v3)


# ==========================================
# 13.  RELAY K1 DRIVER CIRCUIT
#      FUSED5V → R12 → D3 (indicator LED) → K1[A2] ← Q1[D]
#      K1[A1] → FUSED5V;  K1[A2] ← Q1 drain;  D2 = flyback diode
# ==========================================

# Q1: AO3400A N-MOSFET relay driver
q1_t = Part('Device', 'R', dest=TEMPLATE)
q1_t.name, q1_t.ref_prefix = 'AO3400A', 'Q'
q1_t.footprint = 'Package_TO_SOT_SMD:SOT-23'
q1_t.pins = [Pin(num='1', name='G'), Pin(num='2', name='S'), Pin(num='3', name='D')]
q1 = q1_t()
q1.ref   = 'Q1'
q1.value = 'AO3400A'
q1['G'] += net_q1_g
q1['S'] += gnd
q1['D'] += net_d2_2

# Gate drive: R10 (series) and R11 (pull-down)
# NOTE: R10 = 220R in .net vs 560R in Rev 4.61 BOM
make_res('R10', '560R', relay1,   net_q1_g)  # series gate resistor
make_res('R11', '51K',  gnd,      net_q1_g)  # gate pull-down

# D2: LL4148 flyback diode across K1 coil
make_diode('D2', 'LL4148', net_d2_2, fused5v)  # anode=coil-, cathode=FUSED5V

# D3: Yellow LED indicator for K1 energised
# Circuit: FUSED5V → R12 → D3 anode → D3 cathode → K1[A2] (net_d2_2)
make_led('D3', 'YELLOW LED', net_d3_2, net_d2_2)  # A=net_d3_2, K=net_d2_2
make_res('R12', '560R', fused5v, net_d3_2)  # LED current limiter

# K1: Songle SRD-05VDC-SL-C relay
k1_t = Part('Device', 'R', dest=TEMPLATE)
k1_t.name, k1_t.ref_prefix = 'SRD-05VDC-SL-C', 'K'
k1_t.footprint = 'ControllerCircuit:RELAY_SRD-05VDC-SL-C'
k1_t.pins = [
    Pin(num='A1',  name='A1'),
    Pin(num='A2',  name='A2'),
    Pin(num='COM', name='COM'),
    Pin(num='NC',  name='NC'),
    Pin(num='NO',  name='NO'),
]
k1 = k1_t()
k1.ref   = 'K1'
k1.value = 'SRD-05VDC-SL-C'
k1['A1']  += fused5v
k1['A2']  += net_d2_2
k1['COM'] += net_j2_1
k1['NC']  += net_j2_2
k1['NO']  += net_j2_3

# J2: 3-pin screw terminal for K1 switch contacts
j2_t = Part('Device', 'R', dest=TEMPLATE)
j2_t.name, j2_t.ref_prefix = 'ScrewTerminal3Pin', 'J'
j2_t.footprint = 'ControllerCircuit:Terminal-Block_5.0mm_3P-LCSC_C395850'
j2_t.pins = [Pin(num=str(i), name=f'Pin_{i}') for i in range(1, 4)]
j2 = j2_t()
j2.ref   = 'J2'
j2.value = 'ScrewTerminal3Pin'
j2['Pin_1'] += net_j2_1  # COM
j2['Pin_2'] += net_j2_2  # NC
j2['Pin_3'] += net_j2_3  # NO


# ==========================================
# 14.  RELAY K2 DRIVER CIRCUIT  (mirrors K1)
# ==========================================

# Q2: AO3400A N-MOSFET relay driver
q2 = q1_t()    # reuse template
q2.ref   = 'Q2'
q2.value = 'AO3400A'
q2['G'] += net_q2_g
q2['S'] += gnd
q2['D'] += net_d4_1

make_res('R14', '560R', relay2,  net_q2_g)
make_res('R15', '51K',  gnd,     net_q2_g)

# D5: LL4148 flyback diode across K2 coil
make_diode('D5', 'LL4148', net_d4_1, fused5v)

# D4: Yellow LED indicator for K2 energised
make_led('D4', 'YELLOW LED', net_d4_2, net_d4_1)
make_res('R13', '560R', fused5v, net_d4_2)

# K2: relay
k2 = k1_t()
k2.ref   = 'K2'
k2.value = 'SRD-05VDC-SL-C'
k2['A1']  += fused5v
k2['A2']  += net_d4_1
k2['COM'] += net_j3_1
k2['NC']  += net_j3_2
k2['NO']  += net_j3_3

j3 = j2_t()
j3.ref   = 'J3'
j3.value = 'ScrewTerminal3Pin'
j3['Pin_1'] += net_j3_1
j3['Pin_2'] += net_j3_2
j3['Pin_3'] += net_j3_3


# ==========================================
# 15.  SOLID STATE RELAYS  U9, U12  (AQY212GSZ, SO-4)
#      NOTE: Rev 4.61 BOM uses AQY282SX — different rating, same pinout.
#      Input (LED side): pin 1 = anode (+), pin 2 = cathode (GND)
#      Output (MOSFET side): pins 3,4
# ==========================================
ssr_t = Part('Device', 'R', dest=TEMPLATE)
ssr_t.name, ssr_t.ref_prefix = 'AQY282SX', 'U'
ssr_t.footprint = 'Package_SO:SO-4_4.4x3.6mm_P2.54mm'
ssr_t.pins = [
    Pin(num='1', name='LED_A'),
    Pin(num='2', name='LED_K'),
    Pin(num='3', name='SW1'),
    Pin(num='4', name='SW2'),
]

# U9: RELAY3_SSR — driven by U3 P6 via R18
u9 = ssr_t()
u9.ref   = 'U9'
u9.value = 'AQY282SX'
u9['LED_A'] += net_r18_1   # anode via R18 from /RELAY3_SSR
u9['LED_K'] += gnd
u9['SW1']   += net_j12_1
u9['SW2']   += net_j12_2

make_res('R18', '220R', relay3_ssr, net_r18_1)  # NOTE: 220R net vs — not in BOM table

# U12: RELAY4_SSR — driven by U3 P7 via R25
u12 = ssr_t()
u12.ref   = 'U12'
u12.value = 'AQY282SX'
u12['LED_A'] += net_r25_1
u12['LED_K'] += gnd
u12['SW1']   += net_j12_3
u12['SW2']   += net_j12_4

make_res('R25', '220R', relay4_ssr, net_r25_1)

# --- Q4: AO3400A N-MOSFET (additional load/driver switch)
# Rev 4.61 addition — drives an auxiliary output (e.g. fan, buzzer, or 4th relay)
net_q4_g   = Net('Net-(Q4-Pad1)')
net_q4_d   = Net('Net-(Q4-Pad3)')
ext_drive4 = Net('/EXT_DRIVE4')    # driven by spare I/O or U3 Port 1 pin

q4_t = Part('Device', 'R', dest=TEMPLATE)
q4_t.name, q4_t.ref_prefix = 'AO3400A', 'Q'
q4_t.footprint = 'Package_TO_SOT_SMD:SOT-23'
q4_t.pins = [Pin(num='1', name='G'), Pin(num='2', name='S'), Pin(num='3', name='D')]
q4 = q4_t()
q4.ref   = 'Q4'
q4.value = 'AO3400A'
q4['G'] += net_q4_g
q4['S'] += gnd
q4['D'] += net_q4_d

make_res('R19', '10K', v3v3, io39_in)   # IO39 pull-up (interrupt line)
make_res('R20', '1M',  gnd,  net_q4_g)  # Q4 gate pull-down (1M bleed)
make_res('R29', '10K', fused5v, net_q4_d)  # Q4 drain pull-up / load
make_res('R31', '10K', v3v3, io33)      # IO33 pull-up
make_res('R32', '10K', v3v3, io32)      # IO32 pull-up

# --- Additional resistors from Rev 4.61 BOM ---
make_res('R22', '10K',  gnd, io34_in)   # IO34 pull-down (was 180R DNP in Rev 1.1)
make_res('R23', '10R',  io26, io26)     # I2C series protection (placeholder — verify net)
make_res('R30', '10R',  io27, io27)     # I2C series protection (placeholder — verify net)

# J12: 4-pin terminal for both SSR load outputs
j12_t = Part('Device', 'R', dest=TEMPLATE)
j12_t.name, j12_t.ref_prefix = 'ScrewTerminal', 'J'
j12_t.footprint = 'ControllerCircuit:Terminal-Block_3.81_4P_LCSC_C395880'
j12_t.pins = [Pin(num=str(i), name=f'Pin_{i}') for i in range(1, 5)]
j12 = j12_t()
j12.ref   = 'J12'
j12.value = 'ScrewTerminal'
j12['Pin_1'] += net_j12_1
j12['Pin_2'] += net_j12_2
j12['Pin_3'] += net_j12_3
j12['Pin_4'] += net_j12_4


# ==========================================
# 16.  EXTERNAL I/O CONNECTOR  J4  (TCA6408 P0–P3)
# ==========================================
j4_t = Part('Device', 'R', dest=TEMPLATE)
j4_t.name, j4_t.ref_prefix = 'ScrewTerminal', 'J'
j4_t.footprint = 'ControllerCircuit:Terminal-Block_3.81_4P_LCSC_C395880'
j4_t.pins = [Pin(num=str(i), name=f'Pin_{i}') for i in range(1, 5)]
j4 = j4_t()
j4.ref   = 'J4'
j4.value = 'ScrewTerminal'
j4['Pin_1'] += ext_io_a
j4['Pin_2'] += ext_io_b
j4['Pin_3'] += ext_io_c
j4['Pin_4'] += ext_io_d


# ==========================================
# 17.  RGB STATUS LED  D1  (6-pin 5050 package)
#      Common anode pins (4,5,6) tied to GND; cathodes driven by U8.
#      NOTE: schematic note — "Green/Red intentionally swapped to match
#      component + ground! (footprint wrong)"
# ==========================================
d1_t = Part('Device', 'R', dest=TEMPLATE)
d1_t.name, d1_t.ref_prefix = 'RGB', 'D'
d1_t.footprint = 'LED_SMD:LED_RGB_5050-6'
d1_t.pins = [
    Pin(num='1', name='RK'),   # Red cathode
    Pin(num='2', name='GK'),   # Green cathode
    Pin(num='3', name='BK'),   # Blue cathode
    Pin(num='4', name='BA'),   # Blue anode  → GND (common)
    Pin(num='5', name='GA'),   # Green anode → GND
    Pin(num='6', name='RA'),   # Red anode   → GND
]
d1 = d1_t()
d1.ref   = 'D1'
d1.value = 'RGB'
d1['RK'] += net_d1_rk    # → R17 → /GREEN_LED (swapped)
d1['GK'] += net_d1_gk    # → R4  → /RED_LED   (swapped)
d1['BK'] += net_d1_bk    # → R1  → /BLUE_LED
d1['BA'] += gnd
d1['GA'] += gnd
d1['RA'] += gnd

# LED current-limit resistors
make_res('R1',  '220R', net_d1_bk, blue_led)   # Blue  cathode → U8 P0
make_res('R4',  '560R', net_d1_gk, red_led)    # Green→Red (swapped) → U8 P1
make_res('R17', '220R', net_d1_rk, green_led)  # Red→Green (swapped) → U8 P2


# ==========================================
# 18.  DISPLAY BACKLIGHT LED CIRCUIT
#      +3V3 → R21 → LCD LED pin → U8 P3 (PWM control)
#      NOTE: R21 = 180R in .net vs 220R in Rev 4.61 BOM
# ==========================================
make_res('R21', '220R', v3v3, net_lcd_led)


# ==========================================
# 19.  LCD MODULE  (ILI9341 2.8" SPI TFT with touch)
#      Two SPI buses: HSPI for display, VSPI for touch + SD card
# ==========================================
lcd_t = Part('Device', 'R', dest=TEMPLATE)
lcd_t.name, lcd_t.ref_prefix = 'LCD', 'LCD'
lcd_t.footprint = 'ControllerCircuit:TFTSPI_2_8_240x320_TOUCH'
lcd_t.pins = [
    Pin(num='1',   name='T_IRQ'),    # touch interrupt
    Pin(num='2',   name='T_DO'),     # touch MISO
    Pin(num='3',   name='T_DIN'),    # touch MOSI
    Pin(num='4',   name='T_CS'),     # touch chip select
    Pin(num='5',   name='T_CLK'),    # touch SPI clock
    Pin(num='6',   name='MISO'),     # display MISO (HSPI)
    Pin(num='7',   name='LED'),      # backlight anode
    Pin(num='8',   name='SCK'),      # display clock (HSPI)
    Pin(num='9',   name='MOSI'),     # display MOSI (HSPI)
    Pin(num='10',  name='D/C'),      # data/command
    Pin(num='11',  name='RESET'),    # hardware reset
    Pin(num='12',  name='CS'),       # display CS — tied to GND (only device)
    Pin(num='13',  name='GND'),
    Pin(num='14',  name='VCC'),
    Pin(num='SD1', name='SD_SCK'),   # SD card clock (VSPI)
    Pin(num='SD2', name='SD_MISO'),  # SD card MISO (VSPI)
    Pin(num='SD3', name='SD_MOSI'),  # SD card MOSI (VSPI)
    Pin(num='SD4', name='SD_CS'),    # SD card CS
]
lcd1 = lcd_t()
lcd1.ref   = 'LCD1'
lcd1.value = 'LCD'
lcd1['T_IRQ']  += io36_in     # touch interrupt → IO36 (SENSOR_VP)
lcd1['T_DO']   += vspi_miso   # touch MISO → VSPI MISO
lcd1['T_DIN']  += vspi_mosi   # touch MOSI ← VSPI MOSI
lcd1['T_CS']   += io4          # touch CS ← IO4
lcd1['T_CLK']  += vspi_clk    # touch CLK ← VSPI CLK
lcd1['MISO']   += hspi_miso   # display MISO (HSPI)
lcd1['LED']    += net_lcd_led  # backlight → R21 → +3V3 (PWM via U8 P3)
lcd1['SCK']    += hspi_clk    # display CLK (HSPI)
lcd1['MOSI']   += hspi_mosi   # display MOSI (HSPI)
lcd1['D/C']    += display_dc  # data/command → IO15
lcd1['RESET']  += reset_net   # hardware reset
lcd1['CS']     += gnd          # permanently selected (only SPI device on HSPI)
lcd1['GND']    += gnd
lcd1['VCC']    += v3v3
lcd1['SD_SCK']  += vspi_clk   # SD clock shares VSPI bus
lcd1['SD_MISO'] += vspi_miso
lcd1['SD_MOSI'] += vspi_mosi
lcd1['SD_CS']   += io5         # SD CS ← IO5


# ==========================================
# 20.  microSD CONNECTOR: Molex 0472192001  (J15)
#      Single-wire SPI mode: CMD=MOSI, CLK, DAT0=MISO, DAT3=CS
#      DAT1, DAT2 are unused (NC) in SPI mode.
# ==========================================
j15_t = Part('Device', 'R', dest=TEMPLATE)
j15_t.name, j15_t.ref_prefix = 'Molex 0472192001', 'J'
j15_t.footprint = '0472192001'
j15_t.pins = [
    Pin(num='1',  name='DAT2'),     Pin(num='2',  name='CD/DAT3'),
    Pin(num='3',  name='CMD'),      Pin(num='4',  name='VDD'),
    Pin(num='5',  name='CLK'),      Pin(num='6',  name='VSS'),
    Pin(num='7',  name='DAT0'),     Pin(num='8',  name='DAT1'),
    Pin(num='G1', name='GND_1'),    Pin(num='G2', name='GND_2'),
    Pin(num='G3', name='GND_3'),    Pin(num='G4', name='GND_4'),
]
j15 = j15_t()
j15.ref   = 'J15'
j15.value = 'Molex 0472192001'
j15['DAT2']  += net_j15_1  # NC in SPI mode
j15['CD/DAT3'] += io5      # SD_CS ← IO5
j15['CMD']   += vspi_mosi  # SD_MOSI
j15['VDD']   += v3v3
j15['CLK']   += vspi_clk
j15['VSS']   += gnd
j15['DAT0']  += vspi_miso  # SD_MISO
j15['DAT1']  += net_j15_8  # NC in SPI mode
j15['GND_1'] += gnd
j15['GND_2'] += gnd
j15['GND_3'] += gnd
j15['GND_4'] += gnd


# ==========================================
# 21.  AVRISP / VSPI HEADER  J8  (2×3 2.54mm)
#      Doubles as AVRISP-6 and VSPI debug/programming header.
# ==========================================
j8_t = Part('Device', 'R', dest=TEMPLATE)
j8_t.name, j8_t.ref_prefix = '2x3 2.54mm IDC Connectors', 'J'
j8_t.footprint = 'Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical'
j8_t.pins = [
    Pin(num='1', name='MISO'), Pin(num='2', name='VCC'),
    Pin(num='3', name='SCK'),  Pin(num='4', name='MOSI'),
    Pin(num='5', name='~RST'), Pin(num='6', name='GND'),
]
j8 = j8_t()
j8.ref   = 'J8'
j8.value = '2x3 2.54mm IDC Connectors'
j8['MISO'] += vspi_miso
j8['VCC']  += v3v3
j8['SCK']  += vspi_clk
j8['MOSI'] += vspi_mosi
j8['~RST'] += avrisp_reset   # IO0 (ESP32 boot mode / AVRISP reset)
j8['GND']  += gnd


# ==========================================
# 22.  PUSH BUTTONS  SW1, SW2  (with RC debounce)
#
#      Circuit: +3V3 → R7(51K) → SW_node → SW → GND
#               SW_node → R26(22K) → SW1OUTPUT → U8 P4
#               SW1OUTPUT → C7(1uF) → GND  (filter cap, already wired)
# ==========================================
sw_t = Part('Device', 'R', dest=TEMPLATE)
sw_t.name, sw_t.ref_prefix = 'SW_Push', 'SW'
sw_t.footprint = 'Button_Switch_THT:SW_PUSH_6mm_H5mm'
sw_t.pins = [Pin(num='1', name='P1'), Pin(num='2', name='P2')]

sw1 = sw_t()
sw1.ref   = 'SW1'
sw1.value = 'SW_Push'
sw1['P1'] += net_sw1_node   # switch contact: high side (pulled up via R7)
sw1['P2'] += gnd             # switch contact: low side

make_res('R7',  '51K', v3v3, net_sw1_node)  # pull-up
make_res('R26', '22K', net_sw1_node, sw1out)  # debounce / signal conditioner
# C7 (debounce filter cap) already wired in section 5 above

sw2 = sw_t()
sw2.ref   = 'SW2'
sw2.value = 'SW_Push'
sw2['P1'] += net_sw2_node
sw2['P2'] += gnd

make_res('R27', '51K', v3v3, net_sw2_node)
make_res('R28', '22K', net_sw2_node, sw2out)
# C11 (debounce filter cap) already wired in section 5 above


# ==========================================
# 23.  ESTOP HEADER  J10
# ==========================================
j10_t = Part('Device', 'R', dest=TEMPLATE)
j10_t.name, j10_t.ref_prefix = 'Conn_01x02_Female', 'J'
j10_t.footprint = 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Horizontal'
j10_t.pins = [Pin(num='1', name='Pin_1'), Pin(num='2', name='Pin_2')]
j10 = j10_t()
j10.ref   = 'J10'
j10.value = 'Conn_01x02_Female'
j10['Pin_1'] += net_j10_1  # ESTOP signal (active low, pulled high by R24)
j10['Pin_2'] += gnd


# ==========================================
# 24.  MISC CONNECTORS
# ==========================================

# J9: 4-pin shunt connector — wires current shunt into INA229 (U8)
# Pin 1,2 = line in/out (shunt +/-); Pin 3,4 = GND/FUSED5V sense lines
j9_t = Part('Device', 'R', dest=TEMPLATE)
j9_t.name, j9_t.ref_prefix = 'Shunt', 'J'
j9_t.footprint = 'ControllerCircuit:Terminal-Block_3.81_4P_LCSC_C395880'
j9_t.pins = [Pin(num=str(i), name=f'Pin_{i}') for i in range(1, 5)]
j9 = j9_t()
j9.ref   = 'J9'
j9.value = 'Shunt'
j9['Pin_1'] += net_shunt_p   # shunt + → U8 IN+
j9['Pin_2'] += net_shunt_n   # shunt - → U8 IN-
j9['Pin_3'] += fused5v
j9['Pin_4'] += gnd

# J11: 3-pin I2C debug header (SDA, SCL, GND)
j11_t = Part('Device', 'R', dest=TEMPLATE)
j11_t.name, j11_t.ref_prefix = 'Conn_01x03_Female', 'J'
j11_t.footprint = 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical'
j11_t.pins = [Pin(num=str(i), name=f'Pin_{i}') for i in range(1, 4)]
j11 = j11_t()
j11.ref   = 'J11'
j11.value = 'Conn_01x03_Female'
j11['Pin_1'] += io26  # i2c SDA
j11['Pin_2'] += io27  # i2c SCL
j11['Pin_3'] += gnd

# J12 already wired in SSR section (section 15)

# J14: Unused debug header (4-pin: +3V3, IO35, IO33, GND)
j14_t = Part('Device', 'R', dest=TEMPLATE)
j14_t.name, j14_t.ref_prefix = 'ScrewTerminal', 'J'
j14_t.footprint = 'Connector_PinHeader_1.27mm:PinHeader_1x04_P1.27mm_Vertical'
j14_t.pins = [Pin(num=str(i), name=f'Pin_{i}') for i in range(1, 5)]
j14 = j14_t()
j14.ref   = 'J14'
j14.value = 'ScrewTerminal'
j14['Pin_1'] += v3v3
j14['Pin_2'] += io35_in
j14['Pin_3'] += io33
j14['Pin_4'] += gnd

# J16: 4-pin socket (spare/debug — not connected per .net analysis)
j16_t = Part('Device', 'R', dest=TEMPLATE)
j16_t.name, j16_t.ref_prefix = '4PinSocket', 'J'
j16_t.footprint = 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical'
j16_t.pins = [Pin(num=str(i), name=f'Pin_{i}') for i in range(1, 5)]
j16 = j16_t()
j16.ref   = 'J16'
j16.value = '4PinSocket'
j16['Pin_1'] += v3v3  # labeled "+3.3V" on schematic


# ==========================================
# 25.  DNP COMPONENTS (Do Not Place / Do Not Purchase)
#      Wired as per .net file connectivity. Mark as DNP in BOM.
# ==========================================

# D6: MHPC3528CRGBCT RGB LED (DNP — Do Not Place)
d6_t = Part('Device', 'R', dest=TEMPLATE)
d6_t.name, d6_t.ref_prefix = 'LED_RGBC', 'D'
d6_t.footprint = 'ControllerCircuit:LED_MHPC3528CRGBCT'
d6_t.pins = [Pin(num=str(i), name=f'P{i}') for i in range(1, 7)]
d6 = d6_t()
d6.ref   = 'D6'
d6.value = 'MHPC3528CRGBCT'
d6['P1'] += net_d6_2
d6['P2'] += gnd
d6['P3'] += gnd
d6['P4'] += gnd
d6['P5'] += gnd
d6['P6'] += gnd

# R22 is now instantiated in section 15 as active 10K

# U10: ATtiny841-SSU microcontroller (DNP)
u10_t = Part('Device', 'R', dest=TEMPLATE)
u10_t.name, u10_t.ref_prefix = 'ATtiny841-SSU', 'U'
u10_t.footprint = 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm'
u10_t.pins = [
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
u10 = u10_t()   # DNP
u10.ref   = 'U10'
u10.value = 'ATtiny841-SSU'
u10['VCC']          += v3v3
u10['GND']          += gnd
u10['~RESET~/PB3']  += reset_net
u10['PA7']          += io32        # net /IO32
u10['PA6']          += net_r22_2   # → R22 → D6 (DNP indicator)
u10['PA5']          += net_j6_1    # → J6 pin 1 (MISO)
u10['PA4']          += net_j9_6    # → J9 pin 6
u10['PA3']          += net_j9_1    # AREF/PA0? net remapped — per .net pin 10=PA3
u10['PA2']          += io26        # i2c SDA
u10['PA1']          += net_j9_2
u10['AREF/PA0']     += net_j9_1
u10['XTAL1/PB0']    += net_j9_4
u10['XTAL2/PB1']    += net_j9_5
u10['PB2']          += net_j9_6

# R23: 10K pull-up for ATtiny ~RESET~ (DNP)
r23_t = Part('Device', 'R', value='10K', footprint=FP_R0805)
r23_t.ref   = 'R23'
r23_t.value = '10K'
r23_t[1] += v3v3
r23_t[2] += net_j6_5   # ATtiny ~RESET~ line via J6

# J6: ATtiny AVR-ISP-6 programming header (DNP)
j6_t = Part('Device', 'R', dest=TEMPLATE)
j6_t.name, j6_t.ref_prefix = 'AVR-ISP-6', 'J'
j6_t.footprint = 'Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical'
j6_t.pins = [
    Pin(num='1', name='MISO'), Pin(num='2', name='VCC'),
    Pin(num='3', name='SCK'),  Pin(num='4', name='MOSI'),
    Pin(num='5', name='~RST'), Pin(num='6', name='GND'),
]
j6 = j6_t()   # DNP
j6.ref   = 'J6'
j6.value = 'AVR-ISP-6'
j6['MISO'] += net_j6_1
j6['VCC']  += v3v3
j6['SCK']  += io26    # reusing i2c/IO26 for ATtiny SCK
j6['MOSI'] += io27    # reusing i2c/IO27 for ATtiny MOSI
j6['~RST'] += net_j6_5
j6['GND']  += gnd

# JP2, JP3: DNP solder jumpers (shorting IO26 / IO27 for test)
jp2_t = Part('Device', 'R', dest=TEMPLATE)
jp2_t.name, jp2_t.ref_prefix = 'Conn_01x02_Female', 'JP'
jp2_t.footprint = 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'
jp2_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='B')]
jp2 = jp2_t()   # DNP
jp2.ref   = 'JP2'
jp2.value = 'Conn_01x02_Female'
jp2['A'] += io26
jp2['B'] += io26  # bridged (pin 1 + 2 shorted per .net)

jp3 = jp2_t()   # DNP
jp3.ref   = 'JP3'
jp3.value = 'Conn_01x02_Female'
jp3['A'] += io27
jp3['B'] += io27

# C8, C9 already instantiated in section 5 (marked DNP in comments)


# ==========================================
# 26.  OUTPUT: KiCad netlist  +  CSV BOM
# ==========================================
def generate_csv_bom(filename='ControllerCircuit_BOM.csv'):
    """
    Iterate every instantiated part, group by (name, value, footprint),
    sort references, and write a CSV BOM.  DNP parts are included with
    a 'DNP' note in the Value field for identification.
    """
    DNP_REFS = {
        'D6', 'D7', 'U10', 'J6', 'JP2', 'JP3',
    }

    bom_groups = defaultdict(list)

    for part in default_circuit.parts:  # type: ignore
        is_template = getattr(part, 'dest', None) == TEMPLATE  # type: ignore
        has_no_ref  = not getattr(part, 'ref',  None)
        if is_template or has_no_ref:
            continue

        ref   = part.ref
        value = getattr(part, 'value',     '')
        name  = getattr(part, 'name',      '')
        fp    = getattr(part, 'footprint', '')

        # Tag DNP items so they can be identified in the BOM
        display_value = f'{value} [DNP]' if ref in DNP_REFS else value

        key = (name, display_value, fp)
        bom_groups[key].append(ref)

    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Quantity', 'Reference(s)', 'Value',
                         'Part Name', 'Footprint'])
        for (name, value, fp), refs in sorted(bom_groups.items()):
            refs.sort()
            writer.writerow([len(refs), ', '.join(refs), value, name, fp])

    print(f'✅  BOM   saved  →  {filename}')


generate_netlist(filename='ControllerCircuit_skidl.net')
print('✅  Netlist saved  →  ControllerCircuit_skidl.net')
generate_csv_bom(filename='ControllerCircuit_BOM.csv')
