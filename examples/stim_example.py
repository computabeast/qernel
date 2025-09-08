import stim
from qernel import Algorithm, QernelClient, QernelConfig

class StimErrorCorrection(Algorithm):
    """Quantum error correction code using Stim string format."""

    def get_name(self) -> str:
        """Return the human-readable name of the algorithm."""
        return "Simple stim error correction"

    def get_type(self) -> str:
        """Return the algorithm type identifier."""
        return "error_correction"

    def build_circuit(self, params: dict) -> stim.Circuit:
        """
        Build a simple quantum error correction circuit using Stim string format.

        This demonstrates Stim's strengths in error correction simulations.
        We implement a basic repetition code for error correction.
        """
        error_rate = params.get("error_rate", 0.01)

        # Create circuit string with dynamic error rate
        circuit_str = f"""
        # 3-qubit repetition code for error correction
        # Data qubits: 0, 1, 2
        # Syndrome qubits: 3, 4

        # Initialize data qubits to |+++⟩ state
        H 0
        H 1
        H 2

        # Encode the logical qubit using CNOT gates
        CNOT 0 1
        CNOT 0 2

        # Add bit flip noise for demonstration
        X_ERROR({error_rate}) 0
        X_ERROR({error_rate}) 1
        X_ERROR({error_rate}) 2

        # Syndrome extraction (parity checks)
        CNOT 0 3
        CNOT 2 3    # Check qubits 0 and 2
        CNOT 1 4
        CNOT 2 4    # Check qubits 1 and 2

        # Measure syndrome qubits
        M 3 4

        # Measure data qubits
        M 0 1 2
        """

        return stim.Circuit(circuit_str)


def main() -> int:
    # Configure client
    # api_url="http://127.0.0.1:8000"
    client = QernelClient(QernelConfig(api_url="http://127.0.0.1:8080"))
    _ = client.run_stream(
        algorithm_instance=StimErrorCorrection(), params={}, visualize=False
    )


if __name__ == "__main__":
    main()
