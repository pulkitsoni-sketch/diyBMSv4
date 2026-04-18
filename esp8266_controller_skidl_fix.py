"""
esp8266_controller_skidl.py  —  ESP8266 Controller Circuit
============================================================
SKiDL script to regenerate the KiCad netlist and grouped BOM for the
ESP8266 Controller Circuit.

Hardware overview:
  Interface   : I2C (ESP8266 host → PCF8574T I/O expander)
  I/O expander: 8-bit quasi-bidirectional GPIO (P0–P7)
  Isolation   : EL3H7(B)(TA)-G phototransistor optocoupler
  Indicator   : COMMS status LED (D1)

Key ICs:
  U2  EL3H7(B)(TA)-G    Phototransistor optocoupler (SOP-4)
  U3  PCF8574T/3,518    I2C 8-bit I/O expander (SOIC-16W)

Schematic source : ESP8266_Circuit.pdf
BOM source       : ESP8266ControllerCircuit_bom_jlc.csv

IMPORTANT — explicit reference designators
-----------------------------------------
Every instantiated part has its .ref set explicitly so that the generated
BOM reference strings match the original schematic exactly.

Usage:
    python esp8266_controller_skidl.py
Outputs:
    esp8266_controller.net      — KiCad-compatible netlist
    esp8266_controller_BOM.csv  — grouped Bill of Materials
"""

import os
import csv
from collections import defaultdict


# =============================================================================
# 1.  SETUP & PATHS  (edit to match your KiCad installation)
# =============================================================================
app_symbols    = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
app_footprints = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
user_config    = '/Users/user/Documents/KiCad/9.0'  # adjust as needed

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
vcc  = Net('VCC')        # 3.3 V supply rail from ESP8266 regulator


# =============================================================================
# 3.  SIGNAL NETS
# =============================================================================
i2c_scl   = Net('I2C_SCL')     # I2C clock  (J1 → U3 SCL, pulled up via R4)
i2c_sda   = Net('I2C_SDA')     # I2C data   (J1 → U3 SDA, pulled up via R5)
int_n     = Net('/INT')         # PCF8574T interrupt output (active-low)

# PCF8574T quasi-bidirectional I/O lines
p0 = Net('P0')
p1 = Net('P1')
p2 = Net('P2')
p3 = Net('P3')
p4 = Net('P4')
p5 = Net('P5')
p6 = Net('P6')
p7 = Net('P7')

# Optocoupler nets
opto_in  = Net('OPTO_IN')    # Anode side of U2 LED (after R3 series resistor)
opto_out = Net('OPTO_OUT')   # Collector of U2 phototransistor (pulled up via R2)

# COMMS LED drive net (VCC → R1 → LED_COMMS → D1_A → D1_K → P7, active-low)
led_comms = Net('LED_COMMS')


# =============================================================================
# 4.  FOOTPRINT CONSTANTS & COMPONENT FACTORIES
# =============================================================================
FP_R0805     = 'Resistor_SMD:R_0805_2012Metric'
FP_R0805_HS  = 'R_0805_HandSoldering'
FP_LED0805   = 'LED_0805'
FP_SOP4      = 'SOP-4_4.4x2.8mm_Pitch1.27mm'
FP_SOIC16W   = 'SOIC-16W_7.5x10.3mm_Pitch1.27mm'
FP_HDR_1x04  = 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical'


def make_res(ref, value, net_1, net_2, footprint=FP_R0805_HS):
    """Instantiate a resistor and assign an explicit reference designator."""
    r = Part('Device', 'R', value=value, footprint=footprint)
    r.ref = ref
    r[1] += net_1
    r[2] += net_2
    return r


# =============================================================================
# 5.  J1 — 4-PIN I2C HEADER (ESP8266 → Controller Board)
#     Pin 1: VCC (+3.3V)
#     Pin 2: GND
#     Pin 3: I2C_SCL
#     Pin 4: I2C_SDA
# =============================================================================
j1_t = Part('Device', 'R', dest=TEMPLATE)
j1_t.name, j1_t.ref_prefix = 'Conn_01x04', 'J'
j1_t.footprint = FP_HDR_1x04
j1_t.pins = [
    Pin(num='1', name='VCC'),
    Pin(num='2', name='GND'),
    Pin(num='3', name='SCL'),
    Pin(num='4', name='SDA'),
]

j1 = j1_t()
j1.ref   = 'J1'
j1.value = 'Conn_01x04'
j1['VCC'] += vcc
j1['GND'] += gnd
j1['SCL'] += i2c_scl
j1['SDA'] += i2c_sda


# =============================================================================
# 6.  I2C PULL-UP RESISTORS
#     R4 (4K7): SCL pull-up to VCC
#     R5 (4K7): SDA pull-up to VCC
# =============================================================================
make_res('R4', '4K7', vcc, i2c_scl)
make_res('R5', '4K7', vcc, i2c_sda)


