"""Data models and dataclasses for the video converter."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ConversionResult:
    """Result of an MP4 to HLS conversion operation."""
    success: bool
    output_path: Path
    playlist_file: Path  # master_h264.m3u8
    init_file: Path      # init.mp4 from first quality
    segment_files: List[Path]  # All segment files from all qualities
    error_message: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of HLS output validation."""
    valid: bool
    playlist_valid: bool
    segments_valid: bool
    ffmpeg_playable: bool
    error_message: Optional[str] = None


@dataclass
class StatsSummary:
    """Summary statistics for conversion operations."""
    total_source_gb: float
    total_output_gb: float
    successful_conversions: int
    failed_conversions: int
    skipped_folders: int
    skipped_no_mp4: int
    skipped_multiple_mp4: int
    compression_ratio: float
