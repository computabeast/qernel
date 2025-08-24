import threading
from qernel import QernelClient, Algorithm
from qernel.core.client import QernelAPIError
from qernel.vis.visualizer import AlgorithmVisualizer

# Use your existing Algorithm implementation (e.g., HelloWorldAlgorithm from hello_world.py)
class HelloWorldAlgorithm(Algorithm):
    def get_name(self) -> str: return "Hello World"
    def get_type(self) -> str: return "hello_world"
    def build_circuit(self, params: dict):
        import cirq
        q = cirq.LineQubit.range(3)
        return cirq.Circuit(
            cirq.H(q[0]), cirq.CCX(q[0], q[1], q[2]), cirq.T(q[2]) ** -1
        )

def main() -> None:
    algorithm = HelloWorldAlgorithm()
    client = QernelClient()
    viz = AlgorithmVisualizer(algorithm_name=algorithm.get_name())

    def _run_stream():
        try:
            # Streams events, updates terminal and viz live, returns transcript on success
            transcript = client.run_stream_with_handler(
                algorithm_instance=algorithm,
                params={},
                visualizer=viz,
            )
            print("\nFinished. Transcript summary:")
            print(transcript.to_jsonable())  # JSON-serializable
        except QernelAPIError as e:
            print("Streaming error:", e.message)
            if e.transcript:
                print("Partial transcript:", e.transcript)

    # Start the streaming in a background thread
    t = threading.Thread(target=_run_stream, daemon=True)
    t.start()

    # Open the pywebview window on the main thread (blocks until closed)
    viz.start_and_run()

    # Optionally wait a moment for the worker to finish cleanup
    t.join(timeout=1)

if __name__ == "__main__":
    main()