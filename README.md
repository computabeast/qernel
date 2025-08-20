# Qernel - Quantum Algorithm Plugin System

A simple system for creating quantum algorithm plugins that can be executed by the quantum resource estimation system.

## Quickstart: Creating Your First Algorithm

This guide shows you how to create a quantum algorithm plugin for Qernel.

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository and navigate to the project directory:
```bash
cd qernel
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

### Creating Your Algorithm

1. **Create your algorithm file** (e.g., `my_algorithm.py`):
```python
import cirq
from qernel import Algorithm

class MyAlgorithm(Algorithm):
    def get_name(self) -> str:
        return "my_algorithm"
    
    def get_type(self) -> str:
        return "my_algorithm"
    
    def build_circuit(self, params: dict) -> cirq.Circuit:
        # Your quantum circuit implementation here
        q = cirq.LineQubit.range(2)
        circuit = cirq.Circuit(
            cirq.H(q[0]),
            cirq.CNOT(q[0], q[1])
        )
        return circuit

# Create an instance for testing
algorithm = MyAlgorithm()
```

2. **Create your specification file** (`spec.yaml`):
```yaml
algorithm:
  name: "my_algorithm"
  type: "my_algorithm"
  epsilon: 0.01
  payoff: "max"
  hardware_preset: "GF-realistic"
```

**Important**: The algorithm file name must match the `name` field in your spec.yaml!

### Testing Your Algorithm

Run the test script to validate your algorithm:

```bash
python test_algorithm.py
```

This will:
- Automatically discover all algorithms in your repository
- Test algorithm import and instantiation
- Test circuit building
- Test parameter validation
- Validate YAML specification files

### Example: Hello World

The repository includes a `hello_world.py` example that demonstrates:
- A simple 3-qubit circuit with Hadamard, Toffoli, and T gates
- Proper algorithm structure
- Parameter handling

### How It Works

1. **Plugin Discovery**: The system automatically finds all `spec.yaml` files
2. **Dynamic Loading**: Algorithms are loaded based on the `name` field in spec.yaml
3. **Algorithm Class**: Extend the `Algorithm` base class
4. **Required Methods**:
   - `get_name()`: Human-readable name
   - `get_type()`: Algorithm type identifier
   - `build_circuit(params)`: Build your quantum circuit using Cirq

5. **Configuration**: Use `spec.yaml` for parameters like epsilon, payoff, and hardware presets
6. **CI/CD**: The GitHub Actions workflow automatically tests and submits all discovered algorithms

### Next Steps

- Explore the `hello_world.py` example
- Check out the `qernel/` package for advanced features
- Use the `QernelClient` for API interactions

### Dependencies

- **Cirq**: Google's quantum computing framework
- **PyYAML**: YAML configuration file parsing
- **Requests**: HTTP library for API interactions
- **typing-extensions**: Enhanced type hints support
