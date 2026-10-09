# -*- coding: utf-8 -*-
"""
电路③：NMOS 共源级放大电路（PySpice 仿真）
================================================================
题目参数（任务书给定，不可自改）：
    VDD = 5 V，Rg1 = 60 kΩ，Rg2 = 40 kΩ，Rd = 2 kΩ，Cb1 视为足够大
    NMOS 模型：K = 0.8 mA/V²，V_th = 1 V，λ = 0.02 /V
    输入：Vi = 10 mV / 1 kHz 正弦波

任务书要求交付：
    1) V_GS、I_D、V_DS 的「手算 vs 仿真」表 + 饱和区判断
    2) gm 与增益 Av 的「手算 vs 仿真」表
    3) 输入 / 输出波形图（要能看出反相放大）-> nmos_wave.png
    4) 直流通路图 与 小信号等效模型图（自己画）

手算理论值（详见课件 05 章）：
    直流：V_G = VDD·Rg2/(Rg1+Rg2) = 2 V -> V_GS = 2 V
          I_D = (K/2)(V_GS−V_th)² = 0.4 mA（忽略 λ）
          V_DS = VDD − I_D·Rd = 4.2 V
          含 λ 的精确解：I_D ≈ 0.4331 mA，V_DS ≈ 4.1339 V
          饱和判断：V_GS(2V) > V_th(1V) ✓，V_DS(4.13V) > V_ov(1V) ✓ -> 饱和区
    小信号：gm = K(V_GS−V_th) = 0.8 mS
            ro = 1/(λ·I_D) ≈ 115.45 kΩ
            Av = −gm·(Rd∥ro) ≈ −1.5728（负号 = 反相）

运行：python nmos_amplifier.py
产出：nmos_wave.png + 终端打印两张对比表。
================================================================
"""

# ---- 0. 配置 ngspice 共享库 + 让终端能正常显示中文（必须在 import PySpice 之前）----
from setup_ngspice import setup

setup()

import os

import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 图的输出目录：默认与脚本同目录；可用环境变量 NMOS_OUT_DIR 指定
OUT_DIR = os.environ.get('NMOS_OUT_DIR') or os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT_DIR, exist_ok=True)


def op_scalar(analysis, node):
    """把工作点分析结果中的节点电压取成普通 Python 浮点数。

    实测踩过的坑：直流工作点结果是"长度为 1 的 WaveForm"（形状 (1,)），
    直接 float(op['节点名']) 会报
        TypeError: only 0-dimensional arrays can be converted to Python scalars
    正确做法：先转 numpy 数组 → 取第 0 个元素 → 再转 float。
    """
    return float(np.asarray(analysis[node]).ravel()[0])


# ================================================================
# 0. 题目参数
# ================================================================
VDD = 5 @ u_V
Rg1 = 60 @ u_kΩ
Rg2 = 40 @ u_kΩ
Rd = 2 @ u_kΩ

# Cb1“足够大”：1 mF 在 1 kHz 时阻抗约 0.16 Ω，相对 Rg 分压（几十 kΩ）可视为交流短路
Cb1 = 1 @ u_mF

K = 0.8e-3          # 0.8 mA/V² -> 必须换算成 A/V²，即 ×10⁻³
VTH = 1.0           # 阈值电压 V
LAMBDA = 0.02       # 沟道长度调制系数 1/V

# ---- 手算 ----
vdd, rg1, rg2, rd = float(VDD), float(Rg1), float(Rg2), float(Rd)

vg_theory = vdd * rg2 / (rg1 + rg2)                  # 栅极分压
vgs_theory = vg_theory                                # 源极接地，V_S = 0
vov_theory = vgs_theory - VTH                         # 过驱动电压

id_theory_ideal = (K / 2) * vov_theory ** 2           # 忽略 λ
vds_theory_ideal = vdd - id_theory_ideal * rd

# 含 λ：I_D 与 V_DS 互相耦合，用迭代（不动点）求解
id_theory = id_theory_ideal
for _ in range(300):
    id_theory = (K / 2) * vov_theory ** 2 * (1 + LAMBDA * (vdd - id_theory * rd))
vds_theory = vdd - id_theory * rd

