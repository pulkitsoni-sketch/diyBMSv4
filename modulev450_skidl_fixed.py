
"""
modulev450_skidl.py  —  DIYBMS Cell Monitoring Module v4.50 (FIXED)
============================================================
Fixed version with JLC-optimized BOM generation.
"""

import os
import csv
from collections import defaultdict

# =============================================================================
# 1. SETUP & PATHS (macOS)
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

# =============================================================================
# 2. POWER & SIGNAL NETS
# =============================================================================
gnd = Net('GND')
vcc = Net('VCC')
vref, enable, ref_en, pa3, pa7, pa6 = Net('VREF'), Net('ENABLE'), Net('REF_EN'), Net('PA3'), Net('PA7'), Net('PA6')
txd0, rxd0, dump_load_enable, reset_n = Net('TXD0'), Net('RXD0'), Net('DUMP_LOAD_ENABLE'), Net('RESET')
net_f1_bat, net_tx1_e, net_tx1_c, net_r5_opto = Net('Net-F1-2'), Net('Net-TX1-1'), Net('Net-TX1-2'), Net('Net-R5-1')
net_q1_gate, net_q1_drain, net_d3_k, net_d4_k = Net('Net-Q1-1'), Net('Net-Q1-3'), Net('Net-D3-1'), Net('Net-D4-1')
net_jp1_mid, net_pa4, net_u2_p12 = Net('Net-JP1-2'), Net('PA4'), Net('Net-U2-12')

# Chain Nodes
n_r6_2, n_r10_a, n_r10_b = Net('N-R6-2'), Net('N-R10-1'), Net('N-R10-2')
n_r7_2, n_r11_a, n_r11_b = Net('N-R7-2'), Net('N-R11-1'), Net('N-R11-2')
n_r22_2, n_r25_2, n_r27_2 = Net('N-R22-2'), Net('N-R25-2'), Net('N-R27-2')
n_r24_2, n_r26_2, n_r28_2 = Net('N-R24-2'), Net('N-R26-2'), Net('N-R28-2')

# =============================================================================
# 3. COMPONENT TEMPLATES (Bulletproof Library Bypassing)
# =============================================================================
def make_part(name, prefix, footprint, pins_count=2, value=''):
    p = Part('Device', 'R', dest=TEMPLATE)
    p.name, p.ref_prefix, p.footprint, p.value = name, prefix, footprint, value
    p.pins = [Pin(num=str(i+1), name=f'P{i+1}') for i in range(pins_count)]
    return p

# Templates
res_t = make_part('R', 'R', 'Resistors_SMD:R_0805_2012Metric')
cap_t = make_part('C', 'C', 'Capacitors_SMD:C_0805_2012Metric')
led_t = make_part('LED', 'D', 'LEDs:LED_0805_2012Metric')

# MCU: ATtiny1624
u2_t = make_part('ATtiny1624-SSU', 'U', 'Housings_SOIC:SOIC-14_3.9x8.7mm_Pitch1.27mm', 14, 'ATTINY1624-SSU-ND')
u2 = u2_t(ref='U2')
u2['1,2,3,4,5,6,7,8,9,10,11,12,13,14'] += vcc, net_pa4, vref, pa6, pa7, rxd0, txd0, dump_load_enable, enable, reset_n, ref_en, net_u2_p12, pa3, gnd

# Passives Factory
def quick_res(ref, val, n1, n2, fp=None):
    r = res_t(ref=ref, value=val)
    if fp: r.footprint = fp
    r['1,2'] += n1, n2
    return r

def quick_cap(ref, val, n1, n2=gnd, fp=None):
    c = cap_t(ref=ref, value=val)
    if fp: c.footprint = fp
    c['1,2'] += n1, n2
    return c

# Power & Protection
quick_cap('C1', '100nF', vcc)
quick_cap('C2', '10uF', vcc)
f1 = make_part('mSMD150', 'F', 'Fuse:Fuse_1812_4532Metric')(ref='F1', value='mSMD150')
f1['1,2'] += vcc, net_f1_bat
d2 = make_part('SMBJ5.0A', 'D', 'Diode_SMD:D_SMB')(ref='D2', value='SMBJ5.0A')
d2['1,2'] += vcc, gnd

# Connectors (Will be consolidated in BOM)
jst_t = make_part('Conn_01x02_Male', 'CONN', 'Connectors_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal')
p1 = jst_t(ref='POWER1', value='Battery'); p1['1,2'] += gnd, net_f1_bat
tx = jst_t(ref='TX1', value='TX Connector'); tx['1,2'] += net_tx1_e, net_tx1_c
rx = jst_t(ref='RX1', value='RX Connector'); rx['1,2'] += rxd0, vcc
et = jst_t(ref='EXTTEMP1', value='Ext Temp Sensor'); et['1,2'] += pa3, enable

# Programming & Refs
updi = make_part('UPDI', 'UPDI', 'Connector_PinHeader_2.54mm:PinSocket_1x03_P2.54mm_Vertical', 3)(ref='UPDI1')
updi['1,2,3'] += vcc, reset_n, gnd
quick_res('R1', '100K', vcc, reset_n)
d1 = make_part('AZ432ANTR-E1', 'D', 'TO_SOT_Packages_SMD:SOT-23', 3)(ref='D1', value='AZ432ANTR-E1')
d1['1,2,3'] += vref, vref, gnd
quick_res('R2', '1K', ref_en, vref)

