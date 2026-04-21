"""
programming_adapter_skidl.py  —  DIYBMS ISP Programmer Adapter
===============================================================
SKiDL script for the 3-component ISP programming adapter.

The adapter is a direct passthrough between two AVR-ISP-6 connectors
(J1 ↔ J2, all 6 pins tied together) plus a 3-pin female header (J3)
that exposes VCC, MISO and GND for an alternative connection point.

Components: J1 (AVR-ISP-6), J2 (AVR-ISP-6), J3 (Conn_01x03_Female)

Schematic source : ProgrammingAdapter.sch  (KiCad 5.1.5, 2021-03-11)
BOM source       : ProgrammingAdapter.csv

Usage:
    python programming_adapter_skidl.py
Outputs:
    programming_adapter.net     — KiCad-compatible netlist
    programming_adapter_BOM.csv — grouped Bill of Materials
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

for k in ['KICAD_SYMBOL_DIR','KICAD6_SYMBOL_DIR','KICAD7_SYMBOL_DIR',
          'KICAD8_SYMBOL_DIR','KICAD9_SYMBOL_DIR']:
    os.environ[k] = app_symbols
for k in ['KICAD_FOOTPRINT_DIR','KICAD8_FOOTPRINT_DIR']:
    os.environ[k] = app_footprints

from skidl import *  # noqa: E402

lib_search_paths[KICAD].extend([app_symbols, user_config])
footprint_search_paths[KICAD].append(app_footprints)
set_default_tool(KICAD)


# =============================================================================
# 2.  NETS
# =============================================================================
gnd   = Net('GND')
vcc   = Net('+3V3')    # VCC rail (3.3V supplied via ISP connector)
miso  = Net('MISO')
mosi  = Net('MOSI')
sck   = Net('SCK')
reset = Net('RESET')


# =============================================================================
# 3.  FOOTPRINTS
# =============================================================================
FP_ISP_6    = 'Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical'
FP_HDR_1x03 = 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical'


# =============================================================================
# 4.  J1, J2 — AVR-ISP-6  (2×3 pin header)
#     Standard ISP-6 pinout:
#       Pin 1: MISO   Pin 2: VCC
#       Pin 3: SCK    Pin 4: MOSI
#       Pin 5: ~RST   Pin 6: GND
# =============================================================================
isp_t = Part('Device', 'R', dest=TEMPLATE)
isp_t.name, isp_t.ref_prefix = 'AVR-ISP-6', 'J'
isp_t.footprint = FP_ISP_6
isp_t.pins = [
    Pin(num='1', name='MISO'),
    Pin(num='2', name='VCC'),
    Pin(num='3', name='SCK'),
    Pin(num='4', name='MOSI'),
    Pin(num='5', name='~RST'),
    Pin(num='6', name='GND'),
]

j1 = isp_t()
j1.ref = 'J1'; j1.value = 'AVR-ISP-6'
j1['MISO'] += miso
j1['VCC']  += vcc
j1['SCK']  += sck
j1['MOSI'] += mosi
j1['~RST'] += reset
j1['GND']  += gnd

j2 = isp_t()
j2.ref = 'J2'; j2.value = 'AVR-ISP-6'
j2['MISO'] += miso
j2['VCC']  += vcc
j2['SCK']  += sck
j2['MOSI'] += mosi
j2['~RST'] += reset
j2['GND']  += gnd


# =============================================================================
# 5.  J3 — Conn_01x03_Female  (1×3 pin header)
#     Pin 1: +3V3 (VCC)
#     Pin 2: MISO
#     Pin 3: GND
# =============================================================================
j3_t = Part('Device', 'R', dest=TEMPLATE)
j3_t.name, j3_t.ref_prefix = 'Conn_01x03_Female', 'J'
j3_t.footprint = FP_HDR_1x03
j3_t.pins = [
    Pin(num='1', name='Pin_1'),
    Pin(num='2', name='Pin_2'),
    Pin(num='3', name='Pin_3'),
]

j3 = j3_t()
j3.ref = 'J3'; j3.value = 'Conn_01x03_Female'
j3[1] += vcc
j3[2] += miso
j3[3] += gnd


# =============================================================================
# 6.  OUTPUT: KiCad netlist  +  CSV BOM
# =============================================================================

def generate_csv_bom(filename: str = 'programming_adapter_BOM.csv') -> None:
    bom_groups: dict = defaultdict(list)
    for part in default_circuit.parts:  # type: ignore[attr-defined]
        if getattr(part, 'dest', None) == TEMPLATE:  # type: ignore[name-defined]
            continue
        ref = getattr(part, 'ref', None)
        if not ref:
            continue
        key = (getattr(part,'name',''), getattr(part,'value',''), getattr(part,'footprint',''))
        bom_groups[key].append(ref)

    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Quantity','Reference(s)','Value','Part Name','Footprint'])
        for (name,value,footprint), refs in sorted(bom_groups.items()):
            refs.sort()
            writer.writerow([len(refs), ', '.join(refs), value, name, footprint])
    print(f'✅  BOM   saved  →  {filename}')


generate_netlist(filename='programming_adapter.net')
print('✅  Netlist saved  →  programming_adapter.net')
generate_csv_bom(filename='programming_adapter_BOM.csv')
