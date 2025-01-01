import secrets
import unittest
from pathlib import Path


class TestEntryPoint(unittest.TestCase):
    def test_plugin_available(self):
        from qiskit.transpiler.preset_passmanagers.plugin import list_stage_plugins

        scheduling_plugins = list_stage_plugins("layout")
        self.assertTrue("leaky_layout" in scheduling_plugins)


class TestExample(unittest.TestCase):
    def test_example_readme(self):
        from qiskit.circuit import QuantumCircuit
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit.transpiler.preset_passmanagers.plugin import list_stage_plugins
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane

        from qiskit_leaky_layout.decoder import recover_data

        backend = FakeBrisbane()

        pm = generate_preset_pass_manager(
            optimization_level=3, backend=backend, layout_method="leaky_layout"
        )

        qc = QuantumCircuit(backend.num_qubits)
        qc.h(0)
        qc.cx(0, range(1, 3))

        isa_qc = pm.run(qc)

        recovered_default_message = recover_data(isa_qc, size_alphabet=127)[-56:]
        self.assertEqual(
            recovered_default_message,
            b"My secret data encoded in the transpiled circuit layout.",
        )

    def test_example_readme_builtins(self):
        import builtins

        from qiskit.circuit import QuantumCircuit
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit.transpiler.preset_passmanagers.plugin import list_stage_plugins
        from qiskit_ibm_runtime.fake_provider import FakeBrisbane

        from qiskit_leaky_layout.decoder import recover_data

        backend = FakeBrisbane()

        pm = generate_preset_pass_manager(
            optimization_level=3, backend=backend, layout_method="leaky_layout"
        )

        qc = QuantumCircuit(backend.num_qubits)
        qc.h(0)
        qc.cx(0, range(1, 3))

        builtins.data = b"\x12Y\xfd$^%g\xcbf\x1b"

        isa_qc = pm.run(qc)

        recovered_custom_message = recover_data(isa_qc, size_alphabet=127)[-10:]
        self.assertEqual(recovered_custom_message, b"\x12Y\xfd$^%g\xcbf\x1b")

        del builtins.data
