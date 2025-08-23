"""
Algorithm Visualizer for real-time quantum algorithm execution monitoring.
"""

import os
import tempfile
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import webview


@dataclass
class StatusUpdate:
    """Represents a status update with timestamp."""
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    level: str = "info"  # info, warning, error, success


class AlgorithmVisualizer:
    """
    Real-time visualizer for quantum algorithm execution.
    
    Provides a live window into the quantum programming process,
    showing status updates, progress, and final results.
    """
    
    def __init__(self, algorithm_file: str, spec_file: str):
        """
        Initialize the visualizer.
        
        Args:
            algorithm_file: Path to the algorithm file
            spec_file: Path to the specification file
        """
        self.algorithm_file = algorithm_file
        self.spec_file = spec_file
        self.algorithm_name = os.path.basename(algorithm_file).replace('.py', '')
        
        # Status tracking
        self.status_updates: List[StatusUpdate] = []
        self.current_status = "Initializing..."
        self.final_results: Optional[Dict[str, Any]] = None
        
        # File contents for code snippets
        self.algorithm_code: Optional[str] = None
        self.yaml_code: Optional[str] = None
        self._load_file_contents()
        
        # Webview components
        self.window: Optional[webview.Window] = None
        self.temp_file: Optional[str] = None
        self._window_closed = False
    
    def _load_file_contents(self) -> None:
        """Load the contents of algorithm and spec files for code snippets."""
        try:
            # Load algorithm file
            if os.path.exists(self.algorithm_file):
                with open(self.algorithm_file, 'r', encoding='utf-8') as f:
                    self.algorithm_code = f.read()
            
            # Load YAML file
            if os.path.exists(self.spec_file):
                with open(self.spec_file, 'r', encoding='utf-8') as f:
                    self.yaml_code = f.read()
        except Exception as e:
            print(f"Warning: Could not load file contents for code snippets: {e}")
    
    def start_and_run(self) -> None:
        """Start the visualization window and run webview on main thread."""
        # Create initial HTML
        html_content = self._generate_html()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            self.temp_file = f.name
        
        # Create window
        self.window = webview.create_window(
            title=f"Qernel - {self.algorithm_name}",
            url=f'file://{self.temp_file}',
            width=900,
            height=700,
            resizable=True,
            text_select=True
        )
        
        print("Opening visualization window...")
        
        # Start webview on main thread (this will block until window closes)
        try:
            webview.start(debug=False)
        except Exception as e:
            print(f"Webview error: {e}")
        finally:
            self._window_closed = True
            self.cleanup()
    
    def update_status(self, message: str, level: str = "info") -> None:
        """
        Update the current status and add to history.
        
        Args:
            message: Status message
            level: Message level (info, warning, error, success)
        """
        update = StatusUpdate(message, level=level)
        self.status_updates.append(update)
        self.current_status = message
        
        # Update both terminal and webview
        print(f"[{level.upper()}] {message}")
        
        # Update webview content
        self._update_webview()
    
    def update_with_results(self, results: Dict[str, Any]) -> None:
        """
        Update visualization with final algorithm results.
        
        Args:
            results: Final results from algorithm execution
        """
        self.final_results = results
        self.update_status("Algorithm execution completed successfully!", "success")
    
    def _update_webview(self) -> None:
        """Update the webview content."""
        if self.window is None or self.temp_file is None or self._window_closed:
            return
        
        try:
            html_content = self._generate_html()
            
            # Write updated content to temp file
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Reload the window content
            try:
                self.window.evaluate_js("location.reload();")
            except:
                pass  # Window might be closed or not ready
                
        except Exception as e:
            # Don't print errors as they can be frequent during updates
            pass
    
    def _generate_html(self) -> str:
        """Generate HTML content for the visualization."""
        return self._generate_combined_html()
    
    def _generate_combined_html(self) -> str:
        """Generate HTML with streaming status and results in one view."""
        from .html import HTMLBuilder
        
        # Convert StatusUpdate objects to dictionaries for the builder
        status_updates = []
        for update in self.status_updates:
            status_updates.append({
                'timestamp': update.timestamp,
                'level': update.level,
                'message': update.message
            })
        
        return HTMLBuilder.build_combined_view(
            algorithm_name=self.algorithm_name,
            current_status=self.current_status,
            status_updates=status_updates,
            final_results=self.final_results,
            algorithm_code=self.algorithm_code,
            yaml_code=self.yaml_code
        )
    

    

    
    def cleanup(self) -> None:
        """Clean up temporary files."""
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.unlink(self.temp_file)
            except:
                pass
