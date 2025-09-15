import math

import gmpy2
from qiskit.circuit import QuantumCircuit


def int_to_bytes(integer: int, num_bytes: int) -> bytes:
    return integer.to_bytes(num_bytes)


def permutation_to_index(permutation, size_alphabet) -> int:
    """
    Returns the index of a given permutation assuming they are lexicographical ordered.
    Implements a slightly different variation of the Lehmer code.
    """
    possible_values = list(range(size_alphabet))
    index = gmpy2.mpz(0)

    for i, p in enumerate(permutation):
        if p == possible_values[0]:
            del possible_values[0]
            continue

        for j, val in enumerate(possible_values):
            if p == val:
                del possible_values[j]
                index += gmpy2.fac(size_alphabet - 1 - i) * j
                break

    return int(index)


def permutation_to_data(permutation, size_alphabet) -> bytes:
    num = permutation_to_index(permutation, size_alphabet)
    num_bytes = math.floor(math.log2(math.factorial(size_alphabet)) / 8)
    return int_to_bytes(num, num_bytes)


def recover_data(qc: QuantumCircuit, size_alphabet) -> bytes:
    if qc.layout is None:
        return b""

    permutation = qc.layout.initial_index_layout()
    return permutation_to_data(permutation, size_alphabet)
