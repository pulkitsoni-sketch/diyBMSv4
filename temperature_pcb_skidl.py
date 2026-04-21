"""
temperature_pcb_skidl.py  —  DIYBMS Temperature Probe PCB
==========================================================
Minimal two-component probe PCB: a 10K NTC thermistor (TH1) wired
directly across a 2-pin JST PH SMD horizontal connector (J1).
The resistor divider lives on the main controller board; this PCB
just mounts the NTC and provides the JST plug.

Also carries one mounting hole (H1) — mechanical only, no nets.

Schematic source : TemperaturePCB.kicad_sch  (KiCad 7.0.11)
BOM source       : TemperaturePCB-bom.csv

Usage:
    python temperature_pcb_skidl.py
Outputs:
    temperature_pcb.net          — KiCad-compatible netlist
    temperature_pcb_BOM.csv      — grouped Bill of Materials
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
#     Two signal lines — named to match the host-board convention where
#     pin 1 carries the divided voltage (NTC mid-point) and pin 2 is GND.
# =============================================================================
ntc_a = Net('NTC_A')   # J1 pin 1 / TH1 pin 1
ntc_b = Net('NTC_B')   # J1 pin 2 / TH1 pin 2


# =============================================================================
# 3.  J1 — S2B-PH-SM4-TB(LF)(SN)  JST PH SMD 2-pin horizontal connector
# =============================================================================
j1_t = Part('Device', 'R', dest=TEMPLATE)
j1_t.name, j1_t.ref_prefix = 'Conn_01x02_Socket', 'J'
j1_t.footprint = 'Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal'
j1_t.pins = [Pin(num='1', name='Pin_1'), Pin(num='2', name='Pin_2')]

j1 = j1_t()
j1.ref = 'J1'; j1.value = 'S2B-PH-SM4-TB(LF)(SN)'
j1[1] += ntc_a
j1[2] += ntc_b


# =============================================================================
# 4.  TH1 — CMFB103F3950FANT  10K NTC thermistor  (0805)
# =============================================================================
th1_t = Part('Device', 'R', dest=TEMPLATE)
th1_t.name, th1_t.ref_prefix = 'Thermistor_NTC', 'TH'
th1_t.footprint = 'Resistor_SMD:R_0805_2012Metric'
th1_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]

th1 = th1_t()
th1.ref = 'TH1'; th1.value = '10K NTC'
th1[1] += ntc_a
th1[2] += ntc_b


# =============================================================================
# 5.  OUTPUT: KiCad netlist  +  CSV BOM
# =============================================================================

def generate_csv_bom(filename: str = 'temperature_pcb_BOM.csv') -> None:
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


generate_netlist(filename='temperature_pcb.net')
print('✅  Netlist saved  →  temperature_pcb.net')
generate_csv_bom(filename='temperature_pcb_BOM.csv')
