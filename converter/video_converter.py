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
        logging.info(f"VideoConverter initialized with segment_duration={segment_duration}s")
    
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
                logging.debug(f"Video duration: {duration:.2f} seconds")
                return duration
            else:
                logging.error(f"Failed to get video duration: {result.stderr}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting video duration: {e}")
            return None
    
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
            logging.info(f"Extracting {len(percentages)} thumbnails from {video_path.name}")
            
            # Get video duration
            duration = self.get_video_duration(video_path)
            if duration is None:
                logging.error("Cannot extract thumbnails: unable to determine video duration")
                return False
            
            logging.info(f"Video duration: {duration:.2f} seconds")
            
            # Extract thumbnail at each percentage
            success_count = 0
            for idx, percentage in enumerate(percentages, 1):
                try:
                    # Calculate timestamp in seconds
                    timestamp = (percentage / 100.0) * duration
                    
                    # Output filename: thumbnail1.jpg, thumbnail2.jpg, thumbnail3.jpg
                    output_file = output_folder / f"thumbnail{idx}.jpg"
                    
                    logging.debug(f"Extracting thumbnail {idx} at {percentage}% ({timestamp:.2f}s)")
                    
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
                        file_size = output_file.stat().st_size
                        logging.info(f"Thumbnail {idx} extracted: {output_file.name} ({file_size} bytes)")
                        success_count += 1
                    else:
                        logging.error(f"Failed to extract thumbnail {idx}: {result.stderr}")
                        
                except Exception as e:
                    logging.error(f"Error extracting thumbnail {idx} at {percentage}%: {e}")
            
            if success_count == len(percentages):
                logging.info(f"Successfully extracted all {len(percentages)} thumbnails")
                return True
            else:
                logging.warning(f"Only extracted {success_count}/{len(percentages)} thumbnails")
                return False
                
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
            logging.info(f"Starting multi-quality HLS conversion: {input_mp4.name}")
            logging.debug(f"Input file: {input_mp4}")
            logging.debug(f"Output directory: {output_dir}")
            
            # Validate input file
            if not input_mp4.exists():
                error_msg = f"Input MP4 file does not exist: {input_mp4}"
                logging.error(error_msg)
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=output_dir / "video" / "master_h264.m3u8",
                    init_file=output_dir / "video" / "h264_720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            if not input_mp4.is_file():
                error_msg = f"Input path is not a file: {input_mp4}"
                logging.error(error_msg)
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=output_dir / "video" / "master_h264.m3u8",
                    init_file=output_dir / "video" / "h264_720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            # Log input file size
            try:
                file_size_mb = input_mp4.stat().st_size / (1024 * 1024)
                logging.info(f"Input file size: {file_size_mb:.2f} MB")
            except Exception as e:
                logging.warning(f"Could not determine input file size: {e}")
            
            video_dir = output_dir / "video"
            video_dir.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Detect video quality
            detector = VideoQualityDetector()
            video_info = detector.get_video_info(input_mp4)
            
            if video_info is None:
                error_msg = "Failed to detect video information"
                logging.error(error_msg)
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=video_dir / "master_h264.m3u8",
                    init_file=video_dir / "h264_720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            source_quality = detector.determine_source_quality(video_info)
            encoding_profiles = detector.get_encoding_profiles(source_quality)
            
            if not encoding_profiles:
                error_msg = f"No encoding profiles determined for {source_quality}"
                logging.error(error_msg)
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=video_dir / "master_h264.m3u8",
                    init_file=video_dir / "h264_720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            logging.info(f"Will encode {len(encoding_profiles)} quality levels: {[p.name for p in encoding_profiles]}")
            
            # Step 2: Encode audio separately
            encoder = HLSEncoder(segment_duration=self.segment_duration)
            logging.info("Encoding audio track...")
            audio_success = encoder.encode_audio(input_mp4, video_dir, audio_bitrate="128k")
            
            if not audio_success:
                logging.warning("Failed to encode audio, continuing with video-only")
            
            # Step 3: Encode each quality level (video only)
            encoded_profiles = []
            all_segment_files = []
            
            for profile in encoding_profiles:
                logging.info(f"Encoding {profile.name}...")
                success = encoder.encode_quality(input_mp4, video_dir, profile)
                
                if success:
                    encoded_profiles.append(profile)
                    # Collect segment files for this quality
                    quality_dir = video_dir / profile.folder_name
                    segments = list(quality_dir.glob("video*.m4s"))
                    all_segment_files.extend(segments)
                    logging.info(f"Successfully encoded {profile.name} with {len(segments)} segments")
                else:
                    logging.error(f"Failed to encode {profile.name}")
            
            if not encoded_profiles:
                error_msg = "Failed to encode any quality levels"
                logging.error(error_msg)
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=video_dir / "master_h264.m3u8",
                    init_file=video_dir / "h264_720p" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            # Add audio segments to the list if audio was encoded
            if audio_success:
                audio_dir = output_dir / "audio"
                audio_segments = list(audio_dir.glob("audio*.m4s"))
                all_segment_files.extend(audio_segments)
                logging.info(f"Added {len(audio_segments)} audio segments")
            
            # Step 4: Create master playlist
            logging.info("Creating master playlist...")
            master_success = encoder.create_master_playlist(video_dir, encoded_profiles, has_audio=audio_success)
            
            if not master_success:
                error_msg = "Failed to create master playlist"
                logging.error(error_msg)
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=video_dir / "master_h264.m3u8",
                    init_file=video_dir / encoded_profiles[0].folder_name / "init.mp4",
                    segment_files=all_segment_files,
                    error_message=error_msg
                )
            
            # Success!
            master_playlist = video_dir / "master_h264.m3u8"
            first_init = video_dir / encoded_profiles[0].folder_name / "init.mp4"
            
            logging.info(f"Multi-quality conversion successful: {len(encoded_profiles)} qualities, {len(all_segment_files)} total segments")
            
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
                init_file=output_dir / "video" / "h264_720p" / "init.mp4",
                segment_files=[],
                error_message=error_msg
            )
