import cirq
from qernel import Algorithm, QernelClient
from qernel.core.client import QernelAPIError, AlgorithmTranscript
from qernel.vis.visualizer import AlgorithmVisualizer

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
        Build the Hello World quantum circuit.
        
        Args:
            params: Dictionary containing algorithm parameters
        
        Returns:
            A Cirq Circuit object
        """
        # Create a simple 3-qubit circuit
        q = cirq.LineQubit.range(3)
        
        circuit = cirq.Circuit(
            cirq.H(q[0]),           # Hadamard on first qubit
            cirq.CCX(q[0], q[1], q[2]),  # Toffoli gate
            cirq.T(q[2]) ** -1,     # T dagger on third qubit
        )
        
        return circuit

algorithm = HelloWorldAlgorithm()
client = QernelClient()

# Optional visualizer
viz = AlgorithmVisualizer(algorithm_name=algorithm.get_name())

try:
    transcript: AlgorithmTranscript = client.run_stream_with_handler(
        algorithm_instance=algorithm,
        params={},           # optional params
        visualizer=viz       # or None for terminal-only
    )
    # Access aggregated payloads
    print("Class:", transcript.class_name)
    print("Name:", transcript.methods.get_name_result)
    print("Type:", transcript.methods.get_type_result)
    print("Circuit:\n", transcript.methods.build_circuit_summary)
    # Full JSON-serializable transcript (for future persistence)
    json_payload = transcript.to_jsonable()
except QernelAPIError as e:
    # Inspect partial transcript on failure
    print("Stream error:", e.message)
    if e.transcript:
        print("Partial transcript:", e.transcript)
    raise