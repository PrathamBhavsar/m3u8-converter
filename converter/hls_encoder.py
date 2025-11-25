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
    
    def encode_audio(
        self,
        input_video: Path,
        output_dir: Path,
        audio_bitrate: str = "128k"
    ) -> bool:
        """
        Encode audio separately to audio/ folder.
        
        Args:
            input_video: Path to source video file
            output_dir: Path to output directory (video/)
            audio_bitrate: Audio bitrate (e.g., "128k")
            
        Returns:
            True if encoding succeeded, False otherwise
        """
        try:
            # Create audio folder
            audio_dir = output_dir.parent / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"Encoding audio to {audio_dir}")
            
            # Build FFmpeg command for audio-only HLS
            # Use relative paths for init and segments so they work in the playlist
            command = [
                "ffmpeg",
                "-y",
                "-i", str(input_video.absolute()),
                # Audio only - no video
                "-vn",
                # Audio encoding
                "-c:a", "aac",
                "-b:a", audio_bitrate,
                "-ac", "2",
                # HLS settings
                "-f", "hls",
                "-hls_time", str(self.segment_duration),
                "-hls_playlist_type", "vod",
                "-hls_segment_type", "fmp4",
                "-hls_fmp4_init_filename", "init.mp4",
                "-hls_segment_filename", "audio%d.m4s",
                "-hls_flags", "independent_segments",
                "-start_number", "1",
                "aac.m3u8"
            ]
            
            logging.debug(f"FFmpeg audio command: {' '.join(command)}")
            
            # Execute FFmpeg from the audio directory so files are created there
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600,
                cwd=str(audio_dir.absolute())
            )
            
            if result.stderr:
                logging.debug(f"FFmpeg audio stderr (last 500 chars): {result.stderr[-500:]}")
            
            if result.returncode == 0:
                logging.info(f"Successfully encoded audio")
                
                # List created files
                created_files = list(audio_dir.iterdir())
                logging.info(f"Audio files created: {[f.name for f in created_files]}")
                
                # Verify playlist exists
                playlist = audio_dir / "aac.m3u8"
                init_file = audio_dir / "init.mp4"
                
                if not playlist.exists():
                    logging.error(f"Audio playlist not created: {playlist}")
                    return False
                
                # Create init file manually if needed
                if not init_file.exists():
                    logging.warning(f"Audio init file not created by FFmpeg, creating manually...")
                    try:
                        init_command = [
                            "ffmpeg",
                            "-y",
                            "-i", str(input_video.absolute()),
                            "-vn",
                            "-c:a", "aac",
                            "-b:a", audio_bitrate,
                            "-ac", "2",
                            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                            "-f", "mp4",
                            "-t", "0.001",
                            str(init_file.absolute())
                        ]
                        
                        init_result = subprocess.run(
                            init_command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=60
                        )
                        
                        if init_result.returncode == 0 and init_file.exists():
                            logging.info(f"Successfully created audio init file manually")
                        else:
                            logging.error(f"Failed to create audio init file")
                            return False
                    except Exception as e:
                        logging.error(f"Error creating audio init file: {e}")
                        return False
                
                # Count audio segments
                segments = list(audio_dir.glob("audio*.m4s"))
                logging.info(f"Created {len(segments)} audio segments")
                
                return True
            else:
                logging.error(f"FFmpeg audio encoding failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error(f"Audio encoding timeout")
            return False
        except Exception as e:
            logging.error(f"Error encoding audio: {e}", exc_info=True)
            return False
    
    def encode_quality(
        self,
        input_video: Path,
        output_dir: Path,
        profile: QualityProfile
    ) -> bool:
        """
        Encode video to a specific quality level (video only, no audio).
        Supports both H.264 and VP9 codecs.
        
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
            
            logging.info(f"Encoding {profile.name} quality ({profile.codec}) to {quality_dir}")
            
            # Build FFmpeg command based on codec
            if profile.codec == "vp9":
                # VP9 encoding
                command = [
                    "ffmpeg",
                    "-y",
                    "-i", str(input_video.absolute()),
                    # Video only - no audio
                    "-an",
                    # VP9 encoding
                    "-c:v", "libvpx-vp9",
                    "-b:v", profile.video_bitrate,
                    "-maxrate", profile.video_bitrate,
                    "-bufsize", str(int(profile.video_bitrate.rstrip('k')) * 2) + "k",
                    "-vf", f"scale=-2:{profile.height}",
                    "-row-mt", "1",  # Enable row-based multithreading for VP9
                    "-cpu-used", "2",  # Speed vs quality tradeoff (0-5, higher is faster)
                    # HLS settings
                    "-f", "hls",
                    "-hls_time", str(self.segment_duration),
                    "-hls_playlist_type", "vod",
                    "-hls_segment_type", "fmp4",
                    "-hls_fmp4_init_filename", "init.mp4",
                    "-hls_segment_filename", "video%d.m4s",
                    "-hls_flags", "independent_segments",
                    "-start_number", "1",
                    "video.m3u8"
                ]
            else:
                # H.264 encoding (default)
                command = [
                    "ffmpeg",
                    "-y",
                    "-i", str(input_video.absolute()),
                    # Video only - no audio
                    "-an",
                    # Video encoding
                    "-c:v", "libx264",
                    "-b:v", profile.video_bitrate,
                    "-maxrate", profile.video_bitrate,
                    "-bufsize", str(int(profile.video_bitrate.rstrip('k')) * 2) + "k",
                    "-vf", f"scale=-2:{profile.height}",
                    "-profile:v", "main",
                    "-level", "4.0",
                    # HLS settings
                    "-f", "hls",
                    "-hls_time", str(self.segment_duration),
                    "-hls_playlist_type", "vod",
                    "-hls_segment_type", "fmp4",
                    "-hls_fmp4_init_filename", "init.mp4",
                    "-hls_segment_filename", "video%d.m4s",
                    "-hls_flags", "independent_segments",
                    "-start_number", "1",
                    "video.m3u8"
                ]
            
            logging.debug(f"FFmpeg command: {' '.join(command)}")
            
            # Execute FFmpeg from the quality directory so files are created there
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600,
                cwd=str(quality_dir.absolute())
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
                        # Create init segment with just the moov atom (video only)
                        if profile.codec == "vp9":
                            init_command = [
                                "ffmpeg",
                                "-y",
                                "-i", str(input_video.absolute()),
                                "-an",
                                "-c:v", "libvpx-vp9",
                                "-b:v", profile.video_bitrate,
                                "-vf", f"scale=-2:{profile.height}",
                                "-row-mt", "1",
                                "-cpu-used", "2",
                                "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                                "-f", "mp4",
                                "-t", "0.001",
                                str(init_file.absolute())
                            ]
                        else:
                            init_command = [
                                "ffmpeg",
                                "-y",
                                "-i", str(input_video.absolute()),
                                "-an",
                                "-c:v", "libx264",
                                "-b:v", profile.video_bitrate,
                                "-vf", f"scale=-2:{profile.height}",
                                "-profile:v", "main",
                                "-level", "4.0",
                                "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                                "-f", "mp4",
                                "-t", "0.001",
                                str(init_file.absolute())
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
        profiles: List[QualityProfile],
        has_audio: bool = True,
        codec: str = "h264"
    ) -> bool:
        """
        Create master HLS playlist referencing all quality levels and audio.
        
        Args:
            output_dir: Path to output directory (video/)
            profiles: List of QualityProfile objects that were encoded
            has_audio: Whether separate audio track exists
            codec: Codec type ("h264" or "vp9")
            
        Returns:
            True if master playlist created successfully
        """
        try:
            master_filename = f"master_{codec}.m3u8"
            master_path = output_dir / master_filename
            logging.info(f"Creating master playlist: {master_path}")
            
            with open(master_path, 'w') as f:
                f.write("#EXTM3U\n")
                
                if codec == "vp9":
                    f.write("#EXT-X-VERSION:4\n")
                else:
                    f.write("#EXT-X-VERSION:3\n")
                
                # Add audio media group if audio exists
                if has_audio:
                    audio_path = output_dir.parent / "audio" / "aac.m3u8"
                    if audio_path.exists():
                        f.write('#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="English",'
                               'DEFAULT=YES,AUTOSELECT=YES,LANGUAGE="en",'
                               'URI="../audio/aac.m3u8"\n')
                        logging.info("Added audio track to master playlist")
                
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
                    
                    # Determine codec string for playlist
                    if codec == "vp9":
                        # VP9 codec strings based on profile level
                        vp9_codecs = {
                            1080: "vp09.00.41.08.00.01.01.01.00",
                            720: "vp09.00.31.08.00.01.01.01.00",
                            480: "vp09.00.30.08.00.01.01.01.00",
                            360: "vp09.00.21.08.00.01.01.01.00"
                        }
                        video_codec = vp9_codecs.get(profile.height, "vp09.00.30.08.00.01.01.01.00")
                    else:
                        # H.264 codec strings based on profile level
                        h264_codecs = {
                            720: "avc1.64001f",
                            360: "avc1.4d401e"
                        }
                        video_codec = h264_codecs.get(profile.height, "avc1.4d401f")
                    
                    # Write stream info - format matches requirements.md exactly
                    if codec == "vp9":
                        # VP9 format: only 1080p has AVERAGE-BANDWIDTH
                        if profile.height == 1080:
                            f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                                   f"AVERAGE-BANDWIDTH={profile.bandwidth},"
                                   f"RESOLUTION={width}x{profile.height},"
                                   f"FRAME-RATE=30,"
                                   f'CODECS="{video_codec},mp4a.40.2"\n')
                        else:
                            f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                                   f"RESOLUTION={width}x{profile.height},"
                                   f'CODECS="{video_codec},mp4a.40.2"\n')
                    else:
                        # H.264 format - simple format from requirements.md
                        f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                               f"RESOLUTION={width}x{profile.height},"
                               f'CODECS="{video_codec},mp4a.40.2"\n')
                    
                    f.write(f"{profile.folder_name}/video.m3u8\n")
                    
                    logging.debug(f"Added {profile.name} to master playlist")
            
            logging.info(f"Master playlist created successfully with {len(profiles)} qualities")
            return True
            
        except Exception as e:
            logging.error(f"Error creating master playlist: {e}", exc_info=True)
            return False
