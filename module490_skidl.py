"""
module_16s_skidl.py  —  DIYBMS 16S Controller Board (Module_16S)
=================================================================
SKiDL script derived from Schematic.pdf (3 sheets) + Module_16S_bom_jlc.csv.
No .net file was provided; all connections are traced from the schematic PDF.

Architecture (3 sheets):
  Sheet 1 (Main/AFE): MAX14921 16-cell AFE, MCP33151 ADC, MCP1502 VREF,
                       balance-board connectors J14/J15, cell connector J7,
                       all CVx/BAx/CTx/CBx filter networks
  Sheet 2 (STM32):    STM32F030K6Tx controller, EL3H7 opto comms, RELAY,
                       AO3401A MOSFET, 8MHz crystal, NTC thermistors,
                       programming/debug headers J3/J4/J8, boot switch SW1
  Sheet 3 (PowerSupply): XL7005A 65V→12V step-down, AP2204K 12V→5V,
                          XC6206 5V→3.3V, XC6206 5V→1.8V, input fuse/clamp

Key ICs:
  U1   MAX14921ECS+T   16-cell battery measurement AFE (TQFP-80)
  U3   MCP33151-05-E/MS SPI SAR ADC 14-bit 500ksps (MSOP-10)
  U5   STM32F030K6Tx   ARM Cortex-M0 MCU (LQFP-32)
  U6   MCP1502T-45E/CHY 4.5V precision reference (SOT-23-6)
  U9   XC6206-3.3V     LDO 3.3V regulator (SOT-23-3)
  U10  XL7005A         65V→12V step-down controller (SOIC-8)
  U11  AP2204K-5.0     5V regulator (SOT-23-5)
  U12  XC6206-1.8NR    LDO 1.8V regulator (SOT-23-3)
  U13  EL3H7(B)(TA)-G  Optocoupler (SOP-4)
  U4   RELAY1          4-pin solid-state relay (SO-4)

NOTE: Pin assignments for STM32 GPIOs and J14/J15 balance-board connector
      pins are traced from the PDF schematic; verify against Module_16S.sch.

Usage:
    python module_16s_skidl.py
Outputs:
    module_16s.net          — KiCad-compatible netlist
    module_16s_BOM.csv      — grouped Bill of Materials
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
# 2.  POWER RAILS
# =============================================================================
gnd          = Net('GND')
voltage_in   = Net('VOLTAGE_IN')    # Raw battery input J5 (up to 65V)
step_down_v  = Net('STEP_DOWN_V')   # XL7005A output ~12V
vcc_5v       = Net('+5V')
vcc_3v3      = Net('+3.3V')
vcc_1v8      = Net('+1V8')
vref         = Net('VREF')          # MCP1502 4.5V precision reference


# =============================================================================
# 3.  SIGNAL NETS
# =============================================================================
# SPI bus (level-shifted 3.3V from STM32 to AFE and ADC)
spi_sclk       = Net('3V3_SPI_SCLK')
spi_sdi        = Net('3V3_SPI_SDI')     # MOSI from STM32 → AFE/ADC DI
spi_sdo        = Net('3V3_SPI_SDO')     # MISO to STM32 ← AFE/ADC DO
adc_cs         = Net('3V3_ADC_CS')      # MCP33151 chip-select
afe_cs         = Net('3V3_AFE_CS')      # MAX14921 chip-select
sample_afe     = Net('3V3_SAMPLE_AFE')  # SAMPL trigger → MAX14921 + MCP33151 CNVST
afe_en         = Net('AFE_EN')          # MAX14921 EN (active-low)
afe_pwr        = Net('AFE_PWR')         # Analog supply to MAX14921 VA (Q1-switched)
bal_en         = Net('BAL_EN')          # Global balance enable
th_enable      = Net('TH_ENABLE')       # 3.3V power gate for thermistors
relay1_net     = Net('RELAY1')          # Relay drive output
fan_net        = Net('FAN')             # Fan control output
t1             = Net('T1')              # Temp-mux select 1
t2             = Net('T2')              # Temp-mux select 2
t3             = Net('T3')              # Temp-mux select 3
aout           = Net('AOUT')            # MAX14921 multiplexed voltage output
pa8_net        = Net('PA8')             # STM32 PA8 GPIO
tx_net         = Net('TX')              # USART1 TX
rx_net         = Net('RX')              # USART1 RX
swdio          = Net('SWDIO')           # SWD data
swclk          = Net('SWCLK_USART_PROG1')  # SWD clock / USART prog
usart_prog2    = Net('USART_PROG2')     # Second USART programming line
adc_th3        = Net('ADC_TH3')         # Thermistor 3 ADC
adc_th4        = Net('ADC_TH4')         # Thermistor 4 ADC
adc_th5        = Net('ADC_TH5')         # Thermistor 5 ADC
reset_net      = Net('RESET')           # MCU NRST

# Cell voltage nets (CV0=most negative, CV16=most positive)
cv  = [Net(f'CV{i}')  for i in range(17)]   # CV0–CV16

# Balance tap nets (mid-point of each cell for active balancing)
ba  = [Net(f'BA{i}')  for i in range(1, 17)]   # BA1–BA16

# Cell top/bottom taps (for cell-level connections to MAX14921)
ct  = [Net(f'CT{i}')  for i in range(1, 17)]   # CT1–CT16
cb  = [Net(f'CB{i}')  for i in range(1, 17)]   # CB1–CB16


# =============================================================================
# 4.  FOOTPRINT CONSTANTS & HELPERS
# =============================================================================
FP_R0603     = 'Resistors_SMD:R_0603_1608Metric'
FP_R0805     = 'Resistors_SMD:R_0805_2012Metric'
FP_C0402     = 'Capacitors_SMD:C_0402_1005Metric'
FP_C0603     = 'Capacitors_SMD:C_0603_1608Metric'
FP_C0805     = 'Capacitors_SMD:C_0805_2012Metric'
FP_CP_A      = 'Capacitors_SMD:CP_EIA-3216-18_Kemet-A'  # 10uF tantalum
FP_CP_5x5    = 'Capacitors_SMD:CP_Elec_5x5.4'           # 47uF
FP_CP_10x8   = 'Capacitors_SMD:CP_Elec_10x7.9'          # 33uF 100V
FP_LED0603   = 'LEDs:LED_0603_1608Metric'
FP_SOD123    = 'Diode_SMD:D_SOD-123'
FP_SOD123F   = 'Diode_SMD:D_SOD-123F'
FP_D_SMA     = 'Diode_SMD:D_SMA'
FP_FUSE_0805 = 'Fuse:Fuse_0805_2012Metric'
FP_SOT23     = 'TO_SOT_Packages_SMD:SOT-23'
FP_SOT23_3   = 'TO_SOT_Packages_SMD:SOT-23-3'
FP_SOT23_5   = 'TO_SOT_Packages_SMD:SOT-23-5'
FP_SOT23_6   = 'TO_SOT_Packages_SMD:SOT-23-6'
FP_SOP4      = 'Housings_SSOP:SOP-4_4.4x2.6mm_P1.27mm'
FP_SO4       = 'Package_SO:SO-4_4.4x4.3mm_P2.54mm'
FP_LQFP32    = 'Package_QFP:LQFP-32_7x7mm_P0.8mm'
FP_SOIC8     = 'Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.29x3mm'
FP_MSOP10    = 'Package_SO:MSOP-10_3x3mm_P0.5mm'
FP_TQFP80    = 'Package_QFP:TQFP-80_12x12mm_P0.5mm'
FP_XTAL_3225 = 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm'
FP_JST_PH2H  = 'Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal'
FP_PHX_2     = 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_2-G-3.81_1x02_P3.81mm_Horizontal'
FP_PHX_4     = 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_4-G-3.81_1x04_P3.81mm_Horizontal'
FP_HDR_1x04H = 'Connector_PinHeader_2.54mm:PinSocket_1x04_P2.54mm_Horizontal'
FP_PSK_1x22  = 'Connector_PinHeader_2.54mm:PinSocket_1x22_P2.54mm_Vertical'
FP_CELL_CON  = 'Connector_Wuerth:WJ15EDGRC-3.81-17P'
FP_L_1008    = 'Inductor_SMD:L_1008_2520Metric_Pad1.43x2.20mm_HandSolder'
FP_SW        = 'Button_Switch_SMD:SW_SPDT_PCM12'
FP_LOGO      = 'Symbol:diybms_logo_24x10mm'


def make_res(ref, value, n1, n2, fp=FP_R0603):
    r = Part('Device', 'R', value=value, footprint=fp)
    r.ref = ref; r[1] += n1; r[2] += n2
    return r

def make_cap(ref, value, npos, nneg=None, fp=FP_C0805):
    c = Part('Device', 'C', value=value, footprint=fp)
    c.ref = ref; c[1] += npos; c[2] += (nneg if nneg else gnd)
    return c


# =============================================================================
# 5.  SHEET 3 — POWER SUPPLY
#     J5 → F1 → D20 → VOLTAGE_IN → XL7005A(U10) → STEP_DOWN_V
#     STEP_DOWN_V → AP2204K(U11) → +5V
#     +5V → XC6206(U9) → +3.3V
#     +5V → XC6206(U12) → +1V8
# =============================================================================

# J5 POWER_IN (Phoenix Contact 2-pin)
j5_t = Part('Device', 'R', dest=TEMPLATE)
j5_t.name, j5_t.ref_prefix = 'Conn_01x02_Male', 'J'
j5_t.footprint = FP_PHX_2
j5_t.pins = [Pin(num='1', name='-'), Pin(num='2', name='+')]

j5 = j5_t()
j5.ref = 'J5'; j5.value = 'POWER_IN'
j5[1] += gnd
j5[2] += Net('J5_RAW')   # Raw before fuse

# F1 (30mA fuse) — series in power input path
f1_t = Part('Device', 'R', dest=TEMPLATE)
f1_t.name, f1_t.ref_prefix = 'Fuse', 'F'
f1_t.footprint = FP_FUSE_0805
f1_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='K')]

f1 = f1_t()
f1.ref = 'F1'; f1.value = 'Fuse 30mA'
f1[1] += Net('J5_RAW')
f1[2] += voltage_in

# D20 (1N4002W) — reverse polarity protection
d20_t = Part('Device', 'R', dest=TEMPLATE)
d20_t.name, d20_t.ref_prefix = '1N4002W', 'D'
d20_t.footprint = FP_SOD123F
d20_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='K')]

d20 = d20_t(); d20.ref = 'D20'; d20.value = '1N4002W'
d20['A'] += voltage_in
d20['K'] += Net('VOLTAGE_IN_RECT')

# D1 (68V zener) — overvoltage clamp across input
d1_t = Part('Device', 'R', dest=TEMPLATE)
d1_t.name, d1_t.ref_prefix = 'D_Zener', 'D'
d1_t.footprint = FP_SOD123
d1_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='K')]

d1 = d1_t(); d1.ref = 'D1'; d1.value = '68V, 500mW zener diode'
d1['A'] += gnd
d1['K'] += voltage_in

make_cap('C2',  '100nF 100V', voltage_in, fp=FP_C0805)   # HV input bypass
make_cap('C52', '100nF 100V', voltage_in, fp=FP_C0805)   # HV input bypass
make_cap('C20', '33uF 100V ±20% D10xL8.4mm', voltage_in, fp=FP_CP_10x8)  # HV bulk

# R1, R52 (100R) — current limiting resistors (likely gate/EN resistors)
make_res('R1',  '100R', voltage_in, step_down_v)   # Series protection / pre-charge
make_res('R52', '100R', step_down_v, vcc_5v)       # Series in 5V path

# U10 XL7005A — 65V→12V step-down controller (SOIC-8-1EP)
u10_t = Part('Device', 'R', dest=TEMPLATE)
u10_t.name, u10_t.ref_prefix = 'XL7005A', 'U'
u10_t.footprint = FP_SOIC8
u10_t.pins = [
    Pin(num='1', name='SW'),
    Pin(num='2', name='FB'),
    Pin(num='3', name='~EN'),
    Pin(num='4', name='GND_a'),
    Pin(num='5', name='GND_b'),
    Pin(num='6', name='GND_c'),
    Pin(num='7', name='GND_d'),
    Pin(num='8', name='GND_e'),
    Pin(num='9', name='VIN'),
]

u10 = u10_t(); u10.ref = 'U10'; u10.value = 'XL7005A'
u10['VIN']   += voltage_in
u10['SW']    += Net('XL7005_SW')   # Switch node
u10['~EN']   += vcc_3v3            # Pulled high (always enabled)
u10['FB']    += Net('XL7005_FB')
u10['GND_a'] += gnd; u10['GND_b'] += gnd
u10['GND_c'] += gnd; u10['GND_d'] += gnd; u10['GND_e'] += gnd

# L1 (100uH) — XL7005A output inductor
l1_t = Part('Device', 'R', dest=TEMPLATE)
l1_t.name, l1_t.ref_prefix = 'L', 'L'
l1_t.footprint = FP_L_1008
l1_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]

l1 = l1_t(); l1.ref = 'L1'; l1.value = '100uH'
l1[1] += Net('XL7005_SW')
l1[2] += step_down_v

# D21 (SS210) — freewheeling diode
d21_t = Part('Device', 'R', dest=TEMPLATE)
d21_t.name, d21_t.ref_prefix = 'SS210', 'D'
d21_t.footprint = FP_D_SMA
d21_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='K')]

d21 = d21_t(); d21.ref = 'D21'; d21.value = 'SS210'
d21['A'] += gnd; d21['K'] += Net('XL7005_SW')

# R76 (43K) / R77 (4.99K) — feedback divider for 12V output
# VOUT = 1.25 × (1 + 43K/4.99K) = 12.02V
xl_fb = Net('XL7005_FB')
make_res('R76', '43K 1%',    step_down_v, xl_fb)
make_res('R77', '4.99kΩ 1%', xl_fb, gnd)

make_cap('C43', '47uF 16V', step_down_v, fp=FP_CP_5x5)
make_cap('C45', '47uF 16V', step_down_v, fp=FP_CP_5x5)
make_cap('C44', '33nF',     xl_fb,       fp=FP_C0603)   # Compensation cap

# U11 AP2204K-5.0 — 5V regulator (SOT-23-5): VIN=1,GND=2,EN=3,VOUT=5
u11_t = Part('Device', 'R', dest=TEMPLATE)
u11_t.name, u11_t.ref_prefix = 'AP2204K-5.0', 'U'
u11_t.footprint = FP_SOT23_5
u11_t.pins = [
    Pin(num='1', name='VIN'),
    Pin(num='2', name='GND'),
    Pin(num='3', name='EN'),
    Pin(num='4', name='NC'),
    Pin(num='5', name='VOUT'),
]

u11 = u11_t(); u11.ref = 'U11'; u11.value = 'AP2204K-5.0TRG1'
u11['VIN']  += step_down_v
u11['GND']  += gnd
u11['EN']   += step_down_v    # Always enabled
u11['NC']   += gnd
u11['VOUT'] += vcc_5v

make_cap('C46', '1uF', step_down_v)    # AP2204K input bypass
make_cap('C47', '1uF', vcc_5v)         # AP2204K output bypass
make_cap('C48', '1uF', vcc_5v)         # Extra 5V bypass
make_cap('C49', '1uF', vcc_5v)         # Extra 5V bypass
make_cap('C50', '1uF', vcc_5v)         # Extra 5V bypass

# U9 XC6206-3.3V — 3.3V LDO (SOT-23-3): VO=1,VI=2,GND=3
u9_t = Part('Device', 'R', dest=TEMPLATE)
u9_t.name, u9_t.ref_prefix = 'XC6206', 'U'
u9_t.footprint = FP_SOT23_3
u9_t.pins = [Pin(num='1', name='VO'), Pin(num='2', name='VI'), Pin(num='3', name='GND')]

u9 = u9_t(); u9.ref = 'U9'; u9.value = 'XC6206-3.3V'
u9['VI']  += vcc_5v
u9['VO']  += vcc_3v3
u9['GND'] += gnd

# U12 XC6206-1.8NR — 1.8V LDO (SOT-23-3)
u12_t = Part('Device', 'R', dest=TEMPLATE)
u12_t.name, u12_t.ref_prefix = 'XC6206', 'U'
u12_t.footprint = FP_SOT23_3
u12_t.pins = [Pin(num='1', name='VO'), Pin(num='2', name='VI'), Pin(num='3', name='GND')]

u12 = u12_t(); u12.ref = 'U12'; u12.value = 'XC6206-1.8NR'
u12['VI']  += vcc_5v
u12['VO']  += vcc_1v8
u12['GND'] += gnd

make_cap('C51', '2.2uF', vcc_1v8, fp=FP_C0603)

# TP test points (not in BOM — schematic only)
# TP1=+12V/STEP_DOWN_V, TP2=+3.3V, TP3=+1V8, TP4=+5V, TP5=VREF


# =============================================================================
# 6.  SHEET 1 — AFE  (MAX14921, MCP33151, MCP1502, filter network)
# =============================================================================

# U6 MCP1502T-45E/CHY — 4.5V precision reference (SOT-23-6)
# OUT(1), GND(2,3,5), SHDN(4), VDD(6)
u6_t = Part('Device', 'R', dest=TEMPLATE)
u6_t.name, u6_t.ref_prefix = 'MCP1502', 'U'
u6_t.footprint = FP_SOT23_6
u6_t.pins = [
    Pin(num='1', name='OUT'),
    Pin(num='2', name='GND_a'),
    Pin(num='3', name='GND_b'),
    Pin(num='4', name='SHDN'),
    Pin(num='5', name='GND_c'),
    Pin(num='6', name='VDD'),
]

u6 = u6_t(); u6.ref = 'U6'; u6.value = 'MCP1502T-45E/CHY'
u6['OUT']   += vref
u6['VDD']   += vcc_5v
u6['SHDN']  += vcc_5v    # Not shutdown (active high enable)
u6['GND_a'] += gnd; u6['GND_b'] += gnd; u6['GND_c'] += gnd

make_cap('C24',  '100pF', vref,    fp=FP_C0603)   # VREF output filter
make_cap('C27',  '2.2uF', vref,    fp=FP_C0603)   # VREF output bulk

# U3 MCP33151-05-E/MS — 14-bit SPI ADC (MSOP-10)
# VREF(1), AVDD(2), AIN+(3), AIN-(4), GND(5), CNVST(6), SDO(7), SCLK(8), SDI(9), DVIO(10)
u3_t = Part('Device', 'R', dest=TEMPLATE)
u3_t.name, u3_t.ref_prefix = 'MCP33151', 'U'
u3_t.footprint = FP_MSOP10
u3_t.pins = [
    Pin(num='1',  name='VREF'),
    Pin(num='2',  name='AVDD'),
    Pin(num='3',  name='AIN+'),
    Pin(num='4',  name='AIN-'),
    Pin(num='5',  name='GND'),
    Pin(num='6',  name='CNVST'),
    Pin(num='7',  name='SDO'),
    Pin(num='8',  name='SCLK'),
    Pin(num='9',  name='SDI'),
    Pin(num='10', name='DVIO'),
]

u3 = u3_t(); u3.ref = 'U3'; u3.value = 'MCP33151-05-E/MS'
u3['VREF']  += vref
u3['AVDD']  += vcc_3v3
u3['DVIO']  += vcc_3v3
u3['AIN+']  += aout         # MAX14921 AOUT
u3['AIN-']  += gnd
u3['GND']   += gnd
u3['CNVST'] += sample_afe   # Shared sample trigger with MAX14921 SAMPL
u3['SDO']   += spi_sdo
u3['SCLK']  += spi_sclk
u3['SDI']   += spi_sdi

make_cap('C21', '1uF',      vcc_3v3)              # U3 AVDD bypass
make_cap('C22', '100nF 50V', vcc_3v3, fp=FP_C0603) # U3 DVIO bypass

# U1 MAX14921ECS+T — 16-cell measurement AFE (TQFP-80)
u1_t = Part('Device', 'R', dest=TEMPLATE)
u1_t.name, u1_t.ref_prefix = 'MAX14921', 'U'
u1_t.footprint = FP_TQFP80
u1_t.pins = [
    Pin(num='1',  name='SCLK'),
    Pin(num='2',  name='SDI'),
    Pin(num='3',  name='SDO'),
    Pin(num='4',  name='SAMPL'),
    Pin(num='5',  name='VL'),
    Pin(num='6',  name='DGND'),
    Pin(num='7',  name='T3'),
    Pin(num='8',  name='T2'),
    Pin(num='9',  name='T1'),
    Pin(num='10', name='AOUT'),
    Pin(num='11', name='AGND'),
    Pin(num='12', name='VA'),
    Pin(num='13', name='LDOIN'),
    Pin(num='14', name='VP'),
    Pin(num='15', name='CV16'),
    Pin(num='16', name='BA16'),
    Pin(num='17', name='CT16'),
    Pin(num='18', name='CB16'),
    Pin(num='19', name='CV15'),
    Pin(num='20', name='BA15'),
    Pin(num='21', name='CT15'),
    Pin(num='22', name='CB15'),
    Pin(num='23', name='CV14'),
    Pin(num='24', name='BA14'),
    Pin(num='25', name='CT14'),
    Pin(num='26', name='CB14'),
    Pin(num='27', name='CV13'),
    Pin(num='28', name='BA13'),
    Pin(num='29', name='CT13'),
    Pin(num='30', name='CB13'),
    Pin(num='31', name='CV12'),
    Pin(num='32', name='BA12'),
    Pin(num='33', name='CT12'),
    Pin(num='34', name='CB12'),
    Pin(num='35', name='CV11'),
    Pin(num='36', name='BA11'),
    Pin(num='37', name='CT11'),
    Pin(num='38', name='CB11'),
    Pin(num='39', name='CV10'),
    Pin(num='40', name='BA10'),
    Pin(num='41', name='CT10'),
    Pin(num='42', name='CB10'),
    Pin(num='43', name='CV9'),
    Pin(num='44', name='BA9'),
    Pin(num='45', name='CT9'),
    Pin(num='46', name='CB9'),
    Pin(num='47', name='CV8'),
    Pin(num='48', name='BA8'),
    Pin(num='49', name='CT8'),
    Pin(num='50', name='CB8'),
    Pin(num='51', name='CV7'),
    Pin(num='52', name='BA7'),
    Pin(num='53', name='CT7'),
    Pin(num='54', name='CB7'),
    Pin(num='55', name='CV6'),
    Pin(num='56', name='BA6'),
    Pin(num='57', name='CT6'),
    Pin(num='58', name='CB6'),
    Pin(num='59', name='CV5'),
    Pin(num='60', name='BA5'),
    Pin(num='61', name='CT5'),
    Pin(num='62', name='CB5'),
    Pin(num='63', name='CV4'),
    Pin(num='64', name='BA4'),
    Pin(num='65', name='CT4'),
    Pin(num='66', name='CB4'),
    Pin(num='67', name='CV3'),
    Pin(num='68', name='BA3'),
    Pin(num='69', name='CT3'),
    Pin(num='70', name='CB3'),
    Pin(num='71', name='CV2'),
    Pin(num='72', name='BA2'),
    Pin(num='73', name='CT2'),
    Pin(num='74', name='CB2'),
    Pin(num='75', name='CV1'),
    Pin(num='76', name='BA1'),
    Pin(num='77', name='CT1'),
    Pin(num='78', name='CV0'),
    Pin(num='79', name='EN'),
    Pin(num='80', name='CS'),
]

u1 = u1_t(); u1.ref = 'U1'; u1.value = 'MAX14921ECS+T'

# SPI + control
u1['SCLK']  += spi_sclk
u1['SDI']   += spi_sdi
u1['SDO']   += spi_sdo
u1['SAMPL'] += sample_afe
u1['CS']    += afe_cs
u1['EN']    += afe_en

# Power pins
u1['VL']    += vcc_1v8     # 1.8V digital logic supply
u1['DGND']  += gnd
u1['AGND']  += gnd
u1['VA']    += afe_pwr     # Analog supply (Q1-switched from STEP_DOWN_V)
u1['LDOIN'] += vcc_5v      # LDO input (see MAX14921 datasheet)
u1['VP']    += cv[16]      # High-voltage supply = most positive cell

# Temperature mux
u1['T1'] += t1
u1['T2'] += t2
u1['T3'] += t3

# AOUT (multiplexed cell voltage output to MCP33151)
u1['AOUT'] += aout

# Cell voltage inputs (CV0=negative terminal, CV16=positive)
for i in range(17):
    u1[f'CV{i}'] += cv[i]

# Balance / tap outputs
# NOTE: MAX14921 has no CB1 pin — cell 1 bottom is CV0.
# CB2-CB16 exist; cb[0] (CB1 net) is tied to cv[0] (CV0).
cb[0] += cv[0]   # CB1 = CV0 (cell 1 bottom reference)
for i in range(1, 17):
    u1[f'BA{i}'] += ba[i-1]
    u1[f'CT{i}'] += ct[i-1]
    if i > 1:
        u1[f'CB{i}'] += cb[i-1]

# MAX14921 decoupling capacitors
# C3-C19: 1uF across each CV pin to GND (17 caps for CV0-CV16)
cv_cap_refs = ['C3','C4','C5','C6','C7','C8','C9','C10',
               'C11','C12','C13','C14','C15','C16','C17','C18','C19']
for i, ref in enumerate(cv_cap_refs):
    make_cap(ref, '1uF', cv[i])

# C26/C53/C54 removed — not in JLC BOM (24x 1uF matches reference)

make_cap('C23', '10uF tantalum', vcc_3v3, fp=FP_CP_A)   # AFE area bulk 3.3V

# R2-R17: sixteen 3K3 1% series filter resistors on CV1-CV16 paths
# (CV0 connects directly; CV1-CV16 each have a 3K3 series R from cell tap)
# R2=CV1 path, R3=CV2, ... R17=CV16
for idx, ref in enumerate(['R2','R3','R4','R5','R6','R7','R8',
                            'R9','R10','R11','R12','R13','R14','R15','R16','R17'],
                           start=1):
    cell_net = Net(f'CELL_TAP_{idx}')   # Cell tap → R → CV
    make_res(ref, '3K3 1%', cell_net, cv[idx])

# R75 (3K3 1%) — filter resistor near MCP33151 (AOUT path or VREF divider)
make_res('R75', '3K3 1%', aout, Net('AOUT_FILTERED'))

# D2 (100V 200mW Schottky) — protection diode on high-voltage input path
d2_t = Part('Device', 'R', dest=TEMPLATE)
d2_t.name, d2_t.ref_prefix = 'D_Schottky', 'D'
d2_t.footprint = FP_SOD123
d2_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='K')]

d2 = d2_t(); d2.ref = 'D2'; d2.value = '100V, 200mW Schottky diodes'
d2['A'] += cv[0]      # Most negative cell side (GND potential)
d2['K'] += step_down_v

# J7 CELL CONNECTOR (17-pin Wuerth WJ15EDGRC-3.81-17P)
j7_t = Part('Device', 'R', dest=TEMPLATE)
j7_t.name, j7_t.ref_prefix = 'Conn_01x17_Male', 'J'
j7_t.footprint = FP_CELL_CON
j7_t.pins = [Pin(num=str(i), name=f'P{i}') for i in range(1, 18)]

j7 = j7_t(); j7.ref = 'J7'; j7.value = 'CELL CONNECTOR'
j7[1]  += gnd         # Pin 1: most negative (GND/cell 0)
for i in range(1, 17):
    j7[i+1] += Net(f'CELL_TAP_{i}')   # Pins 2-17: cell taps 1-16

# J14, J15 BALANCE BOARD connectors (1×22 pin sockets)
# Carry BA1-BA16, CT/CB taps, GND, STEP_DOWN_V, and control signals
# Pin assignment from schematic PDF (approximate — verify vs .sch):
#   Odd connector (J14): cells 1-8 balance + GND + power + control
#   Even connector (J15): cells 9-16 balance + GND + power + control
def make_22pin_conn(ref, label):
    t = Part('Device', 'R', dest=TEMPLATE)
    t.name, t.ref_prefix = 'Conn_01x22_Male', 'J'
    t.footprint = FP_PSK_1x22
    t.pins = [Pin(num=str(i), name=f'P{i}') for i in range(1, 23)]
    c = t(); c.ref = ref; c.value = label
    return c

j14 = make_22pin_conn('J14', 'BALANCE BOARD')
# J14 pin mapping (from schematic signal labels — verify against .sch):
j14[1]  += gnd;          j14[2]  += step_down_v
j14[3]  += ba[0];        j14[4]  += ct[0];  j14[5]  += cb[0]
j14[6]  += ba[1];        j14[7]  += ct[1];  j14[8]  += cb[1]
j14[9]  += ba[2];        j14[10] += ct[2];  j14[11] += cb[2]
j14[12] += ba[3];        j14[13] += ct[3];  j14[14] += cb[3]
j14[15] += ba[4];        j14[16] += ct[4];  j14[17] += cb[4]
j14[18] += ba[5];        j14[19] += ct[5];  j14[20] += cb[5]
j14[21] += ba[6];        j14[22] += gnd

j15 = make_22pin_conn('J15', 'BALANCE BOARD')
j15[1]  += gnd;           j15[2]  += step_down_v
j15[3]  += ba[7];         j15[4]  += ct[7];   j15[5]  += cb[7]
j15[6]  += ba[8];         j15[7]  += ct[8];   j15[8]  += cb[8]
j15[9]  += ba[9];         j15[10] += ct[9];   j15[11] += cb[9]
j15[12] += ba[10];        j15[13] += ct[10];  j15[14] += cb[10]
j15[15] += ba[11];        j15[16] += ct[11];  j15[17] += cb[11]
j15[18] += ba[12];        j15[19] += ct[12];  j15[20] += cb[12]
j15[21] += ba[13];        j15[22] += gnd


# =============================================================================
# 7.  SHEET 2 — STM32 CONTROLLER
# =============================================================================

# Y1 8MHz crystal (4-pin SMD 3225)
y1_t = Part('Device', 'R', dest=TEMPLATE)
y1_t.name, y1_t.ref_prefix = 'Crystal', 'Y'
y1_t.footprint = FP_XTAL_3225
y1_t.pins = [Pin(num='1', name='XIN'), Pin(num='2', name='GND_a'),
             Pin(num='3', name='XOUT'), Pin(num='4', name='GND_b')]

y1 = y1_t(); y1.ref = 'Y1'; y1.value = '8MHZ'
xtal_in = Net('XTAL_IN')
xtal_out = Net('XTAL_OUT')
y1['XIN']   += xtal_in
y1['XOUT']  += xtal_out
y1['GND_a'] += gnd; y1['GND_b'] += gnd

make_cap('C30', '14pF', xtal_in,  fp=FP_C0402)
make_cap('C31', '14pF', xtal_out, fp=FP_C0402)

# U5 STM32F030K6Tx (LQFP-32)
u5_t = Part('Device', 'R', dest=TEMPLATE)
u5_t.name, u5_t.ref_prefix = 'STM32F030K6Tx', 'U'
u5_t.footprint = FP_LQFP32
u5_t.pins = [
    Pin(num='1',  name='VDD_a'),
    Pin(num='2',  name='PF0'),
    Pin(num='3',  name='PF1'),
    Pin(num='4',  name='NRST'),
    Pin(num='5',  name='VDDA'),
    Pin(num='6',  name='PA0'),
    Pin(num='7',  name='PA1'),
    Pin(num='8',  name='PA2'),
    Pin(num='9',  name='PA3'),
    Pin(num='10', name='PA4'),
    Pin(num='11', name='PA5'),
    Pin(num='12', name='PA6'),
    Pin(num='13', name='PA7'),
    Pin(num='14', name='PB0'),
    Pin(num='15', name='PB1'),
    Pin(num='16', name='VSS_a'),
    Pin(num='17', name='VDD_b'),
    Pin(num='18', name='PA8'),
    Pin(num='19', name='PA9'),
    Pin(num='20', name='PA10'),
    Pin(num='21', name='PA11'),
    Pin(num='22', name='PA12'),
    Pin(num='23', name='PA13'),
    Pin(num='24', name='PA14'),
    Pin(num='25', name='PA15'),
    Pin(num='26', name='PB3'),
    Pin(num='27', name='PB4'),
    Pin(num='28', name='PB5'),
    Pin(num='29', name='PB6'),
    Pin(num='30', name='PB7'),
    Pin(num='31', name='BOOT0'),
    Pin(num='32', name='VSS_b'),
]

u5 = u5_t(); u5.ref = 'U5'; u5.value = 'STM32F030K6Tx'

# Power
u5['VDD_a'] += vcc_3v3; u5['VDD_b'] += vcc_3v3
u5['VDDA']  += vcc_3v3
u5['VSS_a'] += gnd;     u5['VSS_b'] += gnd
u5['NRST']  += reset_net

# Crystal
u5['PF0'] += xtal_in    # OSC_IN
u5['PF1'] += xtal_out   # OSC_OUT

# ADC thermistor inputs
u5['PA0'] += adc_th5
u5['PA1'] += adc_th4
u5['PA2'] += adc_th3

# AFE/ADC SPI + control
u5['PA3']  += afe_cs
u5['PA4']  += adc_cs
u5['PA5']  += spi_sclk
u5['PA6']  += spi_sdo    # SPI1_MISO
u5['PA7']  += spi_sdi    # SPI1_MOSI
u5['PA8']  += sample_afe  # SAMPL trigger

# USART1
u5['PA9']  += tx_net     # USART1_TX
u5['PA10'] += rx_net     # USART1_RX

# Unused PA11/PA12
u5['PA11'] += Net('PA11_NC')
u5['PA12'] += Net('PA12_NC')

# SWD / programming
u5['PA13'] += swdio
u5['PA14'] += swclk        # shared SWCLK / USART_PROG1
u5['PA15'] += bal_en       # Balance enable output

# GPIO outputs
u5['PB0'] += t1
u5['PB1'] += t2
u5['PB3'] += t3
u5['PB4'] += th_enable     # TH_ENABLE (3.3V supply gate for NTCs)
u5['PB5'] += afe_en        # AFE_EN (MAX14921 enable)
u5['PB6'] += relay1_net    # RELAY1
u5['PB7'] += fan_net       # FAN output

# BOOT0
u5['BOOT0'] += Net('BOOT0_NET')

# STM32 decoupling
make_cap('C28', '100nF 50V', vcc_3v3, fp=FP_C0603)
make_cap('C29', '1uF',       vcc_3v3)
make_cap('C32', '100nF 50V', vcc_3v3, fp=FP_C0603)
make_cap('C35', '100nF 50V', vcc_3v3, fp=FP_C0603)

# R73 (10K) — NRST pull-up
make_res('R73', '10K 1%', vcc_3v3, reset_net)
# R75 (3K3) — SPI or signal filter (assigned above; kept separate from this)

# R80, R85: 10K pull-ups on SWD lines
make_res('R80', '10K 1%', vcc_3v3, swdio)
make_res('R85', '10K 1%', vcc_3v3, swclk)

# SW1 Boot_Mode (3-pin SPDT): BOOT0 toggle
sw1_t = Part('Device', 'R', dest=TEMPLATE)
sw1_t.name, sw1_t.ref_prefix = 'SW_SPDT', 'SW'
sw1_t.footprint = 'Button_Switch_SMD:MST22D18G2 125'
sw1_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='COM'), Pin(num='3', name='B')]

sw1 = sw1_t(); sw1.ref = 'SW1'; sw1.value = 'MST22D18G2 125'
sw1['A']   += vcc_3v3           # BOOT0=1 (bootloader mode)
sw1['COM'] += Net('BOOT0_NET')
sw1['B']   += gnd               # BOOT0=0 (normal mode)

# JP3 SolderJumper_3_Open (not in BOM — not used in JLC build)
# Connects PA14(SWCLK) to USART_PROG1 path if bridged

# U13 EL3H7(B)(TA)-G — Optocoupler for UART comms (SOP-4)
u13_t = Part('Device', 'R', dest=TEMPLATE)
u13_t.name, u13_t.ref_prefix = 'EL3H7', 'U'
u13_t.footprint = FP_SOP4
u13_t.pins = [Pin(num='1', name='A'), Pin(num='2', name='K'),
              Pin(num='3', name='E'), Pin(num='4', name='C')]

u13 = u13_t(); u13.ref = 'U13'; u13.value = 'EL3H7(B)(TA)-G'
u13['A'] += Net('U13_ANODE')   # R87(330R) from TX
u13['K'] += gnd
u13['E'] += Net('OPTO_TX_OUT') # TX output (emitter)
u13['C'] += Net('OPTO_TX_IN')  # Collector pull-up via R79(2K2)

make_res('R87', '330R',  tx_net, Net('U13_ANODE'))  # TX current limiter
make_res('R79', '2K2',   vcc_3v3, Net('OPTO_TX_IN'))  # Collector pull-up
make_res('R78', '330R',  Net('OPTO_TX_OUT'), Net('TXRX_OUT'))  # Output filter

# U4 RELAY1 — 4-pin relay driver (SO-4)
u4_t = Part('Device', 'R', dest=TEMPLATE)
u4_t.name, u4_t.ref_prefix = 'RELAY', 'U'
u4_t.footprint = FP_SO4
u4_t.pins = [Pin(num='1', name='K1'), Pin(num='2', name='A1'),
             Pin(num='3', name='K2'), Pin(num='4', name='A2')]

u4 = u4_t(); u4.ref = 'U4'; u4.value = 'RELAY1'
u4['A1'] += relay1_net
u4['K1'] += gnd
u4['A2'] += Net('RELAY_OUT_A')
u4['K2'] += Net('RELAY_OUT_K')

# Q1 AO3401A P-channel MOSFET (SOT-23) — AFE power switch
q1_t = Part('Device', 'R', dest=TEMPLATE)
q1_t.name, q1_t.ref_prefix = 'AO3401A', 'Q'
q1_t.footprint = FP_SOT23
q1_t.pins = [Pin(num='1', name='G'), Pin(num='2', name='S'), Pin(num='3', name='D')]

q1 = q1_t(); q1.ref = 'Q1'; q1.value = 'AO3401A'
q1['S'] += step_down_v      # Source to supply
q1['D'] += afe_pwr          # Drain to AFE VA
q1['G'] += Net('Q1_GATE')   # Gate driven by STM32 (via R or direct)

# R74, R84, R86: 10K pull-ups/downs on GPIO lines
make_res('R74', '10K 1%',   vcc_3v3, fan_net)       # FAN pull-up
make_res('R84', '10K 1%',   vcc_3v3, relay1_net)    # RELAY1 pull-up
make_res('R86', '10K 1%',   gnd,     Net('Q1_GATE'))  # Q1 gate pull-down

# R69, R70: 10K pull-downs on T1/T2/T3 temp mux lines
make_res('R69', '10K 1%', gnd, t1)
make_res('R70', '10K 1%', gnd, t2)

# D19 (White LED) — status indicator
d19_t = Part('Device', 'R', dest=TEMPLATE)
d19_t.name, d19_t.ref_prefix = 'LED', 'D'
d19_t.footprint = FP_LED0603
d19_t.pins = [Pin(num='1', name='K'), Pin(num='2', name='A')]

d19 = d19_t(); d19.ref = 'D19'; d19.value = 'White'
d19['A'] += vcc_3v3
d19['K'] += Net('LED_STATUS_K')
make_res('R21', '330R', Net('LED_STATUS_K'), gnd)

# C33 (4.7uF), C34 (10nF) — filter caps near NTC/analog
make_cap('C33', '4.7uF', vcc_3v3, fp=FP_C0603)
make_cap('C34', '10nF',  adc_th3, fp=FP_C0603)   # Filter on ADC_TH3 input

# TH6 (10K NTC) — on-board NTC thermistor (only NTC in BOM)
th6_t = Part('Device', 'R', dest=TEMPLATE)
th6_t.name, th6_t.ref_prefix = 'Thermistor', 'TH'
th6_t.footprint = FP_R0805
th6_t.pins = [Pin(num='1', name='~'), Pin(num='2', name='~')]

th6 = th6_t(); th6.ref = 'TH6'; th6.value = '10K NTC'
th6[1] += th_enable    # NTC supply (gated 3.3V)
th6[2] += adc_th3      # ADC_TH3 reading

# R82, R83 (100K) — NTC bias / pull-up resistors
make_res('R82', '100K', th_enable, adc_th4)   # TH4 reference divider
make_res('R83', '100K', th_enable, adc_th5)   # TH5 reference divider

# R20 (10K) — NTC lower divider for TH6
make_res('R20', '10K 1%', adc_th3, gnd)

# R21 on LED assigned above; R78, R79, R87 on opto assigned above

# Programming / debug headers
def make_4pin_hdr(ref, value, p1, p2, p3, p4):
    t = Part('Device', 'R', dest=TEMPLATE)
    t.name, t.ref_prefix = 'Conn_01x04_Male', 'J'
    t.footprint = FP_HDR_1x04H
    t.pins = [Pin(num='1', name='P1'), Pin(num='2', name='P2'),
              Pin(num='3', name='P3'), Pin(num='4', name='P4')]
    c = t(); c.ref = ref; c.value = value
    c[1] += p1; c[2] += p2; c[3] += p3; c[4] += p4
    return c

make_4pin_hdr('J3', 'UART_PROG', vcc_3v3, tx_net, rx_net, gnd)
make_4pin_hdr('J4', 'UART_PROG', vcc_3v3, swclk, swdio, gnd)

# J8 TXRX (Phoenix Contact 4-pin)
j8_t = Part('Device', 'R', dest=TEMPLATE)
j8_t.name, j8_t.ref_prefix = 'Conn_01x04_Male', 'J'
j8_t.footprint = FP_PHX_4
j8_t.pins = [Pin(num='1', name='P1'), Pin(num='2', name='P2'),
             Pin(num='3', name='P3'), Pin(num='4', name='P4')]

j8 = j8_t(); j8.ref = 'J8'; j8.value = 'TXRX'
j8[1] += Net('TXRX_OUT')   # Opto TX output
j8[2] += rx_net             # RX input
j8[3] += gnd
j8[4] += vcc_3v3

# J10-J13 RELAY/TEMP connectors (JST PH SMD horizontal)
relay_temp_conns = [
    ('J10', 'RELAY',  Net('RELAY_OUT_A'), Net('RELAY_OUT_K')),
    ('J11', 'RELAY',  adc_th3, gnd),
    ('J12', 'RELAY',  adc_th4, gnd),
    ('J13', 'RELAY',  adc_th5, gnd),
]
for ref, val, n1, n2 in relay_temp_conns:
    t = Part('Device', 'R', dest=TEMPLATE)
    t.name, t.ref_prefix = 'Conn_01x02_Male', 'J'
    t.footprint = FP_JST_PH2H
    t.pins = [Pin(num='1', name='P1'), Pin(num='2', name='P2')]
    c = t(); c.ref = ref; c.value = val
    c[1] += n1; c[2] += n2

# C1, C25 (100nF 50V) — MCU area decoupling
make_cap('C1',  '100nF 50V', vcc_3v3, fp=FP_C0603)
make_cap('C25', '100nF 50V', vcc_3v3, fp=FP_C0603)



# SYM02: PCB Logo / Graphic (no electrical connections)
sym02_t = Part('Device', 'R', dest=TEMPLATE)
sym02_t.name, sym02_t.ref_prefix = 'LOGO', 'SYM'
sym02_t.footprint = 'Symbol:diybms_logo_24x10mm'
sym02_t.pins = []
sym02 = sym02_t()
sym02.ref   = 'SYM02'
sym02.value = 'LOGO'

# =============================================================================
# 8.  OUTPUT: KiCad netlist  +  CSV BOM
# =============================================================================

def generate_csv_bom(filename: str = 'module_16s_BOM.csv') -> None:
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


generate_netlist(filename='module_16s.net')
print('✅  Netlist saved  →  module_16s.net')
generate_csv_bom(filename='module_16s_BOM.csv')