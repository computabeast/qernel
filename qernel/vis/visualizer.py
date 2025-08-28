"""
Algorithm Visualizer for real-time quantum algorithm execution monitoring.
"""

import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
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
    
    def __init__(self, algorithm_name: str = "Algorithm"):
        """
        Initialize the visualizer.
        
        Args:
            algorithm_name: Name of the algorithm being visualized
        """
        self.algorithm_name = algorithm_name
        
        # Status tracking
        self.status_updates: List[StatusUpdate] = []
        self.current_status = "Initializing..."
        self.final_results: Optional[Dict[str, Any]] = None
        
        # Webview components
        self.window: Optional[webview.Window] = None
        self.temp_file: Optional[str] = None
        self._window_closed = False
    
    def start_and_run(self, on_start: Optional[Callable[[], None]] = None) -> None:
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
        
        # Opening the window should be silent to avoid duplicate console logs
        
        # Start webview on main thread (this will block until window closes)
        try:
            if on_start is not None:
                webview.start(func=on_start, debug=False)
            else:
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
            algorithm_code=None  # No longer loading from files
        )
    
    def cleanup(self) -> None:
        """Clean up temporary files."""
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.unlink(self.temp_file)
            except:
                pass
