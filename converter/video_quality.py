"""Video quality detection and configuration."""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class VideoInfo:
    """Information about a video file."""
    width: int
    height: int
    bitrate: int
    duration: float


@dataclass
class QualityProfile:
    """Quality profile for video encoding."""
    name: str  # e.g., "1080p", "720p"
    height: int
    video_bitrate: str  # e.g., "5000k"
    audio_bitrate: str  # e.g., "128k"
    bandwidth: int  # For master playlist
    codec: str = "h264"  # "h264" or "vp9"
    
    @property
    def folder_name(self) -> str:
        """Get the folder name for this quality."""
        return f"{self.codec}_{self.name}"


# Standard quality profiles for H.264 (from requirements.md)
QUALITY_PROFILES_H264 = {
    "720p": QualityProfile("720p", 720, "2077k", "128k", 2077570, "h264"),
    "360p": QualityProfile("360p", 360, "800k", "128k", 800000, "h264"),
}

# Standard quality profiles for VP9
QUALITY_PROFILES_VP9 = {
    "1080p": QualityProfile("1080p", 1080, "2905k", "128k", 2905000, "vp9"),
    "720p": QualityProfile("720p", 720, "1291k", "128k", 1290999, "vp9"),
    "480p": QualityProfile("480p", 480, "768k", "128k", 768242, "vp9"),
    "360p": QualityProfile("360p", 360, "594k", "128k", 594105, "vp9"),
}

# Backward compatibility
QUALITY_PROFILES = QUALITY_PROFILES_H264

# Quality order from highest to lowest
QUALITY_ORDER = ["1080p", "720p", "480p", "360p"]


class VideoQualityDetector:
    """Detects video quality and determines appropriate encoding profiles."""
    
    def __init__(self):
        """Initialize VideoQualityDetector."""
        logging.info("VideoQualityDetector initialized")
    
    def get_video_info(self, video_path: Path) -> Optional[VideoInfo]:
        """
        Extract video information using FFprobe.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            VideoInfo object or None if detection fails
        """
        try:
            logging.debug(f"Detecting video info for {video_path.name}")
            
            # Get video dimensions and bitrate from stream
            stream_command = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,bit_rate",
                "-of", "csv=p=0",
                str(video_path.absolute())
            ]
            
            stream_result = subprocess.run(
                stream_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            if stream_result.returncode != 0:
                logging.error(f"FFprobe stream query failed: {stream_result.stderr}")
                return None
            
            # Parse stream output: width,height,bitrate
            stream_parts = stream_result.stdout.strip().split(',')
            if len(stream_parts) < 2:
                logging.error(f"Unexpected FFprobe stream output: {stream_result.stdout}")
                return None
            
            width = int(stream_parts[0])
            height = int(stream_parts[1])
            bitrate = int(stream_parts[2]) if len(stream_parts) > 2 and stream_parts[2] and stream_parts[2] != 'N/A' else 0
            
            # Get duration from format
            format_command = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(video_path.absolute())
            ]
            
            format_result = subprocess.run(
                format_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            duration = 0.0
            if format_result.returncode == 0 and format_result.stdout.strip():
                try:
                    duration = float(format_result.stdout.strip())
                except ValueError:
                    logging.warning(f"Could not parse duration: {format_result.stdout}")
            
            video_info = VideoInfo(width, height, bitrate, duration)
            logging.info(f"Video info: {width}x{height}, bitrate={bitrate}, duration={duration:.2f}s")
            
            return video_info
            
        except Exception as e:
            logging.error(f"Error detecting video info: {e}", exc_info=True)
            return None
    
    def determine_source_quality(self, video_info: VideoInfo) -> str:
        """
        Determine the source video quality based on height.
        
        Args:
            video_info: VideoInfo object
            
        Returns:
            Quality string (e.g., "1080p", "720p")
        """
        height = video_info.height
        
        # Use ranges to properly categorize video quality
        if height >= 1000:  # 1080p and above
            quality = "1080p"
        elif height >= 600:  # 720p range
            quality = "720p"
        elif height >= 420:  # 480p range
            quality = "480p"
        else:  # 360p and below
            quality = "360p"
        
        logging.info(f"Source video quality determined: {quality} (height={height})")
        return quality
    
    def get_encoding_profiles(self, source_quality: str, codec: str = "h264") -> List[QualityProfile]:
        """
        Get list of quality profiles to encode based on source quality.
        Only encode qualities equal to or lower than source.
        
        Args:
            source_quality: Source video quality (e.g., "720p")
            codec: Codec to use ("h264" or "vp9")
            
        Returns:
            List of QualityProfile objects to encode
        """
        profiles = []
        
        # Select the appropriate profile set
        profile_set = QUALITY_PROFILES_VP9 if codec == "vp9" else QUALITY_PROFILES_H264
        
        # Find the index of source quality
        try:
            source_index = QUALITY_ORDER.index(source_quality)
        except ValueError:
            logging.error(f"Unknown source quality: {source_quality}")
            return profiles
        
        # Include all qualities from source quality downwards
        for quality in QUALITY_ORDER[source_index:]:
            if quality in profile_set:
                profiles.append(profile_set[quality])
        
        logging.info(f"Encoding profiles for {source_quality} ({codec}): {[p.name for p in profiles]}")
        return profiles
