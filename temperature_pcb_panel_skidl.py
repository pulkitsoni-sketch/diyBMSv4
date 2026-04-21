"""
temperature_pcb_panel_skidl.py  —  DIYBMS Temperature Probe PCB Panel (12-up)
==============================================================================
Panel of 12 identical temperature probe PCBs manufactured together.
Each cell = one JST PH 2-pin connector (Jx) + one 10K NTC thermistor (THx).
All 12 cells are electrically independent; nets are isolated per cell.

Note: connector changed from SMD (S2B-PH-SM4-TB) to through-hole/horizontal
      (S2B-PH-K) vs the single-PCB version.

BOM source : TemperaturePCB_bom_jlc.csv

Usage:
    python temperature_pcb_panel_skidl.py
Outputs:
    temperature_pcb_panel.net      — KiCad-compatible netlist
    temperature_pcb_panel_BOM.csv  — grouped Bill of Materials
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
# 2.  FOOTPRINTS
# =============================================================================
FP_JST_PH2 = 'Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal'
FP_R0805   = 'Resistor_SMD:R_0805_2012Metric'


# =============================================================================
# 3.  COMPONENT TEMPLATES
# =============================================================================
j_t = Part('Device', 'R', dest=TEMPLATE)
j_t.name, j_t.ref_prefix = 'Conn_01x02_Socket', 'J'
j_t.footprint = FP_JST_PH2
j_t.pins = [Pin(num='1', name='Pin_1'), Pin(num='2', name='Pin_2')]

th_t = Part('Device', 'R', dest=TEMPLATE)
th_t.name, th_t.ref_prefix = 'Thermistor_NTC', 'TH'
th_t.footprint = FP_R0805
th_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]


# =============================================================================
# 4.  12 IDENTICAL PROBE CELLS  (each electrically isolated)
# =============================================================================
for n in range(1, 13):
    a = Net(f'NTC{n}_A')
    b = Net(f'NTC{n}_B')

    j = j_t()
    j.ref = f'J{n}'; j.value = 'S2B-PH-K(LF)(SN)'
    j[1] += a; j[2] += b

    th = th_t()
    th.ref = f'TH{n}'; th.value = '10K NTC'
    th[1] += a; th[2] += b


# =============================================================================
# 5.  OUTPUT: KiCad netlist  +  CSV BOM
# =============================================================================

def generate_csv_bom(filename: str = 'temperature_pcb_panel_BOM.csv') -> None:
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


generate_netlist(filename='temperature_pcb_panel.net')
print('✅  Netlist saved  →  temperature_pcb_panel.net')
generate_csv_bom(filename='temperature_pcb_panel_BOM.csv')
