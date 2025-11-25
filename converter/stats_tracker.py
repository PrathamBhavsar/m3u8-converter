"""Statistics tracking for conversion operations."""

import logging
import time
from typing import Optional

from converter.data_models import StatsSummary


class StatsTracker:
    """Tracks conversion statistics and generates summary reports."""
    
    def __init__(self):
        """Initialize StatsTracker with zero counters."""
        self._total_source_bytes = 0
        self._total_output_bytes = 0
        self._successful_conversions = 0
        self._failed_conversions = 0
        self._skipped_no_mp4 = 0
        self._skipped_multiple_mp4 = 0
        self._start_time: Optional[float] = None
        self._total_conversion_time = 0.0  # Total time spent on successful conversions
        self._current_video_start: Optional[float] = None
        logging.info("StatsTracker initialized")
    
    def start_timer(self):
        """Start the overall timer."""
        self._start_time = time.time()
    
    def start_video_timer(self):
        """Start timer for current video conversion."""
        self._current_video_start = time.time()
    
    def end_video_timer(self):
        """End timer for current video and add to total conversion time."""
        if self._current_video_start is not None:
            elapsed = time.time() - self._current_video_start
            self._total_conversion_time += elapsed
            self._current_video_start = None
            return elapsed
        return 0.0
    
    def add_source_size(self, size_bytes: int) -> None:
        """
        Accumulate source file sizes.
        
        Args:
            size_bytes: Size in bytes to add to source total
        """
        self._total_source_bytes += size_bytes
        logging.debug(f"Added {size_bytes} bytes to source size (total: {self._total_source_bytes})")
    
    def add_output_size(self, size_bytes: int) -> None:
        """
        Accumulate output file sizes.
        
        Args:
            size_bytes: Size in bytes to add to output total
        """
        self._total_output_bytes += size_bytes
        logging.debug(f"Added {size_bytes} bytes to output size (total: {self._total_output_bytes})")
    
    def record_success(self) -> None:
        """Record a successful conversion."""
        self._successful_conversions += 1
        logging.debug(f"Recorded successful conversion (total: {self._successful_conversions})")
    
    def record_failure(self) -> None:
        """Record a failed conversion."""
        self._failed_conversions += 1
        logging.debug(f"Recorded failed conversion (total: {self._failed_conversions})")
    
    def record_skipped_no_mp4(self) -> None:
        """Record a folder skipped due to no MP4 files."""
        self._skipped_no_mp4 += 1
        logging.debug(f"Recorded skipped folder (no MP4): {self._skipped_no_mp4}")
    
    def record_skipped_multiple_mp4(self) -> None:
        """Record a folder skipped due to multiple MP4 files."""
        self._skipped_multiple_mp4 += 1
        logging.debug(f"Recorded skipped folder (multiple MP4): {self._skipped_multiple_mp4}")
    
    def get_summary(self) -> StatsSummary:
        """
        Return StatsSummary with GB conversions.
        
        Returns:
            StatsSummary dataclass with statistics in gigabytes
        """
        # Convert bytes to gigabytes
        bytes_per_gb = 1024 * 1024 * 1024
        total_source_gb = self._total_source_bytes / bytes_per_gb
        total_output_gb = self._total_output_bytes / bytes_per_gb
        
        # Calculate compression ratio (avoid division by zero)
        if self._total_source_bytes > 0:
            compression_ratio = self._total_output_bytes / self._total_source_bytes
        else:
            compression_ratio = 0.0
        
        return StatsSummary(
            total_source_gb=total_source_gb,
            total_output_gb=total_output_gb,
            successful_conversions=self._successful_conversions,
            failed_conversions=self._failed_conversions,
            skipped_folders=self._skipped_no_mp4 + self._skipped_multiple_mp4,
            skipped_no_mp4=self._skipped_no_mp4,
            skipped_multiple_mp4=self._skipped_multiple_mp4,
            compression_ratio=compression_ratio
        )
    
    def print_summary(self) -> None:
        """Display formatted statistics report."""
        summary = self.get_summary()
        
        # Calculate timing information
        total_runtime = 0.0
        if self._start_time is not None:
            total_runtime = time.time() - self._start_time
        
        avg_time_per_video = 0.0
        if self._successful_conversions > 0:
            avg_time_per_video = self._total_conversion_time / self._successful_conversions
        
        print("\n" + "=" * 60)
        print("CONVERSION STATISTICS SUMMARY")
        print("=" * 60)
        
        # Timing information
        if total_runtime > 0:
            print(f"Total Runtime:            {self._format_time(total_runtime)}")
            if self._successful_conversions > 0:
                print(f"Average Time per Video:   {self._format_time(avg_time_per_video)}")
        
        # Size information
        print(f"Total Source Size:        {summary.total_source_gb:.2f} GB")
        print(f"Total Output Size:        {summary.total_output_gb:.2f} GB")
        print(f"Compression Ratio:        {summary.compression_ratio:.2%}")
        
        # Conversion counts
        print(f"Successful Conversions:   {summary.successful_conversions}")
        print(f"Failed Conversions:       {summary.failed_conversions}")
        print(f"Skipped Folders:          {summary.skipped_folders}")
        if summary.skipped_no_mp4 > 0:
            print(f"  - No MP4 files:         {summary.skipped_no_mp4}")
        if summary.skipped_multiple_mp4 > 0:
            print(f"  - Multiple MP4 files:   {summary.skipped_multiple_mp4}")
        print(f"Total Processed:          {summary.successful_conversions + summary.failed_conversions + summary.skipped_folders}")
        print("=" * 60 + "\n")
        
        logging.info(
            f"Statistics: {summary.total_source_gb:.2f} GB source, "
            f"{summary.total_output_gb:.2f} GB output, "
            f"{summary.successful_conversions} successful, "
            f"{summary.failed_conversions} failed, "
            f"{summary.skipped_folders} skipped, "
            f"runtime: {self._format_time(total_runtime)}"
        )
    
    def _format_time(self, seconds: float) -> str:
        """
        Format seconds into human-readable time string.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string (e.g., "1h 23m 45s" or "5m 30s" or "45s")
        """
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}h {minutes}m {secs}s"
