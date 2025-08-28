import cirq
from qernel import Algorithm, QernelClient, QernelConfig


class HelloWorldAlgorithm(Algorithm):
    """Hello World quantum algorithm example."""
    
    def get_name(self) -> str:
        """Return the human-readable name of the algorithm."""
        return "Hello World"
    
    def get_type(self) -> str:
        """Return the algorithm type identifier."""
        return "hello_world"
    
    def build_circuit(self, params: dict) -> cirq.Circuit:
        """
        Please estimate resources with metrics t_count, qubit_count, depth, op_counts.
        Then perform error mitigation using Mitiq ZNE on observable Z@q0 with shots=100,
        scale_factors=[1.0, 2.0, 3.0], extrapolator=richardson.
        Also simulate with shots=200 to obtain a measurement histogram.
        """
        # Create a simple 3-qubit circuit
        q = cirq.LineQubit.range(3)

        # Hadamard on first qubit
        # Toffoli gate
        # T dagger on third qubit
        circuit = cirq.Circuit(
            cirq.H(q[0]),           
            cirq.CCX(q[0], q[1], q[2]),
            cirq.T(q[2]) ** -1,     
        )
        
        return circuit


def main() -> int:
    client = QernelClient(QernelConfig(api_url="http://127.0.0.1:8000", stream_timeout=120))
    _ = client.run_stream(algorithm_instance=HelloWorldAlgorithm(), params={}, visualize=False)

if __name__ == "__main__":
    main()


