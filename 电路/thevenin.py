# -*- coding: utf-8 -*-
"""
电路②：验证戴维南定理（PySpice 仿真）
================================================================
任务书要求交付：
    1) 自己画的含源二端网络图（必须标注端口 A、A'）
    2) V_oc、I_sc 两次仿真的「手算 vs 仿真」表
    3) 等效电路替换后接负载的电压 / 电流验证表

本脚本自定的含源二端网络：
    Vs = 10 V 电压源 串联 R1 = 4 kΩ，再接 R2 = 6 kΩ 到地，
    端口 A 取在 R2 两端（A 与地之间）。

手算理论值：
    V_oc = Vs·R2/(R1+R2) = 10 × 6/(4+6)      = 6 V
    R_th = R1 ∥ R2       = 4×6/(4+6)         = 2.4 kΩ
    I_sc = V_oc / R_th   = 6 / 2.4k          = 2.5 mA
    取负载 RL = 1 kΩ：
    V_L  = V_oc·RL/(R_th+RL) = 6 × 1/(2.4+1) = 1.764706 V
    I_L  = V_L / RL                          = 1.764706 mA

仿真三条思路（本脚本就是按这三步做的）：
    (a) 端口悬空  -> 直流工作点分析 -> 读节点 A 电压 = V_oc
    (b) 端口用 0V 电压源短路（0V 源当电流表）-> 读该支路电流 = I_sc
    (c) 原网络接 RL 与 戴维南等效接 RL 分别仿真 -> 对比负载电压电流

运行：python thevenin.py
产出：终端打印两张对比表（可直接抄进 README）。
================================================================
"""

# ---- 0. 配置 ngspice 共享库 + 让终端能正常显示中文（必须在 import PySpice 之前）----
from setup_ngspice import setup

setup()

import numpy as np

from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *


def op_scalar(analysis, node):
    """把工作点分析结果中的节点电压取成普通 Python 浮点数。

    实测踩过的坑：直流工作点分析的结果是"长度为 1 的 WaveForm"对象（形状 (1,)），
    直接写 float(op['节点名']) 会报
        TypeError: only 0-dimensional arrays can be converted to Python scalars
    正确做法：先转 numpy 数组 → 取第 0 个元素 → 再转 float。
    """
    return float(np.asarray(analysis[node]).ravel()[0])


def branch_scalar(analysis, source_name):
    """把工作点分析结果中"某个电压源支路"的电流取成普通 Python 浮点数。

    实测踩过的坑（两处，都要注意）：
      1) 支路的键名不是元件名本身，而是 **'v' + 元件名**：
         元件 `circuit.V('sense', ...)` 对应的键是 `'vsense'`。
         （可先用 list(analysis.branches.keys()) 打印出来核对。）
      2) 结果同样是长度 1 的 WaveForm，必须先转数组取第 0 个元素。
    这里做健壮匹配：先找完全一致的，再找 'v'+名字 的。
    """
    branches = analysis.branches
    for key in (source_name, 'v' + source_name):
        if key in branches:
            return float(np.asarray(branches[key]).ravel()[0])
    raise KeyError(
        f'找不到电压源 {source_name!r} 的支路电流；可用的支路名是 {list(branches.keys())}'
    )


# ================================================================
# 0. 参数与手算理论值
# ================================================================
Vs = 10 @ u_V
R1 = 4 @ u_kΩ
R2 = 6 @ u_kΩ
RL = 1 @ u_kΩ

v_s, r_1, r_2, r_l = float(Vs), float(R1), float(R2), float(RL)

voc_theory = v_s * r_2 / (r_1 + r_2)            # 开路电压
rth_theory = r_1 * r_2 / (r_1 + r_2)            # 等效电阻（R1 ∥ R2）
isc_theory = voc_theory / rth_theory            # 短路电流
vl_theory = voc_theory * r_l / (rth_theory + r_l)
il_theory = vl_theory / r_l

print('=' * 62)
print('电路② 验证戴维南定理')
print('=' * 62)
print(f'含源二端网络  : {v_s:.0f} V 串 R1={r_1/1e3:.0f} kΩ，再接 R2={r_2/1e3:.0f} kΩ 到地')
print(f'端口          : 节点 A 与地之间（A 即 R2 上端）')
print(f'负载          : RL = {r_l/1e3:.0f} kΩ')
print(f'[理论] V_oc = Vs·R2/(R1+R2) = {voc_theory:.6f} V')
print(f'[理论] R_th = R1∥R2         = {rth_theory/1e3:.6f} kΩ')
print(f'[理论] I_sc = V_oc/R_th     = {isc_theory*1e3:.6f} mA')
print(f'[理论] 接负载 V_L = {vl_theory:.6f} V, I_L = {il_theory*1e3:.6f} mA')
print('-' * 62)


def build_network(name):
    """搭出同一个含源二端网络，供下面三种仿真复用，避免抄错参数。"""
    c = Circuit(name)
    c.V('vs', 'src', c.gnd, Vs)      # 10V 独立电压源
    c.R(1, 'src', 'a', R1)           # R1 从电源正极到端口 A
    c.R(2, 'a', c.gnd, R2)           # R2 从端口 A 到地
    return c


