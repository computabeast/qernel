#!/usr/bin/env python3
"""
Generic test script for quantum algorithm plugins.

This script discovers and tests all algorithms found in the repository.
"""

import sys
import traceback
from qernel import PluginLoader


def test_algorithm(algorithm_name: str, spec_file: str):
    """Test a single algorithm."""
    print(f"Testing {algorithm_name} algorithm...")
    
    try:
        # Load the algorithm using the plugin loader
        algorithm = PluginLoader.load_algorithm_from_spec(spec_file)
        
        print("✓ Algorithm loaded successfully")
        print(f"✓ Algorithm name: {algorithm.get_name()}")
        print(f"✓ Algorithm type: {algorithm.get_type()}")
        
        # Test parameter validation
        test_params = {
            'epsilon': 0.01,
            'payoff': 'max',
            'hardware_preset': 'GF-realistic'
        }
        
        try:
            algorithm.validate_params(test_params)
            print("✓ Parameter validation passed")
        except Exception as e:
            print(f"⚠ Parameter validation failed: {e}")
        
        # Test circuit building
        try:
            circuit = algorithm.build_circuit(test_params)
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


def test_spec_file(spec_file: str):
    """Test that a spec.yaml file is valid."""
    print(f"\nTesting specification file: {spec_file}")
    
    try:
        import yaml
        with open(spec_file, 'r') as f:
            yaml.safe_load(f)
        print("✓ spec.yaml is valid YAML")
        return True
    except Exception as e:
        print(f"✗ spec.yaml is invalid: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Running algorithm plugin tests...\n")
    
    # Discover all algorithms
    algorithms = PluginLoader.discover_algorithms()
    
    if not algorithms:
        print("❌ No algorithms found!")
        print("Make sure you have spec.yaml files in your repository.")
        sys.exit(1)
    
    print(f"Found {len(algorithms)} algorithm(s):")
    for name, spec_file in algorithms.items():
        print(f"  - {name} ({spec_file})")
    print()
    
    success = True
    
    # Test each algorithm
    for algorithm_name, spec_file in algorithms.items():
        success &= test_algorithm(algorithm_name, spec_file)
        success &= test_spec_file(spec_file)
        print()  # Add spacing between algorithms
    
    print("="*50)
    if success:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
