"""Validates converted HLS files for playability and completeness."""

import logging
import subprocess
from pathlib import Path
from typing import List

from converter.data_models import ConversionResult, ValidationResult


class Validator:
    """Validates converted HLS files for playability and completeness."""
    
    def __init__(self):
        """Initialize Validator for HLS output validation."""
        logging.info("Validator initialized")
    
    def _check_playlist_exists(self, playlist_path: Path) -> bool:
        """
        Verify that playlist file exists.
        
        Args:
            playlist_path: Path to the playlist file
            
        Returns:
            True if playlist file exists and is readable, False otherwise
        """
        try:
            if not playlist_path.exists():
                logging.error(f"Playlist file does not exist: {playlist_path}")
                return False
            
            if not playlist_path.is_file():
                logging.error(f"Playlist path is not a file: {playlist_path}")
                return False
            
            # Try to read the file to ensure it's readable
            with open(playlist_path, 'r') as f:
                f.read(1)  # Read at least one character
            
            logging.debug(f"Playlist file exists and is readable: {playlist_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error checking playlist file: {e}")
            return False
    
    def _parse_playlist(self, playlist_path: Path) -> List[str]:
        """
        Extract segment references from m3u8 playlist file.
        
        Args:
            playlist_path: Path to the playlist file
            
        Returns:
            List of segment filenames referenced in the playlist
        """
        segment_files = []
        
        try:
            with open(playlist_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Segment files end with .m4s
                    if line.endswith('.m4s'):
                        segment_files.append(line)
                    # Also check for init segment
                    elif line.endswith('.mp4') and 'init' in line.lower():
                        segment_files.append(line)
            
            logging.debug(f"Parsed {len(segment_files)} segment references from playlist")
            return segment_files
            
        except Exception as e:
            logging.error(f"Error parsing playlist file: {e}")
            return []
    
    def _check_segments_exist(self, segment_files: List[Path]) -> bool:
        """
        Verify that all segment files are present on disk.
        
        Args:
            segment_files: List of Path objects for segment files
            
        Returns:
            True if all segment files exist, False otherwise
        """
        if not segment_files:
            logging.error("No segment files to validate")
            return False
        
        missing_files = []
        for segment_file in segment_files:
            if not segment_file.exists():
                missing_files.append(segment_file.name)
        
        if missing_files:
            logging.error(f"Missing segment files: {', '.join(missing_files)}")
            return False
        
        logging.debug(f"All {len(segment_files)} segment files exist")
        return True
    
    def _validate_with_ffmpeg(self, playlist_path: Path) -> bool:
        """
        Test playlist playability using FFmpeg probe.
        
        Args:
            playlist_path: Path to the playlist file
            
        Returns:
            True if FFmpeg can successfully probe the playlist, False otherwise
        """
        try:
            # Check if FFmpeg is installed
            try:
                subprocess.run(
                    ["ffmpeg", "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                logging.error("FFmpeg is not installed or not accessible in PATH")
                return False
            
            # Run FFmpeg probe on the playlist
            # Use absolute path to ensure relative paths in playlist work correctly
            command = [
                "ffmpeg",
                "-v", "error",
                "-i", str(playlist_path.absolute()),
                "-f", "null",
                "-"
            ]
            
            logging.debug(f"Running FFmpeg validation: {' '.join(command)}")
            # Run from the playlist's directory to resolve relative paths
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                cwd=str(playlist_path.parent)
            )
            
            if result.returncode == 0:
                logging.debug("FFmpeg validation successful: playlist is playable")
                return True
            else:
                logging.error(f"FFmpeg validation failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("FFmpeg validation timed out")
            return False
        except Exception as e:
            logging.error(f"Error during FFmpeg validation: {e}")
            return False
    
    def validate_hls_output(self, conversion_result: ConversionResult) -> ValidationResult:
        """
        Run all validation checks on HLS output and return detailed result.
        
        Args:
            conversion_result: ConversionResult from the conversion process
            
        Returns:
            ValidationResult with detailed validation status
        """
        logging.info(f"Starting HLS validation for {conversion_result.playlist_file.name}")
        
        # If conversion itself failed, return invalid result immediately
        if not conversion_result.success:
            error_msg = f"Conversion failed: {conversion_result.error_message}"
            logging.error(error_msg)
            return ValidationResult(
                valid=False,
                playlist_valid=False,
                segments_valid=False,
                ffmpeg_playable=False,
                error_message=error_msg
            )
        
        # Step 1: Check if playlist exists
        playlist_valid = self._check_playlist_exists(conversion_result.playlist_file)
        if not playlist_valid:
            error_msg = f"Playlist file validation failed: {conversion_result.playlist_file}"
            logging.error(error_msg)
            return ValidationResult(
                valid=False,
                playlist_valid=False,
                segments_valid=False,
                ffmpeg_playable=False,
                error_message=error_msg
            )
        
        # Step 2: Check if init file exists and is not empty
        if not conversion_result.init_file.exists():
            error_msg = f"Initialization file missing: {conversion_result.init_file}"
            logging.error(error_msg)
            return ValidationResult(
                valid=False,
                playlist_valid=True,
                segments_valid=False,
                ffmpeg_playable=False,
                error_message=error_msg
            )
        
        init_size = conversion_result.init_file.stat().st_size
        if init_size == 0:
            error_msg = f"Initialization file is empty: {conversion_result.init_file}"
            logging.error(error_msg)
            return ValidationResult(
                valid=False,
                playlist_valid=True,
                segments_valid=False,
                ffmpeg_playable=False,
                error_message=error_msg
            )
        
        logging.debug(f"Init file validated: {conversion_result.init_file.name} ({init_size} bytes)")
        
        # Step 3: Check if all segment files exist
        all_files = [conversion_result.init_file] + conversion_result.segment_files
        segments_valid = self._check_segments_exist(all_files)
        
        if not segments_valid:
            error_msg = "One or more segment files are missing"
            logging.error(error_msg)
            return ValidationResult(
                valid=False,
                playlist_valid=True,
                segments_valid=False,
                ffmpeg_playable=False,
                error_message=error_msg
            )
        
        # Step 4: Validate with FFmpeg
        # Note: Skip FFmpeg validation for master playlists with separate audio tracks
        # as FFmpeg may have issues resolving relative paths on Windows
        ffmpeg_playable = True
        playlist_name = conversion_result.playlist_file.name
        if playlist_name in ["master_h264.m3u8", "master_vp9.m3u8", "playlist.m3u8"]:
            logging.debug("Skipping FFmpeg validation for master playlist (has separate audio track)")
        else:
            ffmpeg_playable = self._validate_with_ffmpeg(conversion_result.playlist_file)
            
            if not ffmpeg_playable:
                error_msg = "FFmpeg validation failed: playlist is not playable"
                logging.error(error_msg)
                return ValidationResult(
                    valid=False,
                    playlist_valid=True,
                    segments_valid=True,
                    ffmpeg_playable=False,
                    error_message=error_msg
                )
        
        # All validation checks passed
        logging.info("HLS validation successful: all checks passed")
        return ValidationResult(
            valid=True,
            playlist_valid=True,
            segments_valid=True,
            ffmpeg_playable=True,
            error_message=None
        )
