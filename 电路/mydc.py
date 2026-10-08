import numpy as np
import PySpice.Logging.Logging as Logging
logger = Logging.setup_logging()
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *
circuit = Circuit('Voltage Divider')
circuit.V('input', 'into', circuit.gnd, 5 @ u_V)
circuit.R(1, 'into', 'out', 1 @ u_kΩ)
circuit.R(2, 'out', circuit.gnd, 2 @ u_kΩ)
simulator = circuit.simulator(temperature=25, nominal_temperature=25)
analysis = simulator.operating_point()
v_out = float(np.asarray(analysis['out']).ravel()[0])
print(f'V_out = {v_out:.4f} V   （手算 3.3333 V）')