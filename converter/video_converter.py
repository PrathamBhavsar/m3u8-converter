"""Video conversion to HLS format with multiple quality levels."""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional

from converter.video_quality import VideoQualityDetector
from converter.hls_encoder import HLSEncoder
from converter.data_models import ConversionResult


class VideoConverter:
    """Converts MP4 files to HLS format using FFmpeg."""
    
    def __init__(self, segment_duration: int = 5):
        """
        Initialize VideoConverter with configurable segment duration.
        
        Args:
            segment_duration: Duration of each HLS segment in seconds (default: 5)
        """
        self.segment_duration = segment_duration
    
    def get_video_duration(self, video_path: Path) -> Optional[float]:
        """
        Get the duration of a video file in seconds using FFprobe.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Duration in seconds, or None if unable to determine
        """
        try:
            command = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path.absolute())
            ]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                return duration
            else:
                return None
                
        except Exception as e:
            logging.error(f"Error getting video duration: {e}")
            return None
    
    def generate_trailer(self, video_path: Path, output_folder: Path, duration: float = 4.0) -> bool:
        """
        Generate a highly compressed, muted 4-second trailer from the video.
        
        Args:
            video_path: Path to the source video file
            output_folder: Path to the folder where trailer should be saved (same level as video/)
            duration: Duration of the trailer in seconds (default: 4)
            
        Returns:
            True if trailer was generated successfully, False otherwise
        """
        try:
            video_duration = self.get_video_duration(video_path)
            if video_duration is None:
                logging.error("Failed to get video duration for trailer generation")
                return False
            
            # Start at 10% of the video to skip intros
            # Ensure we don't seek past the video duration
            start_time = min(video_duration * 0.10, max(0, video_duration - duration - 1))
            
            output_file = output_folder / "trailer.mp4"
            
            # FFmpeg command for highly compressed, muted trailer
            # Using low resolution (360p), low bitrate, and no audio
            # Place -ss after -i for more accurate seeking (slower but more reliable)
            command = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i", str(video_path.absolute()),
                "-ss", str(start_time),  # Seek after input for accuracy
                "-t", str(duration),  # Duration of clip
                "-an",  # No audio
                "-vf", "scale=-2:360",  # Scale to 360p height, maintain aspect ratio
                "-c:v", "libx264",  # H.264 codec
                "-preset", "medium",  # Balance between speed and compression
                "-crf", "35",  # High compression (higher = smaller file, lower quality)
                "-profile:v", "baseline",  # Maximum compatibility
                "-level", "3.0",
                "-movflags", "+faststart",  # Web optimization
                "-pix_fmt", "yuv420p",  # Ensure compatibility
                str(output_file.absolute())
            ]
            
            logging.info(f"Generating trailer: start={start_time:.2f}s, duration={duration}s")
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # Increased timeout for longer videos
            )
            
            if result.returncode != 0:
                logging.error(f"FFmpeg trailer generation failed: {result.stderr}")
                return False
            
            if not output_file.exists():
                logging.error("Trailer file was not created")
                return False
            
            # Verify the file has content
            if output_file.stat().st_size == 0:
                logging.error("Trailer file is empty")
                output_file.unlink()  # Remove empty file
                return False
            
            logging.info(f"Trailer generated successfully: {output_file.name}")
            return True
            
        except subprocess.TimeoutExpired:
            logging.error("Trailer generation timed out")
            return False
        except Exception as e:
            logging.error(f"Error generating trailer: {e}", exc_info=True)
            return False
    
    def extract_thumbnails(self, video_path: Path, output_folder: Path, percentages: List[int]) -> bool:
        """
        Extract thumbnails from video at specified percentage points.
        
        Args:
            video_path: Path to the source video file
            output_folder: Path to the folder where thumbnails should be saved (same level as video/)
            percentages: List of percentage values (e.g., [30, 50, 70])
            
        Returns:
            True if all thumbnails were extracted successfully, False otherwise
        """
        try:
            # Get video duration
            duration = self.get_video_duration(video_path)
            if duration is None:
                return False
            
            # Extract thumbnail at each percentage
            success_count = 0
            for idx, percentage in enumerate(percentages, 1):
                try:
                    # Calculate timestamp in seconds
                    timestamp = (percentage / 100.0) * duration
                    
                    # Output filename: thumbnail1.jpg, thumbnail2.jpg, thumbnail3.jpg
                    output_file = output_folder / f"thumbnail{idx}.jpg"
                    
                    # FFmpeg command to extract frame at specific timestamp
                    command = [
                        "ffmpeg",
                        "-y",  # Overwrite output files
                        "-ss", str(timestamp),  # Seek to timestamp
                        "-i", str(video_path.absolute()),
                        "-vframes", "1",  # Extract 1 frame
                        "-q:v", "2",  # High quality (2-5 is good, lower is better)
                        str(output_file.absolute())
                    ]
                    
                    result = subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0 and output_file.exists():
                        success_count += 1
                        
                except Exception as e:
                    logging.error(f"Error extracting thumbnail {idx}: {e}")
            
            return success_count == len(percentages)
                
        except Exception as e:
            logging.error(f"Error during thumbnail extraction: {e}", exc_info=True)
            return False
    
    def convert_to_hls(self, input_mp4: Path, output_dir: Path) -> ConversionResult:
        """
        Orchestrate conversion of MP4 to HLS format with multiple quality levels.
        
        Args:
            input_mp4: Path to the input MP4 file
            output_dir: Path to the output directory
            
        Returns:
            ConversionResult with success status and file paths
        """
        try:
            # Validate input file
            if not input_mp4.exists():
                error_msg = f"Input MP4 file does not exist"
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=output_dir / "video" / "master_h264.m3u8",
                    init_file=output_dir / "video" / "720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            if not input_mp4.is_file():
                error_msg = f"Input path is not a file"
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=output_dir / "video" / "master_h264.m3u8",
                    init_file=output_dir / "video" / "720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            video_dir = output_dir / "video"
            video_dir.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Detect video quality
            detector = VideoQualityDetector()
            video_info = detector.get_video_info(input_mp4)
            
            if video_info is None:
                error_msg = "Failed to detect video information"
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=video_dir / "master_h264.m3u8",
                    init_file=video_dir / "720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            source_quality = detector.determine_source_quality(video_info)
            encoding_profiles = detector.get_encoding_profiles(source_quality)
            
            if not encoding_profiles:
                error_msg = "No encoding profiles determined"
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=video_dir / "master_h264.m3u8",
                    init_file=video_dir / "720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            # Step 2: Encode audio separately (shared between H.264 and VP9)
            encoder = HLSEncoder(segment_duration=self.segment_duration)
            audio_success = encoder.encode_audio(input_mp4, video_dir, audio_bitrate="128k")
            
            # Step 3: Encode H.264 quality levels
            encoded_h264_profiles = []
            all_segment_files = []
            
            for profile in encoding_profiles:
                success = encoder.encode_quality(input_mp4, video_dir, profile)
                
                if success:
                    encoded_h264_profiles.append(profile)
                    quality_dir = video_dir / profile.folder_name
                    segments = list(quality_dir.glob("video*.m4s"))
                    all_segment_files.extend(segments)
            
            if not encoded_h264_profiles:
                error_msg = "Failed to encode any H.264 quality levels"
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=video_dir / "master_h264.m3u8",
                    init_file=video_dir / "h264_720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            # Step 4: Encode VP9 quality levels
            vp9_encoding_profiles = detector.get_encoding_profiles(source_quality, codec="vp9")
            encoded_vp9_profiles = []
            
            for profile in vp9_encoding_profiles:
                success = encoder.encode_quality(input_mp4, video_dir, profile)
                
                if success:
                    encoded_vp9_profiles.append(profile)
                    quality_dir = video_dir / profile.folder_name
                    segments = list(quality_dir.glob("video*.m4s"))
                    all_segment_files.extend(segments)
            
            # Add audio segments to the list if audio was encoded
            if audio_success:
                audio_dir = output_dir / "audio"
                audio_segments = list(audio_dir.glob("audio*.m4s"))
                all_segment_files.extend(audio_segments)
            
            # Step 5: Create H.264 master playlist
            h264_master_success = encoder.create_master_playlist(
                video_dir, encoded_h264_profiles, has_audio=audio_success, codec="h264"
            )
            
            if not h264_master_success:
                error_msg = "Failed to create H.264 master playlist"
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=video_dir / "master_h264.m3u8",
                    init_file=video_dir / encoded_h264_profiles[0].folder_name / "init.mp4",
                    segment_files=all_segment_files,
                    error_message=error_msg
                )
            
            # Step 6: Create VP9 master playlist if VP9 encoding succeeded
            if encoded_vp9_profiles:
                encoder.create_master_playlist(
                    video_dir, encoded_vp9_profiles, has_audio=audio_success, codec="vp9"
                )
            
            # Step 7: Create unified master playlist (playlist.m3u8) with all qualities
            encoder.create_unified_master_playlist(
                video_dir, encoded_h264_profiles, encoded_vp9_profiles, has_audio=audio_success
            )
            
            # Success!
            # Use the unified playlist as the main playlist
            master_playlist = video_dir / "playlist.m3u8"
            first_init = video_dir / encoded_h264_profiles[0].folder_name / "init.mp4"
            
            return ConversionResult(
                success=True,
                output_path=output_dir,
                playlist_file=master_playlist,
                init_file=first_init,
                segment_files=all_segment_files,
                error_message=None
            )
                
        except Exception as e:
            error_msg = f"Unexpected error during conversion: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return ConversionResult(
                success=False,
                output_path=output_dir,
                playlist_file=output_dir / "video" / "master_h264.m3u8",
                init_file=output_dir / "video" / "720p" / "init.mp4",
                segment_files=[],
                error_message=error_msg
            )
