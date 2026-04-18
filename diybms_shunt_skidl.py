"""
diybms_shunt_skidl.py
===========================================================================
SKiDL script to regenerate the KiCad netlist and grouped BOM for the
DIYBMS CONTROLLER CURRENT SHUNT DAUGHTER CARD.
"""

import os
import csv
from collections import defaultdict

# =============================================================================
# 1. SETUP & PATHS (From MPPT Reference)
# =============================================================================
app_symbols    = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
app_footprints = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'

os.environ['KICAD_SYMBOL_DIR']  = app_symbols
os.environ['KICAD6_SYMBOL_DIR'] = app_symbols
os.environ['KICAD7_SYMBOL_DIR'] = app_symbols
os.environ['KICAD8_SYMBOL_DIR'] = app_symbols
os.environ['KICAD9_SYMBOL_DIR'] = app_symbols

os.environ['KICAD_FOOTPRINT_DIR']  = app_footprints
os.environ['KICAD8_FOOTPRINT_DIR'] = app_footprints

from skidl import * # noqa: E402

lib_search_paths[KICAD].extend([app_symbols])
footprint_search_paths[KICAD].append(app_footprints)
set_default_tool(KICAD)

# ==============================================================================
# 2. Signal Nets
# ==============================================================================
v3v3 = Net('+3.3V')
gnd  = Net('GND')

cs    = Net('CS')
miso  = Net('MISO')
mosi  = Net('MOSI')
sck   = Net('SCK')
alert = Net('ALERT')

battery_p = Net('BATTERY+')
vin_p     = Net('Vin+')
vin_n     = Net('Vin-')
charger_l = Net('CHARGER_LOAD')

in_p = Net('IN+')
in_n = Net('IN-')

# ==============================================================================
# 3. Component Templates (Bypasses library dependency completely)
# ==============================================================================

# Resistor Template
res_t = Part('Device', 'R', dest=TEMPLATE)
res_t.name, res_t.ref_prefix = 'R', 'R'
res_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]

def make_res(ref, value, p1, p2, footprint='Resistor_SMD:R_0805_2012Metric'):
    r = res_t(footprint=footprint)
    r.value, r.ref = value, ref
    r['1'] += p1
    r['2'] += p2
    return r

# Capacitor Template
cap_t = Part('Device', 'R', dest=TEMPLATE)  # Based on 'R' to avoid lookup issues
cap_t.name, cap_t.ref_prefix = 'C', 'C'
cap_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]

def make_cap(ref, value, p1, p2, footprint='Capacitor_SMD:C_0805_2012Metric'):
    c = cap_t(footprint=footprint)
    c.value, c.ref = value, ref
    c['1'] += p1
    c['2'] += p2
    return c

# INA229-Q1 Template
ina_t = Part('Device', 'R', dest=TEMPLATE)
ina_t.name, ina_t.ref_prefix = 'INA229-Q1', 'U'
ina_t.footprint = 'Package_SO:VSSOP-10_3x3mm_P0.5mm'
ina_t.pins = [Pin(num=str(i), name=f'P{i}') for i in range(1, 11)]

u1 = ina_t()
u1.ref = 'U1'
u1.value = 'INA229'

u1['1']  += v3v3       # VS
u1['2']  += gnd        # GND
u1['3']  += alert      # ALERT
u1['4']  += mosi       # SDA/MOSI
u1['5']  += sck        # SCL/SCLK
u1['6']  += miso       # SDO/MISO
u1['7']  += cs         # CS
u1['8']  += battery_p  # VBUS
u1['9']  += in_n       # IN-
u1['10'] += in_p       # IN+

# J1 Template (7-pin)
j1_t = Part('Device', 'R', dest=TEMPLATE)
j1_t.name, j1_t.ref_prefix = 'Conn_01x07_Female', 'J'
j1_t.footprint = 'Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical'
j1_t.pins = [Pin(num=str(i), name=f'P{i}') for i in range(1, 8)]

j1 = j1_t()
j1.ref, j1.value = 'J1', 'header'
j1['1'] += cs
j1['2'] += miso
j1['3'] += mosi
j1['4'] += sck
j1['5'] += alert
j1['6'] += v3v3
j1['7'] += gnd

# J2 Template (4-pin)
j2_t = Part('Device', 'R', dest=TEMPLATE)
j2_t.name, j2_t.ref_prefix = 'Conn_01x04_Female', 'J'
j2_t.footprint = 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical'
j2_t.pins = [Pin(num=str(i), name=f'P{i}') for i in range(1, 5)]

j2 = j2_t()
j2.ref, j2.value = 'J2', 'header'
j2['1'] += battery_p
j2['2'] += vin_p
j2['3'] += vin_n
j2['4'] += charger_l

# ==============================================================================
# 4. Instantiate Passives
# ==============================================================================
make_cap('C1', '100nF 100V', in_p, in_n)
make_cap('C2', '1uF',        v3v3, gnd)
make_cap('C3', '100nF 100V', v3v3, gnd)

make_res('R1', '10R', vin_p, in_p)
make_res('R2', '10R', vin_n, in_n)
make_res('R3', '10K', v3v3,  alert)

# ==============================================================================
# 5. Output Generation
# ==============================================================================
def generate_bom(filename='diybms_shunt_addon_bom.csv'):
    bom_groups = defaultdict(list)
    for part in default_circuit.parts:  # type: ignore[attr-defined]
        # Skip TEMPLATE parts
        if getattr(part, 'dest', None) == TEMPLATE:  # type: ignore[name-defined]
            continue
            
        ref = getattr(part, 'ref', None)
        if not ref: 
            continue
            
        key = (
            getattr(part, 'name', ''),
            getattr(part, 'value', ''),
            getattr(part, 'footprint', ''),
        )
        bom_groups[key].append(ref)

    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Quantity', 'Reference(s)', 'Value', 'Part Name', 'Footprint'])
        for (name, value, footprint), refs in sorted(bom_groups.items()):
            # Natural sort (C1 before C2)
            refs.sort(key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
            # Clean up SKiDL footprint prefix
            clean_fp = footprint.split(':')[-1] if ':' in footprint else footprint
            writer.writerow([len(refs), ' '.join(refs), value, name, clean_fp])
            
    print(f'✅ BOM saved successfully to {filename}')

if __name__ == '__main__':
    generate_netlist(file_='diybms_shunt_addon.net')
    generate_bom()