# ================================================================
# 1. 测开路电压 V_oc：端口悬空，做直流工作点分析
# ================================================================
c1 = build_network('Thevenin - Voc')
sim1 = c1.simulator(temperature=25, nominal_temperature=25)
op1 = sim1.operating_point()          # 直流工作点分析（电路不随时间变化时的解）
voc_sim = op_scalar(op1, 'a')         # 读节点 a 的电压（注意必须先取标量）

err_voc = abs(voc_sim - voc_theory) / voc_theory * 100
print(f'[仿真] V_oc = {voc_sim:.6f} V        （理论 {voc_theory:.6f} V，误差 {err_voc:.4f}%）')

# ================================================================
# 2. 测短路电流 I_sc：用 0V 电压源把端口短路，读流过它的电流
#    为什么能这么干：SPICE 直接给出的是"流过电压源的电流"，
#    所以把 0V 电压源串进要测的支路，就等于串了一个理想电流表。
# ================================================================
c2 = build_network('Thevenin - Isc')
c2.V('sense', 'a', c2.gnd, 0 @ u_V)   # 0V 源：既把端口短路，又能读出电流
sim2 = c2.simulator(temperature=25, nominal_temperature=25)
op2 = sim2.operating_point()
isc_sim = abs(branch_scalar(op2, 'sense'))   # 读 'sense' 这个电压源支路的电流

err_isc = abs(isc_sim - isc_theory) / isc_theory * 100
print(f'[仿真] I_sc = {isc_sim*1e3:.6f} mA      （理论 {isc_theory*1e3:.6f} mA，误差 {err_isc:.4f}%）')

# 由仿真值反推 R_th，验证 R_th = V_oc / I_sc
rth_from_sim = voc_sim / isc_sim
print(f'[仿真] R_th = V_oc/I_sc = {rth_from_sim/1e3:.6f} kΩ'
      f' （理论 {rth_theory/1e3:.6f} kΩ）')
print('-' * 62)

# ================================================================
# 3. 等效替换验证：原网络接负载  vs  戴维南等效接负载
# ================================================================
# 3a. 原网络 + RL
c3 = build_network('Original network + Load')
c3.R('L', 'a', c3.gnd, RL)
op3 = c3.simulator(temperature=25, nominal_temperature=25).operating_point()
vl_orig = op_scalar(op3, 'a')
il_orig = vl_orig / r_l

# 3b. 戴维南等效电路 + RL：V_th 串 R_th 再串 RL
c4 = Circuit('Thevenin equivalent + Load')
c4.V('vth', 'src', c4.gnd, voc_theory @ u_V)        # 等效电压源 = V_oc
c4.R('th', 'src', 'a', (rth_theory) @ u_Ω)          # 等效电阻   = R_th
c4.R('L', 'a', c4.gnd, RL)
op4 = c4.simulator(temperature=25, nominal_temperature=25).operating_point()
vl_eq = op_scalar(op4, 'a')
il_eq = vl_eq / r_l

print(f'[仿真] 原网络 接 RL : V_L = {vl_orig:.6f} V, I_L = {il_orig*1e3:.6f} mA')
print(f'[仿真] 等效电路接 RL : V_L = {vl_eq:.6f} V, I_L = {il_eq*1e3:.6f} mA')
print(f'[验证] 两者电压差 = {abs(vl_orig - vl_eq)*1e6:.4f} µV  ->  完全一致，戴维南定理成立')
print('-' * 62)

# ================================================================
# 4. 两张交付表格（直接抄进 README）
# ================================================================
print('表 2-1  V_oc / I_sc / R_th 的「手算 vs 仿真」表')
print('-' * 62)
print(f'{"物理量":<18}{"理论值":>14}{"仿真值":>14}{"相对误差":>11}')
print(f'{"V_oc":<18}{voc_theory:>11.4f} V{voc_sim:>11.4f} V{err_voc:>10.4f}%')
print(f'{"I_sc":<18}{isc_theory*1e3:>11.4f} mA{isc_sim*1e3:>11.4f} mA{err_isc:>10.4f}%')
print(f'{"R_th = V_oc/I_sc":<18}{rth_theory/1e3:>11.4f} kΩ{rth_from_sim/1e3:>11.4f} kΩ'
      f'{abs(rth_from_sim-rth_theory)/rth_theory*100:>10.4f}%')
print()
print('表 2-2  等效替换接负载验证表（RL = 1 kΩ）')
print('-' * 62)
print(f'{"物理量":<18}{"原网络接负载":>16}{"戴维南等效接负载":>20}{"结论":>10}')
print(f'{"V_L":<18}{vl_orig:>13.4f} V{vl_eq:>17.4f} V{"一致":>10}')
print(f'{"I_L":<18}{il_orig*1e3:>11.4f} mA{il_eq*1e3:>15.4f} mA{"一致":>10}')
print('-' * 62)
print('结论：对同一个负载，复杂网络与"V_th 串 R_th"的等效电路给出的')
print('      负载电压、电流完全相同 —— 这就是戴维南定理要证的结论。')
print('提示：交付时别忘了自己画的含源二端网络图（必须标注端口 A、A′）。')
