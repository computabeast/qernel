### Creating Your Algorithm

1. **Create your algorithm file** (e.g., `my_algorithm.py`):
```python
import cirq
from qernel import Algorithm

class MyAlgorithm(Algorithm):
    def get_name(self) -> str:
        return "My Algorithm"
    
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

### Using Visualization

Qernel includes a real-time visualization system that provides a live window into quantum algorithm execution. To use it:

```python
from qernel import QernelClient

# Create a standard client
client = QernelClient("https://api.qernel.example.com")

# Run with real-time visualization
result = client.run_algorithm_with_visualization("my_algorithm.py", "spec.yaml")
```