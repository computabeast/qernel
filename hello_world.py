"""
Hello World Algorithm Example

This demonstrates how to create a simple quantum algorithm plugin for Qernel.
Users can use this as a template for their own algorithms.
"""

import cirq
from qernel import Algorithm, QernelClient


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


if __name__ == "__main__":
    # Create an instance of the algorithm
    algorithm = HelloWorldAlgorithm()
    
    # Create a client and run the algorithm
    client = QernelClient()
    
    try:
        # Test the connection first
        connection_test = client.test_connection()
        print(f"Connection test: {connection_test}")

        # Run the algorithm
        result = client.run_algorithm(algorithm)
        print(f"Algorithm result: {result}")
        
    except Exception as e:
        print(f"Error running algorithm: {e}")
