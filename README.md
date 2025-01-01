# qiskit-layout-attack

[![Build & Test Python Wheel Package](https://github.com/cryptohslu/qiskit-leaky-layout/actions/workflows/build.yml/badge.svg)](https://github.com/cryptohslu/qiskit-leaky-layout/actions/workflows/build.yml)

A transpilation layout plugin that can be used with Qiskit to leak information from the computer running the
transpilation step to the cloud receiving the quantum computing jobs.

Current implementation, by default, tries to encode [the HSLU logo](https://www.hslu.ch/en/) into the transpiled circuit.
Custom data will be used if available in `builtins.data` (see [the example](#Example) below). If data is too large to
encode into the given circuit, the layout plugin fallbacks to the
[`TrivialLayout`](https://docs.quantum.ibm.com/api/qiskit/qiskit.transpiler.passes.TrivialLayout), which maps  virtual
qubits to physical qubits in the trivial way (i.e., $0\rightarrow0$, $1\rightarrow1$, etc.).

The plugin [is implemented](src/qiskit_leaky_layout/leaky_layout_plugin.py#L151) as a subclass of
[`PassManagerStagePlugin`](https://docs.quantum.ibm.com/api/qiskit/qiskit.transpiler.preset_passmanagers.plugin.PassManagerStagePlugin),
which uses a custom pass called [`LeakyLayout`](src/qiskit_leaky_layout/leaky_layout_plugin.py#L83). This pass is
implemented as a subclass of [`AnalysisPass`](https://docs.quantum.ibm.com/api/qiskit/qiskit.transpiler.AnalysisPass),
since no changes to the quantum circuit are done.

Leaked data can be recovered with the `recover_data()` function implemented in the
[decoder module](src/qiskit_leaky_layout/decoder.py). See [the example](#Example) below.

## Installation

```shell
git clone git@github.com:cryptohslu/qiskit-leaky-layout.git
cd qiskit-leaky-layout
pip install .
```

## Example

```python
import builtins
from qiskit.circuit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.transpiler.preset_passmanagers.plugin import list_stage_plugins
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit_leaky_layout.decoder import recover_data

# Check that layout plugin was installed successfully
assert "leaky_layout" in list_stage_plugins("layout")

# Fake 127-qubit backend used as target for the transpilation
backend = FakeBrisbane()

# Pass manager for the transpilation with our custom layout plugin
pm = generate_preset_pass_manager(
    optimization_level=3, backend=backend, layout_method="leaky_layout"
)

# 3-qubit GHZ circuit
qc = QuantumCircuit(backend.num_qubits)
qc.h(0)
qc.cx(0, range(1, 3))

# Uncomment to leak this bytes instead of the default message
# builtins.data = b"\x12Y\xfd$^%g\xcbf\x1b"

# Transpiled circuit
isa_qc = pm.run(qc)

# Recover data as raw bytes
recovered_default_message = recover_data(isa_qc, size_alphabet=127)[-56:]
assert (recovered_default_message == b"My secret data encoded in the transpiled circuit layout.")

# recovered_custom_message = recover_data(isa_qc, size_alphabet=127)[-10:]
# assert recovered_custom_message == b"\x12Y\xfd$^%g\xcbf\x1b"
```