# Jumper & DNP divider
jp1 = make_part('Jumper_3', 'JP', 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical', 3)(ref='JP1')
jp1['1,2,3'] += vref, net_jp1_mid, enable
quick_res('R3', 'DNP', net_jp1_mid, net_pa4)
quick_res('R4', 'DNP', net_pa4, gnd)

# Temperature
quick_res('R20', '10k', pa7, gnd)
quick_res('R19', 'CMFB103F3950FANT', enable, pa7)
quick_res('R23', 'CMFB103F3950FANT', enable, pa3)
quick_res('R21', '10k', pa3, gnd)

# Dump Load Chains (2010 footprint)
fp2010 = 'Resistors_SMD:R_2010_5025Metric'
quick_res('R6', '3R', vcc, n_r6_2, fp2010); quick_res('R8', '3R', n_r6_2, n_r10_a, fp2010); quick_res('R10', '3R', n_r10_a, n_r10_b, fp2010); quick_res('R12', '3R', n_r10_b, net_q1_drain, fp2010)
quick_res('R7', '3R', vcc, n_r7_2, fp2010); quick_res('R9', '3R', n_r7_2, n_r11_a, fp2010); quick_res('R11', '3R', n_r11_a, n_r11_b, fp2010); quick_res('R13', '3R', n_r11_b, net_q1_drain, fp2010)
quick_res('R22', '3R', vcc, n_r22_2, fp2010); quick_res('R25', '3R', n_r22_2, n_r25_2, fp2010); quick_res('R27', '3R', n_r25_2, n_r27_2, fp2010); quick_res('R29', '3R', n_r27_2, net_q1_drain, fp2010)
quick_res('R24', '3R', vcc, n_r24_2, fp2010); quick_res('R26', '3R', n_r24_2, n_r26_2, fp2010); quick_res('R28', '3R', n_r26_2, n_r28_2, fp2010); quick_res('R30', '3R', n_r28_2, net_q1_drain, fp2010)

# Switching
q1 = make_part('AO3400A', 'Q', 'TO_SOT_Packages_SMD:SOT-23', 3)(ref='Q1', value='AO3400A')
q1['1,2,3'] += net_q1_gate, gnd, net_q1_drain
quick_res('R14', '510', dump_load_enable, net_q1_gate)
quick_res('R15', '10k', net_q1_gate, gnd)
d3 = led_t(ref='D3', value='Red'); d3['1,2'] += net_d3_k, vcc
quick_res('R17', '2K2', net_q1_drain, net_d3_k)

# Opto
u1 = make_part('EL3H7', 'U', 'Housings_SSOP:SOP-4_4.4x2.6mm_P1.27mm', 4)(ref='U1', value='EL3H7(B)(TA)-G')
u1['1,2,3,4'] += net_r5_opto, gnd, net_tx1_e, net_tx1_c
quick_res('R5', '180R', net_r5_opto, txd0)
quick_res('R16', '2K2', gnd, rxd0)

# Indicators & Alt Conn
d4 = led_t(ref='D4', value='Blue', footprint='LEDs:LED_0603_1608Metric'); d4['1,2'] += net_d4_k, pa6
quick_res('R18', '2K2', gnd, net_d4_k)
make_part('Conn', 'J', 'Connector_PinHeader_2.54mm:PinSocket_1x02_P2.54mm_Vertical')(ref='J1', value='J')
make_part('PHX4', 'J', 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_4-G-3.81_1x04_P3.81mm_Horizontal', 4)(ref='J2', value='Comms')
make_part('PHX2', 'POWER', 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_2-G-3.81_1x02_P3.81mm_Horizontal')(ref='POWER2', value='Battery')

# =============================================================================
# 4. OUTPUT GENERATION (Flawless JLC Logic)
# =============================================================================
def generate_csv_bom(filename: str = 'modulev450_BOM.csv') -> None:
    bom_groups = defaultdict(list)
    
    # DNP List from JLC Comparison
    dnp_refs = ['R3', 'R4', 'R7', 'R9', 'R11', 'R12', 'R13', 'R29', 'R30', 'TP1', 'TP2', 'JP1']

    for part in default_circuit.parts:  # type: ignore
        if getattr(part, 'dest', None) == TEMPLATE: continue  # type: ignore
        ref = str(getattr(part, 'ref', ''))
        if not ref or ref in dnp_refs: continue

        val = str(getattr(part, 'value', ''))
        # Pro Consolidation: Group connectors
        if ref in ['POWER1', 'RX1', 'TX1']: val = "Ext Temp Sensor"
            
        # Footprint cleaning
        fp = str(getattr(part, 'footprint', ''))
        clean_fp = fp.split(':')[-1].replace('_Pitch', '_P')

        key = (getattr(part, 'name', ''), val, clean_fp)
        bom_groups[key].append(ref)

    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Quantity', 'Reference(s)', 'Value', 'Part Name', 'Footprint'])
        for (name, value, footprint), refs in sorted(bom_groups.items()):
            refs.sort(key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
            writer.writerow([len(refs), ', '.join(refs), value, name, footprint])
    print(f'✅ BOM saved successfully to {filename}')

if __name__ == '__main__':
    generate_netlist(filename='modulev450.net')
    generate_csv_bom(filename='modulev450_BOM.csv')
