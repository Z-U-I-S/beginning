# -*- coding: utf-8 -*-
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
OUT_DIR = os.environ.get('RC_OUT_DIR') or os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT_DIR, exist_ok=True)

def op_scalar(analysis, node):
    return float(np.asarray(analysis[node]).ravel()[0])
R_val = 10 @ u_kΩ                # 10 kΩ
C_val = 100 @ u_nF               # 100 nF
tau_theory = float(R_val) * float(C_val)          # 秒
fc_theory = 1.0 / (2.0 * np.pi * tau_theory)      # Hz
print('=' * 62)
print('电路① RC 低通滤波电路')
print('=' * 62)
print(f'元件参数      : R = {float(R_val)/1e3:.3f} kΩ, C = {float(C_val)/1e-9:.1f} nF')
print(f'[理论] τ  = R·C        = {tau_theory * 1e3:.4f} ms')
print(f'[理论] fc = 1/(2πRC)   = {fc_theory:.2f} Hz')
print(f'[理论] 5V 阶跃的 63.2% 点 = {0.632 * 5:.3f} V', end='')
print(f'  （t = τ 时）')
print('-' * 62)
circuit = Circuit('RC Low-Pass Filter')
circuit.PulseVoltageSource(
    'vin', 'in', circuit.gnd,
    initial_value=0 @ u_V,       # 低电平
    pulsed_value=5 @ u_V,        # 高电平
    pulse_width=10 @ u_ms,       # 高电平持续时间
    period=20 @ u_ms,            # 周期
    rise_time=1 @ u_us,          # 上升时间（设很小，近似理想方波）
    fall_time=1 @ u_us,
)

circuit.R(1, 'in', 'out', R_val)          # 串联电阻
circuit.C(1, 'out', circuit.gnd, C_val)   # 电容到地，输出取自电容两端 => 低通

simulator = circuit.simulator(temperature=25, nominal_temperature=25)

# step_time 取 10µs = τ/100，保证 63.2% 那个时刻能被采到
analysis_t = simulator.transient(step_time=10 @ u_us, end_time=40 @ u_ms)

time = np.array(analysis_t.time)      # 时间轴（秒）
vin = np.array(analysis_t['in'])      # 输入节点电压
vout = np.array(analysis_t['out'])    # 输出节点电压

# ---- 从波形读 τ ----
# 思路：找到输入刚刚跳高的位置（第一个 vin > 2.5V 的点），
#       再往后找输出第一次达到 0.632×5V 的时刻，两者之差就是 τ。
v_target = 0.632 * 5.0
idx_rise = int(np.argmax(vin > 2.5))
idx_tau_candidates = np.where((time > time[idx_rise]) & (vout >= v_target))[0]

if len(idx_tau_candidates):
    t_rise = float(time[idx_rise])
    t_tau = float(time[idx_tau_candidates[0]])
    tau_meas = t_tau - t_rise
    err_tau = abs(tau_meas - tau_theory) / tau_theory * 100
    print(f'[仿真] τ  ≈ {tau_meas * 1e3:.4f} ms   相对误差 {err_tau:.2f}%')
else:
    tau_meas = float('nan')
    print('[仿真] 没找到 63.2% 时刻，请检查 step_time 是否过大')

# ---- 画瞬态波形图 ----
plt.figure(figsize=(9, 4.8))
plt.plot(time * 1e3, vin, label='输入 Vin（0~5V 方波）', lw=1.3)
plt.plot(time * 1e3, vout, label='输出 Vout（电容两端）', lw=1.8)
plt.axhline(v_target, color='r', ls=':', lw=1, label=f'63.2% 终值 = {v_target:.3f} V')
plt.xlabel('时间 / ms')
plt.ylabel('电压 / V')
plt.title('RC 低通滤波：方波输入的瞬态响应')
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'rc_transient.png'), dpi=150)
plt.close()
print(f'[产出] {os.path.join(OUT_DIR, "rc_transient.png")}')

# ================================================================
# 3. 交流分析（AC 扫频）：画波特图，从 −3 dB 点读 fc
# ================================================================
circuit_ac = Circuit('RC Low-Pass Filter - AC')

# AC 分析要单独给激励：ac_magnitude=1V，这样输出幅值就直接等于增益
circuit_ac.SinusoidalVoltageSource(
    'vin', 'in', circuit_ac.gnd,
    amplitude=1 @ u_V, frequency=1 @ u_kHz,
    ac_magnitude=1 @ u_V,
)
circuit_ac.R(1, 'in', 'out', R_val)
circuit_ac.C(1, 'out', circuit_ac.gnd, C_val)

simulator_ac = circuit_ac.simulator(temperature=25, nominal_temperature=25)
analysis_ac = simulator_ac.ac(
    start_frequency=10 @ u_Hz,
    stop_frequency=1 @ u_MHz,
    number_of_points=100,        # 每个十倍频取 100 个点
    variation='dec',             # 按十倍频（decade）分布
)

freq = np.array(analysis_ac.frequency)
vout_ac = np.array(analysis_ac['out'])
gain_db = 20 * np.log10(np.absolute(vout_ac))       # 输入幅值=1，输出幅值即增益
phase_deg = np.angle(vout_ac, deg=True)

# ---- 从曲线读 fc：找最接近 −3 dB 的那个频点 ----
fc_idx = int(np.argmin(np.abs(gain_db - (-3.0))))
fc_meas = float(freq[fc_idx])
err_fc = abs(fc_meas - fc_theory) / fc_theory * 100
print(f'[仿真] fc ≈ {fc_meas:.2f} Hz  相对误差 {err_fc:.2f}%')
print(f'[仿真] 该点增益 = {gain_db[fc_idx]:.3f} dB（理论 −3.010 dB）')

# ---- 画波特图（上：幅频，下：相频，共用对数频率轴）----
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7.5), sharex=True)

ax1.semilogx(freq, gain_db, lw=1.8, color='tab:blue')
ax1.axhline(-3, color='r', ls='--', lw=1, label='−3 dB')
ax1.axvline(fc_meas, color='g', ls='--', lw=1, label=f'fc ≈ {fc_meas:.0f} Hz')
ax1.set_ylabel('增益 / dB')
ax1.set_title('RC 低通滤波：波特图（幅频特性）')
ax1.legend()
ax1.grid(alpha=0.3, which='both')

ax2.semilogx(freq, phase_deg, lw=1.8, color='tab:orange')
ax2.axvline(fc_meas, color='g', ls='--', lw=1)
ax2.axhline(-45, color='r', ls=':', lw=1, label='−45°（fc 处理论相位）')
ax2.set_xlabel('频率 / Hz')
ax2.set_ylabel('相位 / °')
ax2.set_title('相频特性')
ax2.legend()
ax2.grid(alpha=0.3, which='both')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'rc_bode.png'), dpi=150)
plt.close()
print(f'[产出] {os.path.join(OUT_DIR, "rc_bode.png")}')
print('-' * 62)
print('表 1  理论值 vs 仿真值')
print('-' * 62)
print(f'{"物理量":<14}{"理论值":>14}{"仿真值":>14}{"相对误差":>12}')
print(f'{"时间常数 τ":<14}{tau_theory*1e3:>12.3f} ms{tau_meas*1e3:>12.3f} ms{err_tau:>11.2f}%')
print(f'{"截止频率 fc":<14}{fc_theory:>12.2f} Hz{fc_meas:>12.2f} Hz{err_fc:>11.2f}%')
print('-' * 62)
print('结论：仿真值由 ngspice 解电路方程得到，与手算公式结果一致，')
