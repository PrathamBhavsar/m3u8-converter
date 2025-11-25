"""Progress bar for video conversion process."""

import sys
from typing import Optional


class ProgressBar:
    """Simple progress bar for tracking video conversion phases."""
    
    PHASES = [
        "Validating folder",
        "Detecting quality",
        "Separating audio",
        "Creating HLS format",
        "Creating VP9 format",
        "Creating thumbnails"
    ]
    
    def __init__(self, video_name: str, total_videos: int, current_video: int):
        """
        Initialize progress bar for a video.
        
        Args:
            video_name: Name of the video being processed
            total_videos: Total number of videos to process
            current_video: Current video number (1-indexed)
        """
        self.video_name = video_name
        self.total_videos = total_videos
        self.current_video = current_video
        self.current_phase = 0
        self.total_phases = len(self.PHASES)
    
    def start(self):
        """Start processing a video."""
        print(f"\n{'='*60}")
        print(f"Video {self.current_video}/{self.total_videos}: {self.video_name}")
        print(f"{'='*60}")
        self._render()
    
    def next_phase(self, phase_name: Optional[str] = None):
        """
        Move to the next phase.
        
        Args:
            phase_name: Optional custom phase name (uses default if not provided)
        """
        if phase_name:
            # Find the phase index
            try:
                self.current_phase = self.PHASES.index(phase_name) + 1
            except ValueError:
                self.current_phase += 1
        else:
            self.current_phase += 1
        
        self._render()
    
    def finish(self, success: bool = True):
        """
        Finish processing the video.
        
        Args:
            success: Whether the processing was successful
        """
        if success:
            print(f"\n[OK] Finished: {self.video_name}")
        else:
            print(f"\n[FAILED] {self.video_name}")
        print()
    
    def _render(self):
        """Render the progress bar."""
        if self.current_phase == 0:
            phase_text = "Starting..."
        elif self.current_phase > self.total_phases:
            phase_text = "Finishing..."
        else:
            phase_text = self.PHASES[self.current_phase - 1]
        
        # Calculate progress percentage
        progress = min(self.current_phase / self.total_phases, 1.0)
        bar_width = 40
        filled = int(bar_width * progress)
        bar = '#' * filled + '-' * (bar_width - filled)
        
        # Print progress bar
        percentage = int(progress * 100)
        print(f"\r[{bar}] {percentage:3d}% - {phase_text:<30}", end='', flush=True)
        
        # Move to next line after phase completes
        if self.current_phase > 0 and self.current_phase <= self.total_phases:
            print()
