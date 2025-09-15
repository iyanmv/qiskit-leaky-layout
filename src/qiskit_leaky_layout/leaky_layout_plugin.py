import builtins
import math

import gmpy2
from qiskit.transpiler import PassManager
from qiskit.transpiler.basepasses import AnalysisPass
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.layout import Layout
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers import common
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin
from qiskit.transpiler.target import Target


def index_to_permutation(index_permutation, size_alphabet):
    """
    Returns the (lexicographically ordered) i-th permutation for a set of size_alphabet elements
    """
    assert index_permutation < gmpy2.fac(size_alphabet)

    factorials = [1]
    permutation = []

    # Precompute factorials
    for k in range(1, size_alphabet):
        factorials.append(int(gmpy2.fac(k)))

    # Compute permutation
    for k in range(size_alphabet):
        permutation.append(index_permutation // factorials[size_alphabet - 1 - k])
        index_permutation %= factorials[size_alphabet - 1 - k]

    # Readjust permutation
    for k in range(size_alphabet - 1, 0, -1):
        for j in range(k - 1, -1, -1):
            if permutation[j] <= permutation[k]:
                permutation[k] += 1

    return permutation


def compute_permutation(data, number_qubits):
    index = int.from_bytes(data)
    return index_to_permutation(index, number_qubits)


class LeakyLayout(AnalysisPass):
    def __init__(self, coupling_map):
        super().__init__()

        if isinstance(coupling_map, Target):
            self.target = coupling_map
            self.coupling_map = self.target.build_coupling_map()
        else:
            self.target = None
            self.coupling_map = coupling_map

    def run(self, dag):
        try:
            data = builtins.data
        except AttributeError:
            data = b"My secret data encoded in the transpiled circuit layout."

        n_bits = len(data) * 8
        req_qubits = 0
        while math.floor(math.log2(math.factorial(req_qubits))) < n_bits:
            req_qubits += 1

        if self.target is not None:
            if dag.num_qubits() > self.target.num_qubits:
                raise TranspilerError("Number of qubits greater than device.")
            if self.target.num_qubits() < req_qubits:
                # Fallback to trivial layout
                self.property_set["layout"] = Layout.generate_trivial_layout(*(dag.qubits + list(dag.qregs.values())))
                return

        elif dag.num_qubits() > self.coupling_map.size():
            raise TranspilerError("Number of qubits greater than device.")

        elif self.coupling_map.size() < req_qubits:
            # Fallback to trivial layout
            self.property_set["layout"] = Layout.generate_trivial_layout(*(dag.qubits + list(dag.qregs.values())))
            return

        permutation = compute_permutation(data, max(dag.num_qubits(), req_qubits))
        self.property_set["layout"] = Layout.from_intlist(permutation, *(list(dag.qregs.values())))


class LeakyLayoutPlugin(PassManagerStagePlugin):
    def pass_manager(
        self,
        pass_manager_config: PassManagerConfig,
        optimization_level: int | None = None,
    ) -> PassManager:
        layout_pm = PassManager([LeakyLayout(coupling_map=pass_manager_config.coupling_map)])
        layout_pm += common.generate_embed_passmanager(pass_manager_config.coupling_map)
        return layout_pm
