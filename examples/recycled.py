import cirq
from qernel import Algorithm, QernelClient, QernelConfig


class RecycledHelloWorldAlgorithm(Algorithm):
    """Recycled Hello World quantum algorithm example."""

    def __init__(self, circuit: cirq.Circuit, name: str = "Reloaded Circuit"):
        self._circuit = circuit

    def get_name(self) -> str:
        """Return the human-readable name of the algorithm."""
        return "Recycled Hello World"

    def get_type(self) -> str:
        """Return the algorithm type identifier."""
        return "recycled_hello_world"

    def build_circuit(self, params: dict) -> cirq.Circuit:
        """
        Please estimate resources with metrics t_count, qubit_count, depth, op_counts.
        Then perform error mitigation using Mitiq ZNE on observable Z@q0 with shots=100,
        scale_factors=[1.0, 2.0, 3.0], extrapolator=richardson.
        Also simulate with shots=200 to obtain a measurement histogram.
        """
        return self._circuit


def main() -> int:
    # api_url="http://127.0.0.1:8000",
    client = QernelClient(
        QernelConfig(api_url="http://127.0.0.1:8080", stream_timeout=120)
    )

    job_id = "197"
    # Option 1: Load standard artifacts (trial_result, simulator_state)
    artifacts = client.load_artifacts_sequential(job_id)
    trial_result = artifacts["trial_result"]
    simulator_state = artifacts["simulator_state"]

    # Option 2: Load specific artifacts (if you need custom ones)
    # artifacts = client.load_artifacts_sequential(
    #     job_id, ["trial_result", "simulator_state", "custom_artifact"]
    # )

    # Use the artifacts
    circuit = simulator_state.get("circuit")
    if circuit:
        print(f"Circuit has {len(circuit)} operations")

    print(trial_result.histogram(key="m"))

    # Continue where you left off
    qubits = circuit.all_qubits()
    circuit = cirq.Circuit(circuit.moments[:-1])  # Remove the measurement moment
    circuit.append(cirq.CCX(list(qubits)[0], list(qubits)[1], list(qubits)[2]))

    _ = client.run_stream(
        algorithm_instance=RecycledHelloWorldAlgorithm(circuit),
        params={},
        visualize=False,
    )


if __name__ == "__main__":
    main()
