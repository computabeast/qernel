"""
Test script for validating your algorithm implementation.

Run this script to test that your algorithm:
1. Compiles correctly
2. Can be instantiated
3. Returns a valid Cirq circuit
4. Handles parameters correctly

Usage:
    python test_algorithm.py
"""

import sys
import traceback
from pathlib import Path

try:
    # Import the algorithm
    from algorithm_template import algorithm
    
    print("✓ Algorithm imported successfully")
    
    # Test basic interface
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
        print(f"  - Number of qubits: {circuit.num_qubits()}")
        print(f"  - Number of operations: {len(circuit.all_operations())}")
    except Exception as e:
        print(f"✗ Circuit building failed: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    print("\n🎉 Algorithm validation successful!")
    print("Your algorithm is ready to be submitted to the quantum resource estimation system.")
    
except ImportError as e:
    print(f"✗ Failed to import algorithm: {e}")
    print("Make sure algorithm_template.py exists and is properly formatted.")
    sys.exit(1)
except Exception as e:
    print(f"✗ Algorithm validation failed: {e}")
    traceback.print_exc()
    sys.exit(1)
