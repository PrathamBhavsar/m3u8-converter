"""HLS encoding with multiple quality levels."""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional

from converter.video_quality import QualityProfile


class HLSEncoder:
    """Encodes video to HLS format with multiple quality levels."""
    
    def __init__(self, segment_duration: int = 6):
        """
        Initialize HLSEncoder.
        
        Args:
            segment_duration: Duration of each HLS segment in seconds
        """
        self.segment_duration = segment_duration
        logging.info(f"HLSEncoder initialized with segment_duration={segment_duration}s")
    
    def encode_quality(
        self,
        input_video: Path,
        output_dir: Path,
        profile: QualityProfile
    ) -> bool:
        """
        Encode video to a specific quality level.
        
        Args:
            input_video: Path to source video file
            output_dir: Path to output directory (video/)
            profile: QualityProfile to encode
            
        Returns:
            True if encoding succeeded, False otherwise
        """
        try:
            # Create quality-specific folder
            quality_dir = output_dir / profile.folder_name
            quality_dir.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"Encoding {profile.name} quality to {quality_dir}")
            
            # Build FFmpeg command for HLS with fmp4
            command = [
                "ffmpeg",
                "-y",
                "-i", str(input_video.absolute()),
                # Video encoding
                "-c:v", "libx264",
                "-b:v", profile.video_bitrate,
                "-maxrate", profile.video_bitrate,
                "-bufsize", str(int(profile.video_bitrate.rstrip('k')) * 2) + "k",
                "-vf", f"scale=-2:{profile.height}",  # Scale to target height, maintain aspect ratio
                "-profile:v", "main",
                "-level", "4.0",
                # Audio encoding
                "-c:a", "aac",
                "-b:a", profile.audio_bitrate,
                "-ac", "2",
                # HLS settings
                "-f", "hls",
                "-hls_time", str(self.segment_duration),
                "-hls_playlist_type", "vod",
                "-hls_segment_type", "fmp4",
                "-hls_fmp4_init_filename", "init.mp4",
                "-hls_segment_filename", str(quality_dir / "video%d.m4s"),
                "-hls_flags", "independent_segments",
                "-start_number", "1",
                str(quality_dir / "video.m3u8")
            ]
            
            logging.debug(f"FFmpeg command: {' '.join(command)}")
            
            # Execute FFmpeg
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600
            )
            
            # Log FFmpeg output for debugging
            if result.stdout:
                logging.info(f"FFmpeg stdout: {result.stdout[:500]}")
            if result.stderr:
                logging.info(f"FFmpeg stderr (last 1000 chars): {result.stderr[-1000:]}")
            
            if result.returncode == 0:
                logging.info(f"Successfully encoded {profile.name} quality")
                
                # List all files created in the output directory
                created_files = list(quality_dir.iterdir())
                logging.info(f"Files created in {quality_dir.name}: {[f.name for f in created_files]}")
                
                # Verify output files exist
                playlist = quality_dir / "video.m3u8"
                init_file = quality_dir / "init.mp4"
                
                if not playlist.exists():
                    logging.error(f"Playlist not created: {playlist}")
                    logging.error(f"Expected location: {playlist.absolute()}")
                    return False
                
                # If init file doesn't exist, create it manually from the encoded video
                if not init_file.exists():
                    logging.warning(f"Init file not created by FFmpeg, creating manually...")
                    try:
                        # Create init segment with just the moov atom
                        init_command = [
                            "ffmpeg",
                            "-y",
                            "-i", str(input_video.absolute()),
                            "-c:v", "libx264",
                            "-b:v", profile.video_bitrate,
                            "-vf", f"scale=-2:{profile.height}",
                            "-profile:v", "main",
                            "-level", "4.0",
                            "-c:a", "aac",
                            "-b:a", profile.audio_bitrate,
                            "-ac", "2",
                            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                            "-f", "mp4",
                            "-t", "0.001",  # Minimal duration to create init segment
                            str(init_file)
                        ]
                        
                        init_result = subprocess.run(
                            init_command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=60
                        )
                        
                        if init_result.returncode == 0 and init_file.exists():
                            logging.info(f"Successfully created init file manually")
                        else:
                            logging.error(f"Failed to create init file manually: {init_result.stderr[-500:]}")
                            return False
                    except Exception as e:
                        logging.error(f"Error creating init file: {e}")
                        return False
                
                # Count segment files
                segments = list(quality_dir.glob("video*.m4s"))
                logging.info(f"Created {len(segments)} segments for {profile.name}")
                
                return True
            else:
                logging.error(f"FFmpeg encoding failed for {profile.name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error(f"Encoding timeout for {profile.name}")
            return False
        except Exception as e:
            logging.error(f"Error encoding {profile.name}: {e}", exc_info=True)
            return False
    
    def create_master_playlist(
        self,
        output_dir: Path,
        profiles: List[QualityProfile]
    ) -> bool:
        """
        Create master HLS playlist referencing all quality levels.
        
        Args:
            output_dir: Path to output directory (video/)
            profiles: List of QualityProfile objects that were encoded
            
        Returns:
            True if master playlist created successfully
        """
        try:
            master_path = output_dir / "master_h264.m3u8"
            logging.info(f"Creating master playlist: {master_path}")
            
            with open(master_path, 'w') as f:
                f.write("#EXTM3U\n")
                f.write("#EXT-X-VERSION:3\n")
                
                # Add each quality level
                for profile in profiles:
                    quality_dir = output_dir / profile.folder_name
                    playlist_path = quality_dir / "video.m3u8"
                    
                    # Verify the quality playlist exists
                    if not playlist_path.exists():
                        logging.warning(f"Skipping {profile.name}: playlist not found")
                        continue
                    
                    # Get actual resolution from profile
                    # Calculate width maintaining 16:9 aspect ratio
                    width = int(profile.height * 16 / 9)
                    
                    # Write stream info
                    f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                           f"RESOLUTION={width}x{profile.height},"
                           f'CODECS="avc1.4d401f,mp4a.40.2"\n')
                    f.write(f"{profile.folder_name}/video.m3u8\n")
                    
                    logging.debug(f"Added {profile.name} to master playlist")
            
            logging.info(f"Master playlist created successfully with {len(profiles)} qualities")
            return True
            
        except Exception as e:
            logging.error(f"Error creating master playlist: {e}", exc_info=True)
            return False
