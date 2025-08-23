#!/usr/bin/env python3
"""
Test script to verify the visualization system works correctly.
"""

from qernel import QernelClient
from qernel.core.algorithm import Algorithm


class TestAlgorithm(Algorithm):
    """Test algorithm for visualization testing."""
    
    def get_name(self) -> str:
        return "Test Algorithm"
    
    def get_type(self) -> str:
        return "test"
    
    def build_circuit(self, params):
        # Return a simple mock circuit
        import cirq
        q = cirq.LineQubit.range(2)
        circuit = cirq.Circuit()
        circuit.append(cirq.H(q[0]))
        circuit.append(cirq.CNOT(q[0], q[1]))
        circuit.append(cirq.measure(q[0], q[1]))
        return circuit


class TestQernelClient(QernelClient):
    """Test client that returns realistic test data."""
    
    def _run_algorithm_with_streaming(self, algorithm_instance, visualizer):
        """Mock streaming algorithm execution for testing."""
        import time
        
        # Simulate real-time updates with delays
        visualizer.update_status("Processing algorithm instance...", "info")
        time.sleep(1)
        
        visualizer.update_status("Building quantum circuit...", "info")
        time.sleep(1)
        
        visualizer.update_status("Submitting to quantum backend...", "info")
        time.sleep(2)
        
        visualizer.update_status("Algorithm execution in progress...", "info")
        time.sleep(3)
        
        visualizer.update_status("Processing results...", "info")
        time.sleep(1)
        
        # Return realistic result structure (focusing on artifacts)
        return {
            'run_id': 'test-run-12345',
            'status': 'completed',
            'artifacts': {
                'circuit_diagram': 'https://api.example.com/artifacts/circuit.png',
                'results_summary': 'https://api.example.com/artifacts/results.json',
                'performance_metrics': 'https://api.example.com/artifacts/metrics.csv',
                'quantum_state': 'https://api.example.com/artifacts/state.vec'
            },
            'execution_time': '2.34s',
            'qubits_used': 3,
            'circuit_depth': 15,
            'backend': 'quantum_simulator_v2'
        }


def test_visualization():
    """Test the visualization system."""
    print("Testing visualization system...")
    
    client = TestQernelClient()
    test_algorithm = TestAlgorithm()
    
    try:
        result = client.run_algorithm_with_visualization(test_algorithm)
        print("✓ Visualization test completed successfully!")
        print(f"✓ Result keys: {list(result.keys())}")
        print(f"✓ Artifacts: {list(result.get('artifacts', {}).keys())}")
        return True
    except Exception as e:
        print(f"✗ Visualization test failed: {e}")
        return False


if __name__ == "__main__":
    test_visualization()