# =============================================================================
# 7.  U3 — PCF8574T/3,518  I2C 8-bit I/O Expander (SOIC-16W)
#     Address: A2=A1=A0=GND → I2C address 0x20
#     Open-drain /INT goes low when any input changes
# =============================================================================
u3_t = Part('Device', 'R', dest=TEMPLATE)
u3_t.name, u3_t.ref_prefix = 'PCF8574T', 'U'
u3_t.footprint = FP_SOIC16W
u3_t.pins = [
    Pin(num='1',  name='A0'),
    Pin(num='2',  name='A1'),
    Pin(num='3',  name='A2'),
    Pin(num='4',  name='P0'),
    Pin(num='5',  name='P1'),
    Pin(num='6',  name='P2'),
    Pin(num='7',  name='P3'),
    Pin(num='8',  name='VSS'),
    Pin(num='9',  name='P4'),
    Pin(num='10', name='P5'),
    Pin(num='11', name='P6'),
    Pin(num='12', name='P7'),
    Pin(num='13', name='/INT'),
    Pin(num='14', name='SCL'),
    Pin(num='15', name='SDA'),
    Pin(num='16', name='VDD'),
]

u3 = u3_t()
u3.ref   = 'U3'
u3.value = 'PCF8574T/3,518'

# Power
u3['VDD'] += vcc
u3['VSS'] += gnd

# I2C bus
u3['SCL'] += i2c_scl
u3['SDA'] += i2c_sda

# Address: 0x20 (all address pins to GND)
u3['A0'] += gnd
u3['A1'] += gnd
u3['A2'] += gnd

# Interrupt output
u3['/INT'] += int_n

# GPIO lines P0–P7
u3['P0'] += p0
u3['P1'] += p1
u3['P2'] += p2
u3['P3'] += p3
u3['P4'] += p4
u3['P5'] += p5
u3['P6'] += p6
u3['P7'] += p7    # P7 → COMMS LED cathode (active-low)


# =============================================================================
# 8.  D1 — COMMS LED  (LED_0805, LCSC C2297)
#     Active-low: VCC → R1 (470R) → LED_COMMS → D1_A → D1_K → P7
#     LED lights when PCF8574 P7 is driven low
# =============================================================================
d1_t = Part('Device', 'R', dest=TEMPLATE)
d1_t.name, d1_t.ref_prefix = 'LED', 'D'
d1_t.footprint = FP_LED0805
d1_t.pins = [
    Pin(num='1', name='K'),
    Pin(num='2', name='A'),
]

d1 = d1_t()
d1.ref   = 'D1'
d1.value = 'COMMS'
d1['A'] += led_comms   # Anode ← current-limiting resistor R1
d1['K'] += p7          # Cathode → PCF8574 P7 (current sink, active-low)

# R1 (470R): COMMS LED current limiter
# VCC → R1 → LED_COMMS (D1 anode); D1 cathode sinks through P7 of U3
make_res('R1', '470R', vcc, led_comms)


# =============================================================================
# 9.  U2 — EL3H7(B)(TA)-G  Phototransistor Optocoupler (SOP-4, LCSC C32565)
#     Input LED:   P0 → R3 (220R) → OPTO_IN → U2 A(1) → U2 K(2) → GND
#     Output NPN:  VCC → R2 (2K2) → OPTO_OUT → U2 C(4) → U2 E(3) → GND
# =============================================================================
u2_t = Part('Device', 'R', dest=TEMPLATE)
u2_t.name, u2_t.ref_prefix = 'EL3H7', 'U'
u2_t.footprint = FP_SOP4
u2_t.pins = [
    Pin(num='1', name='A'),    # LED Anode
    Pin(num='2', name='K'),    # LED Cathode
    Pin(num='3', name='E'),    # Phototransistor Emitter
    Pin(num='4', name='C'),    # Phototransistor Collector
]

u2 = u2_t()
u2.ref   = 'U2'
u2.value = 'EL3H7(B)(TA)-G'

u2['A'] += opto_in      # Anode ← series resistor R3
u2['K'] += gnd           # Cathode → GND
u2['E'] += gnd           # Emitter → GND
u2['C'] += opto_out      # Collector ← pull-up resistor R2

# R3 (220R): optocoupler input current-limiting resistor
# PCF8574 P0 drives the optocoupler LED when P0 is asserted high
make_res('R3', '220R', p0, opto_in)

# R2 (2K2): optocoupler collector pull-up to VCC
# OPTO_OUT goes low (≈GND) when optocoupler is triggered
make_res('R2', '2K2', vcc, opto_out)


# =============================================================================
# 10.  OUTPUT: KiCad netlist  +  CSV BOM
# =============================================================================

def generate_csv_bom(filename: str = 'esp8266_controller_BOM.csv') -> None:
    """
    Walk every instantiated (non-template) part, group identical entries by
    (part name, value, footprint), sort reference designators naturally, and
    write a JLC-style BOM CSV to *filename*.
    """
    bom_groups: dict = defaultdict(list)

    for part in default_circuit.parts:  # type: ignore[attr-defined]
        if getattr(part, 'dest', None) == TEMPLATE:  # type: ignore[name-defined]
            continue
        ref = getattr(part, 'ref', None)
        if not ref:
            continue
        if str(ref).startswith('J'):
            continue

        key = (
            getattr(part, 'name',      ''),
            getattr(part, 'value',     ''),
            getattr(part, 'footprint', ''),
        )
        bom_groups[key].append(ref)

    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Quantity', 'Reference(s)', 'Value', 'Part Name', 'Footprint',
        ])
        for (name, value, footprint), refs in sorted(bom_groups.items()):
            refs.sort()
            writer.writerow([
                len(refs),
                ', '.join(refs),
                value,
                name,
                footprint,
            ])

    print(f'✅  BOM   saved  →  {filename}')


generate_netlist(filename='esp8266_controller.net')
print('✅  Netlist saved  →  esp8266_controller.net')
generate_csv_bom(filename='esp8266_controller_BOM.csv')
