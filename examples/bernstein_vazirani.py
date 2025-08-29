# https://github.com/quantumlib/Cirq/blob/main/examples/bernstein_vazirani.py
import cirq
import random
from qernel import Algorithm, QernelClient, QernelConfig
from collections import Counter

def make_oracle(input_qubits, output_qubit, secret_factor_bits, secret_bias_bit):
    """Gates implementing the function f(a) = a·factors + bias (mod 2)."""

    if secret_bias_bit:
        yield cirq.X(output_qubit)

    for qubit, bit in zip(input_qubits, secret_factor_bits):
        if bit:  # pragma: no cover
            yield cirq.CNOT(qubit, output_qubit)

def make_bernstein_vazirani_circuit(input_qubits, output_qubit, oracle):
    """Solves for factors in f(a) = a·factors + bias (mod 2) with one query."""

    c = cirq.Circuit()

    # Initialize qubits.
    c.append([cirq.X(output_qubit), cirq.H(output_qubit), cirq.H.on_each(*input_qubits)])

    # Query oracle.
    c.append(oracle)

    # Measure in X basis.
    c.append([cirq.H.on_each(*input_qubits), cirq.measure(*input_qubits, key='result')])

    return c

def bitstring(bits):
    return ''.join(str(int(b)) for b in bits)


class BernsteinVaziraniAlgorithm(Algorithm):
    """Bernstein Vazirani quantum algorithm example."""
    
    def get_name(self) -> str:
        """Return the human-readable name of the algorithm."""
        return "Bernstein Vazirani"
    
    def get_type(self) -> str:
        """Return the algorithm type identifier."""
        return "primitive"
    
    def build_circuit(self, params: dict) -> cirq.Circuit:
        """
        Please estimate resources with metrics qubit_count, depth.
        Also simulate with shots=10 to obtain a measurement histogram.
        """
        qubit_count = 8
        circuit_sample_count = 3

        # Choose qubits to use.
        input_qubits = [cirq.GridQubit(i, 0) for i in range(qubit_count)]
        output_qubit = cirq.GridQubit(qubit_count, 0)

        # Pick coefficients for the oracle and create a circuit to query it.
        secret_bias_bit = random.randint(0, 1)
        secret_factor_bits = [random.randint(0, 1) for _ in range(qubit_count)]
        oracle = make_oracle(input_qubits, output_qubit, secret_factor_bits, secret_bias_bit)
        print(
            'Secret function:\nf(a) = '
            f"a·<{', '.join(str(e) for e in secret_factor_bits)}> + "
            f"{secret_bias_bit} (mod 2)"
        )

        # Embed the oracle into a special quantum circuit querying it exactly once.
        circuit = make_bernstein_vazirani_circuit(input_qubits, output_qubit, oracle)
        return circuit



def main() -> int:
    client = QernelClient(QernelConfig(api_url="http://127.0.0.1:8000", stream_timeout=120))
    _ = client.run_stream(algorithm_instance=BernsteinVaziraniAlgorithm(), params={}, visualize=True)

if __name__ == "__main__":
    main()
