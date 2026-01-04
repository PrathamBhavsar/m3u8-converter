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


# Standard quality profiles for H.264 (from quality_changes.md)
# Limited to: 360p, 720p only (max 2 qualities)
QUALITY_PROFILES_H264 = {
    "720p": QualityProfile("720p", 720, "2077k", "128k", 2077570, "h264"),
    "360p": QualityProfile("360p", 360, "800k", "128k", 800000, "h264"),
}

# Standard quality profiles for VP9 (from quality_changes.md)
# Limited to: 360p, 480p, 720p only (NO 1080p - max 3 qualities)
QUALITY_PROFILES_VP9 = {
    "720p": QualityProfile("720p", 720, "1291k", "128k", 1290999, "vp9"),
    "480p": QualityProfile("480p", 480, "768k", "128k", 768242, "vp9"),
    "360p": QualityProfile("360p", 360, "594k", "128k", 594105, "vp9"),
}

# Backward compatibility
QUALITY_PROFILES = QUALITY_PROFILES_H264

# Quality order from highest to lowest (max 5 total across both codecs)
# H.264: 720p, 360p (2 qualities)
# VP9: 720p, 480p, 360p (3 qualities)
QUALITY_ORDER_H264 = ["720p", "360p"]
QUALITY_ORDER_VP9 = ["720p", "480p", "360p"]
QUALITY_ORDER = ["720p", "480p", "360p"]  # Combined for source detection


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
            Quality string (e.g., "720p", "480p", "360p")
        """
        height = video_info.height
        
        # Use ranges to properly categorize video quality
        # Note: 1080p is NOT included as we don't encode to 1080p anymore
        if height >= 600:  # 720p and above
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
        
        Quality limits per quality_changes.md:
        - H.264: 360p, 720p only (max 2)
        - VP9: 360p, 480p, 720p only (max 3, NO 1080p)
        
        Args:
            source_quality: Source video quality (e.g., "720p")
            codec: Codec to use ("h264" or "vp9")
            
        Returns:
            List of QualityProfile objects to encode
        """
        profiles = []
        
        # Select the appropriate profile set and quality order
        if codec == "vp9":
            profile_set = QUALITY_PROFILES_VP9
            quality_order = QUALITY_ORDER_VP9
        else:
            profile_set = QUALITY_PROFILES_H264
            quality_order = QUALITY_ORDER_H264
        
        # Find the index of source quality in the appropriate order
        # If source quality not in list, find the closest match
        if source_quality in quality_order:
            source_index = quality_order.index(source_quality)
        else:
            # Map source quality to available qualities
            # e.g., 1080p -> 720p (highest available), 480p -> 480p for VP9, 360p for H264
            quality_height_map = {"720p": 720, "480p": 480, "360p": 360}
            source_height = quality_height_map.get(source_quality, 360)
            
            # Find first quality that is <= source height
            source_index = 0
            for i, q in enumerate(quality_order):
                q_height = quality_height_map.get(q, 360)
                if q_height <= source_height:
                    source_index = i
                    break
        
        # Include all qualities from source quality downwards
        for quality in quality_order[source_index:]:
            if quality in profile_set:
                profiles.append(profile_set[quality])
        
        logging.info(f"Encoding profiles for {source_quality} ({codec}): {[p.name for p in profiles]}")
        return profiles