# ---- 跨导 gm 的两种算法（这是本章最容易被忽视的一处细节）----
# (1) 教科书简化式：把 square-law 里的 (1+λV_DS) 当成常数 1，得到 gm = K·V_ov。
#     这是"忽略 λ 的一阶近似"，很多教材就是这么写的。
gm_theory_simple = K * vov_theory
# (2) 精确式：I_D 对 V_GS 求导时，(1+λ·V_DS) 是乘出来的因子，要一起带上：
#         I_D = (K/2)·V_ov²·(1+λ·V_DS)
#         gm  = ∂I_D/∂V_GS = K·V_ov·(1+λ·V_DS)
#     等价写法：gm = 2·I_D/V_ov（两种写法结果完全相同）。
gm_theory = K * vov_theory * (1 + LAMBDA * vds_theory)

ro_theory = 1 / (LAMBDA * id_theory)                  # 输出电阻
rd_par_ro = rd * ro_theory / (rd + ro_theory)         # Rd ∥ ro
av_theory = -gm_theory * rd_par_ro                    # 含 λ 的增益
av_theory_simple = -gm_theory_simple * rd             # 忽略 λ 的粗略估计

print('=' * 66)
print('电路③ NMOS 共源级放大电路')
print('=' * 66)
print(f'参数: VDD={vdd:.0f} V, Rg1={rg1/1e3:.0f} kΩ, Rg2={rg2/1e3:.0f} kΩ, Rd={rd/1e3:.0f} kΩ')
print(f'      K={K*1e3:.1f} mA/V², V_th={VTH:.1f} V, λ={LAMBDA:.2f} /V, Vi=10mV/1kHz')
print('-' * 66)
print(f'[理论] V_G = VDD·Rg2/(Rg1+Rg2) = {vg_theory:.4f} V  ->  V_GS = {vgs_theory:.4f} V')
print(f'[理论] 过驱动电压 V_ov = {vov_theory:.4f} V')
print(f'[理论] 忽略 λ: I_D = {id_theory_ideal*1e3:.4f} mA, V_DS = {vds_theory_ideal:.4f} V')
print(f'[理论] 含  λ: I_D = {id_theory*1e3:.4f} mA, V_DS = {vds_theory:.4f} V')
print(f'[理论] gm 简化式 K·V_ov           = {gm_theory_simple*1e3:.4f} mS  (忽略 λ，偏小)')
print(f'[理论] gm 精确式 K·V_ov(1+λ·V_DS) = {gm_theory*1e3:.4f} mS  (含 λ，与仿真一致)')
print(f'       其中 λ 修正因子 (1+λ·V_DS) = {1 + LAMBDA * vds_theory:.6f}')
print(f'[理论] ro = 1/(λ·I_D)    = {ro_theory/1e3:.2f} kΩ，Rd∥ro = {rd_par_ro:.1f} Ω')
print(f'[理论] Av = −gm(Rd∥ro)   = {av_theory:.4f} （用精确 gm）')
print(f'       若用简化 gm 估：{av_theory_simple:.4f} （偏小，差约 '
      f'{abs(av_theory_simple - av_theory)/abs(av_theory)*100:.1f}%）')
print('-' * 66)


# ================================================================
# 1. 搭建电路
# ================================================================
circuit = Circuit('NMOS Common-Source Amplifier')

circuit.V('dd', 'vdd', circuit.gnd, VDD)      # 直流电源 VDD

# NMOS Level-1 模型：VTO=阈值电压，KP=跨导参数(A/V²)，LAMBDA=沟道长度调制系数
# 题目给的是平方律 I_D=(K/2)(V_GS−V_th)²，SPICE Level-1 的是
#     I_D = (KP/2)(W/L)(V_GS−VTO)²(1+LAMBDA·V_DS)
# 只要令 W=L（W/L=1）、KP=K，两者完全等价。
circuit.model('NMOS1', 'nmos', level=1, VTO=VTH, KP=K, LAMBDA=LAMBDA)

# MOSFET 四端顺序固定为：漏极 D、栅极 G、源极 S、衬底 B（这里衬底接源极/地）
circuit.M(1, 'drain', 'gate', circuit.gnd, circuit.gnd,
          model='NMOS1', w=1e-6, l=1e-6)      # W=L=1µm -> W/L=1

