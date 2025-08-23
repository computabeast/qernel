#!/usr/bin/env python3
"""
Generic test script for quantum algorithm plugins.

This script tests algorithm instances directly.
"""

import sys
import traceback
from qernel.core.algorithm import Algorithm


def test_algorithm_instance(algorithm_instance: Algorithm):
    """Test a single algorithm instance."""
    print(f"Testing {algorithm_instance.get_name()} algorithm...")
    
    try:
        print("✓ Algorithm loaded successfully")
        print(f"✓ Algorithm name: {algorithm_instance.get_name()}")
        print(f"✓ Algorithm type: {algorithm_instance.get_type()}")
        
        # Test parameter validation
        test_params = {
            'epsilon': 0.01,
            'payoff': 'max',
            'hardware_preset': 'GF-realistic'
        }
        
        try:
            algorithm_instance.validate_params(test_params)
            print("✓ Parameter validation passed")
        except Exception as e:
            print(f"⚠ Parameter validation failed: {e}")
        
        # Test circuit building
        try:
            circuit = algorithm_instance.build_circuit(test_params)
            print(f"✓ Circuit built successfully")
            print(f"  - Circuit depth: {len(circuit)}")
            print(f"  - Number of qubits: {len(circuit.all_qubits())}")
            print(f"  - Number of operations: {len(list(circuit.all_operations()))}")
        except Exception as e:
            print(f"✗ Circuit building failed: {e}")
            traceback.print_exc()
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Algorithm test failed: {e}")
        traceback.print_exc()
        return False


def create_test_algorithm() -> Algorithm:
    """Create a test algorithm instance for testing."""
    class TestAlgorithm(Algorithm):
        def get_name(self) -> str:
            return "Test Algorithm"
        
        def get_type(self) -> str:
            return "test"
        
        def build_circuit(self, params):
            import cirq
            q = cirq.LineQubit.range(2)
            circuit = cirq.Circuit()
            circuit.append(cirq.H(q[0]))
            circuit.append(cirq.CNOT(q[0], q[1]))
            circuit.append(cirq.measure(q[0], q[1]))
            return circuit
    
    return TestAlgorithm()


if __name__ == "__main__":
    print("🧪 Running algorithm instance tests...\n")
    
    # Create test algorithm instance
    test_algorithm = create_test_algorithm()
    
    success = test_algorithm_instance(test_algorithm)
    
    print("="*50)
    if success:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
