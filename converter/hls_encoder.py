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
            
            # Execute FFmpeg from the audio directory so files are created there
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600,
                cwd=str(audio_dir.absolute())
            )
            
            if result.returncode == 0:
                # Verify playlist exists
                playlist = audio_dir / "aac.m3u8"
                init_file = audio_dir / "init.mp4"
                
                if not playlist.exists():
                    return False
                
                # Create init file manually if needed
                if not init_file.exists():
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
                        
                        if init_result.returncode != 0 or not init_file.exists():
                            return False
                    except Exception:
                        return False
                
                return True
            else:
                return False
                
        except subprocess.TimeoutExpired:
            return False
        except Exception:
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
            
            # Execute FFmpeg from the quality directory so files are created there
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600,
                cwd=str(quality_dir.absolute())
            )
            
            if result.returncode == 0:
                # Verify output files exist
                playlist = quality_dir / "video.m3u8"
                init_file = quality_dir / "init.mp4"
                
                if not playlist.exists():
                    return False
                
                # If init file doesn't exist, create it manually from the encoded video
                if not init_file.exists():
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
                        
                        if init_result.returncode != 0 or not init_file.exists():
                            return False
                    except Exception:
                        return False
                
                return True
            else:
                return False
                
        except subprocess.TimeoutExpired:
            return False
        except Exception:
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
                
                # Add each quality level
                for profile in profiles:
                    quality_dir = output_dir / profile.folder_name
                    playlist_path = quality_dir / "video.m3u8"
                    
                    # Verify the quality playlist exists
                    if not playlist_path.exists():
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
                            if has_audio:
                                f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                                       f"AVERAGE-BANDWIDTH={profile.bandwidth},"
                                       f"RESOLUTION={width}x{profile.height},"
                                       f"FRAME-RATE=30,"
                                       f'CODECS="{video_codec},mp4a.40.2",'
                                       f'AUDIO="audio"\n')
                            else:
                                f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                                       f"AVERAGE-BANDWIDTH={profile.bandwidth},"
                                       f"RESOLUTION={width}x{profile.height},"
                                       f"FRAME-RATE=30,"
                                       f'CODECS="{video_codec}"\n')
                        else:
                            if has_audio:
                                f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                                       f"RESOLUTION={width}x{profile.height},"
                                       f'CODECS="{video_codec},mp4a.40.2",'
                                       f'AUDIO="audio"\n')
                            else:
                                f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                                       f"RESOLUTION={width}x{profile.height},"
                                       f'CODECS="{video_codec}"\n')
                    else:
                        # H.264 format - simple format from requirements.md
                        if has_audio:
                            f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                                   f"RESOLUTION={width}x{profile.height},"
                                   f'CODECS="{video_codec},mp4a.40.2",'
                                   f'AUDIO="audio"\n')
                        else:
                            f.write(f"#EXT-X-STREAM-INF:BANDWIDTH={profile.bandwidth},"
                                   f"RESOLUTION={width}x{profile.height},"
                                   f'CODECS="{video_codec}"\n')
                    
                    f.write(f"{profile.folder_name}/video.m3u8\n")
            
            return True
            
        except Exception:
            return False