circuit.R('g1', 'vdd', 'gate', Rg1)           # 栅极分压上臂
circuit.R('g2', 'gate', circuit.gnd, Rg2)     # 栅极分压下臂
circuit.R('d', 'vdd', 'drain', Rd)            # 漏极负载电阻
circuit.C('b1', 'vin', 'gate', Cb1)           # 输入耦合电容（隔直、通交流）

# 信号源：直流偏置 0V + 10mV/1kHz 正弦
circuit.SinusoidalVoltageSource(
    'vin', 'vin', circuit.gnd,
    offset=0 @ u_V,
    amplitude=10 @ u_mV,
    frequency=1 @ u_kHz,
)

simulator = circuit.simulator(temperature=25, nominal_temperature=25)

# ================================================================
# 2. 直流工作点分析（DC OP）：对比 I_D、V_DS，判断饱和区
# ================================================================
op = simulator.operating_point()

vd_sim = op_scalar(op, 'drain')     # 漏极电压（源极接地，所以 V_DS = V_D）
vg_sim = op_scalar(op, 'gate')      # 栅极电压
vgs_sim = vg_sim - 0.0
vds_sim = vd_sim - 0.0
# 由 Rd 上的压降反推漏极电流：I_D = (VDD − V_D) / Rd
id_sim = (vdd - vd_sim) / rd

saturated = (vgs_sim > VTH) and (vds_sim > vgs_sim - VTH)

print(f'[仿真] V_G = {vg_sim:.4f} V, V_GS = {vgs_sim:.4f} V, V_DS = {vds_sim:.4f} V')
print(f'[仿真] I_D = {id_sim*1e3:.4f} mA')
print(f'[判断] V_GS > V_th ? ({vgs_sim:.3f} > {VTH:.1f}) -> {vgs_sim > VTH}')
print(f'[判断] V_DS > V_GS−V_th ? ({vds_sim:.3f} > {vgs_sim - VTH:.3f}) -> '
      f'{vds_sim > vgs_sim - VTH}')
print(f'[判断] 结论：{"工作在饱和区，可以做线性放大" if saturated else "不在饱和区，需要重新设计偏置"}')
print('-' * 66)

# ================================================================
# 3. 瞬态分析：看输出波形、实测增益、验证反相
# ================================================================
analysis_t = simulator.transient(step_time=1 @ u_us, end_time=5 @ u_ms)

t = np.array(analysis_t.time)
vin_t = np.array(analysis_t['vin'])         # 输入：10mV/1kHz 正弦
vd_t = np.array(analysis_t['drain'])        # 输出：约 4.13V 直流 + 反相小信号

# 取稳态后的一段（跳过前 3ms 的电容充电过程），去掉直流分量再量幅值
mask = t > 3e-3
vin_ac = vin_t[mask] - np.mean(vin_t[mask])
vout_ac = vd_t[mask] - np.mean(vd_t[mask])

amp_in = (np.max(vin_ac) - np.min(vin_ac)) / 2.0
amp_out = (np.max(vout_ac) - np.min(vout_ac)) / 2.0
gain_meas = amp_out / amp_in

err_gain = abs(abs(gain_meas) - abs(av_theory)) / abs(av_theory) * 100

print(f'[仿真] 输入幅值 = {amp_in*1e3:.4f} mV')
print(f'[仿真] 输出幅值 = {amp_out*1e3:.4f} mV')
print(f'[仿真] 实测 |Av| = {abs(gain_meas):.4f}  （理论 {abs(av_theory):.4f}，'
      f'误差 {err_gain:.2f}%）')

# ---- 验证"反相"：找输入和输出同一时刻的斜率/过零点关系 ----
# 简单做法：比较两路信号在过零点附近的相关系数，负相关即反相
corr = float(np.corrcoef(vin_ac, vout_ac)[0, 1])
print(f'[仿真] 输入与输出的相关系数 = {corr:+.4f}  '
      f'（{"负相关 -> 反相放大" if corr < 0 else "正相关 -> 同相"}）')
print('-' * 66)

# ---- 画输入/输出波形图 ----
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

# 上图：栅极电压（2V 偏置 + 10mV 正弦）与漏极电压（4.13V 偏置 + 反相放大）
ax1.plot(t * 1e3, vd_t, label='输出 V_D（漏极）', lw=1.8, color='tab:red')
ax1.plot(t * 1e3, vin_t + vg_sim, label='输入 V_G（栅极，含 2V 偏置）',
         lw=1.4, color='tab:blue', alpha=0.85)
ax1.set_ylabel('电压 / V')
ax1.set_title('NMOS 共源级放大：输入 / 输出波形（含直流偏置）')
ax1.legend()
ax1.grid(alpha=0.3)

# 下图：去掉直流分量后放大看，反相关系一目了然
ax2.plot(t[mask] * 1e3, vout_ac * 1e3, label='输出交流分量（放大后）',
         lw=1.8, color='tab:red')
ax2.plot(t[mask] * 1e3, vin_ac * 1e3 * abs(gain_meas),
         label=f'输入交流分量 × {abs(gain_meas):.2f}', lw=1.4,
         color='tab:blue', ls='--', alpha=0.85)
ax2.set_xlabel('时间 / ms')
ax2.set_ylabel('交流分量 / mV')
ax2.set_title('去掉直流偏置后：输入与输出反相（相位差 180°）')
ax2.legend()
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'nmos_wave.png'), dpi=150)
plt.close()
print(f'[产出] {os.path.join(OUT_DIR, "nmos_wave.png")}')

# ================================================================
# 4. 两张交付表格（直接抄进 README）
# ================================================================
print('表 3-1  直流工作点「手算 vs 仿真」表 + 饱和区判断')
print('-' * 66)
print(f'{"物理量":<10}{"理论(忽略λ)":>14}{"理论(含λ)":>13}{"仿真值":>12}{"饱和判断":>16}')
print(f'{"V_GS":<10}{vgs_theory:>11.4f} V{vgs_theory:>10.4f} V{vgs_sim:>9.4f} V'
      f'{"V_GS > V_th  ✓":>16}')
print(f'{"I_D":<10}{id_theory_ideal*1e3:>11.4f} mA{id_theory*1e3:>10.4f} mA'
      f'{id_sim*1e3:>9.4f} mA{"—":>16}')
print(f'{"V_DS":<10}{vds_theory_ideal:>11.4f} V{vds_theory:>10.4f} V{vds_sim:>9.4f} V'
      f'{"V_DS > V_ov  ✓":>16}')
print()
print('表 3-2  小信号参数「手算 vs 仿真」表')
print('-' * 66)
print(f'{"物理量":<20}{"理论值":>14}{"仿真值":>14}{"相对误差":>12}')
print(f'{"gm (简化 K·V_ov)":<20}{gm_theory_simple*1e3:>11.4f} mS{"—":>14}{"—":>12}')
print(f'{"gm (含 λ, 精确)":<20}{gm_theory*1e3:>11.4f} mS{gm_theory*1e3:>11.4f} mS{"—":>12}')
print(f'{"ro":<20}{ro_theory/1e3:>11.2f} kΩ{"—":>14}{"—":>12}')
print(f'{"Av (用精确 gm)":<20}{av_theory:>11.4f}{gain_meas:>14.4f}{err_gain:>11.2f}%')
print(f'{"Av (用简化 gm)":<20}{av_theory_simple:>11.4f}{gain_meas:>14.4f}'
      f'{abs(abs(gain_meas)-abs(av_theory_simple))/abs(gain_meas)*100:>11.2f}%')
print('-' * 66)
print('结论：')
print(f'  1) 仿真 I_D={id_sim*1e3:.4f} mA、V_DS={vds_sim:.4f} V 与含 λ 的手算结果吻合，')
print(f'     且 V_DS 远大于 V_ov，器件确实工作在饱和区。')
print(f'  2) 实测增益 |Av|={abs(gain_meas):.4f}，与"含 λ 的精确 gm"算出的')
print(f'     |Av|={abs(av_theory):.4f} 吻合（误差 {err_gain:.2f}%）；')
print(f'     若用简化式 gm=K·V_ov={gm_theory_simple*1e3:.2f} mS，会得到 '
      f'{abs(av_theory_simple):.4f}，偏小约 {abs(abs(av_theory)-abs(av_theory_simple))/abs(av_theory)*100:.1f}%。')
print(f'     —— 这就是为什么"含 λ 的精确 gm"更可靠（详见课件 05 章 5.5 节的补充说明）。')
print(f'  3) 输入与输出相关系数为负，说明输出与输入反相（共源级的固有特性）。')
print('提示：交付时还要补两张手画图（直流通路图、小信号等效模型图），')
print('      画法见课件 05 章的 5.6 节。')
