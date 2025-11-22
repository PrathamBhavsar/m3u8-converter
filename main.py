#!/usr/bin/env python3
"""
MP4 to HLS Video Converter
Main entry point for the video conversion system.
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ConversionResult:
    """Result of an MP4 to HLS conversion operation."""
    success: bool
    output_path: Path
    playlist_file: Path  # video.m3u8
    init_file: Path      # init.mp4
    segment_files: List[Path]  # video0.m4s, video1.m4s, ...
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


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""
    pass


class FileProcessor:
    """Manages file system operations for MP4 conversion workflow."""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        """
        Initialize FileProcessor with input and output directory paths.
        
        Args:
            input_dir: Path to the input directory containing source folders
            output_dir: Path to the output directory for converted files
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        logging.info(f"FileProcessor initialized: input={input_dir}, output={output_dir}")
    
    def find_source_folders(self) -> List[Path]:
        """
        Scan input directory for subdirectories.
        
        Returns:
            List of Path objects representing subdirectories in input directory
        """
        try:
            logging.debug(f"Scanning input directory: {self.input_dir}")
            
            if not self.input_dir.exists():
                logging.error(f"Input directory does not exist: {self.input_dir}")
                return []
            
            if not self.input_dir.is_dir():
                logging.error(f"Input path is not a directory: {self.input_dir}")
                return []
            
            source_folders = [
                item for item in self.input_dir.iterdir() 
                if item.is_dir()
            ]
            logging.info(f"Found {len(source_folders)} subdirectories in {self.input_dir}")
            
            if source_folders:
                logging.debug(f"Subdirectories: {[f.name for f in source_folders]}")
            
            return source_folders
            
        except PermissionError as e:
            logging.error(f"Permission denied accessing input directory {self.input_dir}: {e}")
            return []
        except Exception as e:
            logging.error(f"Error scanning input directory {self.input_dir}: {e}", exc_info=True)
            return []
    
    def has_single_mp4_file(self, folder: Path) -> tuple[bool, str]:
        """
        Check if a folder contains exactly one MP4 file.
        
        Args:
            folder: Path to the folder to check
            
        Returns:
            Tuple of (is_valid: bool, reason: str)
            - (True, "valid") if folder has exactly 1 MP4 file
            - (False, "no_mp4") if folder has no MP4 files
            - (False, "multiple_mp4") if folder has multiple MP4 files
        """
        try:
            mp4_files = list(folder.glob("*.mp4"))
            mp4_count = len(mp4_files)
            
            if mp4_count == 0:
                logging.debug(f"Folder {folder.name} contains no MP4 files - skipping")
                return False, "no_mp4"
            elif mp4_count == 1:
                logging.debug(f"Folder {folder.name} contains 1 MP4 file - valid")
                return True, "valid"
            else:
                logging.warning(f"Folder {folder.name} contains {mp4_count} MP4 files - skipping (only 1 allowed)")
                return False, "multiple_mp4"
        except Exception as e:
            logging.error(f"Error checking for MP4 files in {folder}: {e}")
            return False, "error"
    
    def get_mp4_file(self, folder: Path) -> Optional[Path]:
        """
        Retrieve the MP4 file path from a folder.
        
        Args:
            folder: Path to the folder containing MP4 file
            
        Returns:
            Path to the MP4 file, or None if no MP4 file exists or multiple exist
        """
        try:
            mp4_files = list(folder.glob("*.mp4"))
            if len(mp4_files) == 1:
                mp4_file = mp4_files[0]
                logging.debug(f"Found MP4 file: {mp4_file}")
                return mp4_file
            elif len(mp4_files) == 0:
                logging.warning(f"No MP4 file found in {folder}")
                return None
            else:
                logging.warning(f"Multiple MP4 files found in {folder} - skipping")
                return None
        except Exception as e:
            logging.error(f"Error retrieving MP4 file from {folder}: {e}")
            return None
    
    def copy_non_mp4_files(self, source_folder: Path, dest_folder: Path) -> None:
        """
        Copy non-MP4 files (jpg, json, and other files) from source to destination.
        
        Args:
            source_folder: Path to the source folder
            dest_folder: Path to the destination folder
        """
        import shutil
        
        try:
            logging.debug(f"Copying non-MP4 files from {source_folder.name} to {dest_folder.name}")
            
            if not source_folder.exists():
                logging.error(f"Source folder does not exist: {source_folder}")
                return
            
            if not dest_folder.exists():
                logging.error(f"Destination folder does not exist: {dest_folder}")
                return
            
            copied_count = 0
            failed_count = 0
            
            for item in source_folder.iterdir():
                if item.is_file() and item.suffix.lower() != '.mp4':
                    try:
                        dest_path = dest_folder / item.name
                        shutil.copy2(item, dest_path)
                        copied_count += 1
                        logging.debug(f"Copied {item.name} to {dest_folder}")
                    except PermissionError as e:
                        logging.error(f"Permission denied copying {item.name}: {e}")
                        failed_count += 1
                    except Exception as e:
                        logging.error(f"Error copying {item.name}: {e}")
                        failed_count += 1
            
            logging.info(f"Copied {copied_count} non-MP4 files from {source_folder.name}")
            if failed_count > 0:
                logging.warning(f"Failed to copy {failed_count} files from {source_folder.name}")
                
        except PermissionError as e:
            logging.error(f"Permission denied accessing folders: {e}")
        except Exception as e:
            logging.error(f"Error copying non-MP4 files from {source_folder.name}: {e}", exc_info=True)
    
    def create_output_structure(self, folder_name: str) -> Path:
        """
        Create output folder with "video" subdirectory.
        
        Args:
            folder_name: Name of the folder to create in output directory
            
        Returns:
            Path to the created output folder
        """
        try:
            logging.debug(f"Creating output structure for {folder_name}")
            output_folder = self.output_dir / folder_name
            video_folder = output_folder / "video"
            
            # Create directories if they don't exist
            video_folder.mkdir(parents=True, exist_ok=True)
            
            logging.info(f"Created output structure: {output_folder}")
            logging.debug(f"Video subdirectory: {video_folder}")
            return output_folder
            
        except PermissionError as e:
            error_msg = f"Permission denied creating output structure for {folder_name}: {e}"
            logging.error(error_msg)
            raise IOError(error_msg)
        except OSError as e:
            error_msg = f"OS error creating output structure for {folder_name}: {e}"
            logging.error(error_msg)
            raise IOError(error_msg)
        except Exception as e:
            error_msg = f"Error creating output structure for {folder_name}: {e}"
            logging.error(error_msg, exc_info=True)
            raise
    
    def get_folder_size(self, folder: Path) -> int:
        """
        Calculate total size of all files in a folder in bytes.
        
        Args:
            folder: Path to the folder
            
        Returns:
            Total size in bytes
        """
        try:
            total_size = 0
            for item in folder.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
            
            logging.debug(f"Folder {folder.name} size: {total_size} bytes")
            return total_size
        except Exception as e:
            logging.error(f"Error calculating folder size for {folder}: {e}")
            return 0
    
    def delete_source_folder(self, folder: Path) -> None:
        """
        Safely remove source directory and all its contents.
        
        Args:
            folder: Path to the folder to delete
        """
        import shutil
        
        try:
            logging.debug(f"Attempting to delete source folder: {folder}")
            
            if not folder.exists():
                logging.warning(f"Source folder does not exist: {folder}")
                return
            
            if not folder.is_dir():
                logging.warning(f"Source path is not a directory: {folder}")
                return
            
            # Log folder contents before deletion for audit trail
            try:
                file_count = len(list(folder.rglob("*")))
                logging.debug(f"Deleting folder {folder.name} containing {file_count} items")
            except Exception:
                pass
            
            shutil.rmtree(folder)
            logging.info(f"Successfully deleted source folder: {folder}")
            
        except PermissionError as e:
            logging.error(f"Permission denied deleting source folder {folder}: {e}")
        except OSError as e:
            logging.error(f"OS error deleting source folder {folder}: {e}")
        except Exception as e:
            logging.error(f"Error deleting source folder {folder}: {e}", exc_info=True)


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
    
    def _build_ffmpeg_command(self, input_mp4: Path, output_dir: Path) -> List[str]:
        """
        Construct FFmpeg command with HLS parameters.
        
        NOTE: This command is designed to be run from the video/ subdirectory
        as the working directory, so all output paths are relative.
        
        Args:
            input_mp4: Path to the input MP4 file (absolute path)
            output_dir: Path to the output directory (should contain "video" subdirectory)
            
        Returns:
            List of command arguments for subprocess execution
        """
        # Since we run FFmpeg from the video/ directory, use relative paths for output
        # but absolute path for input
        command = [
            "ffmpeg",
            "-y",  # Overwrite output files without asking
            "-i", str(input_mp4.absolute()),  # Use absolute path for input
            "-c:v", "libx264",  # Video codec
            "-c:a", "aac",      # Audio codec
            "-f", "hls",        # Output format: HLS
            "-hls_time", str(self.segment_duration),  # Segment duration
            "-hls_playlist_type", "vod",  # Video on demand playlist
            "-hls_segment_type", "fmp4",  # Fragmented MP4 segments
            "-hls_fmp4_init_filename", "init.mp4",  # Relative path - will be created in cwd
            "-hls_segment_filename", "video%d.m4s",  # Relative path - will be created in cwd
            "-hls_flags", "independent_segments",  # Ensure proper segment independence
            "-start_number", "1",  # Start segment numbering from 1 instead of 0
            "video.m3u8"  # Relative path - will be created in cwd
        ]
        
        logging.debug(f"Built FFmpeg command: {' '.join(command)}")
        logging.debug(f"Command will run from video/ subdirectory with relative output paths")
        return command
    
    def _execute_ffmpeg(self, command: List[str], working_dir: Path = None) -> tuple[bool, str]:
        """
        Run FFmpeg command via subprocess.
        
        Args:
            command: List of command arguments
            working_dir: Optional working directory for FFmpeg execution
            
        Returns:
            Tuple of (success: bool, output: str)
        """
        try:
            # Check if FFmpeg is installed
            logging.debug("Checking FFmpeg installation")
            try:
                version_result = subprocess.run(
                    ["ffmpeg", "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    text=True
                )
                logging.debug(f"FFmpeg version check passed: {version_result.stdout.split()[2] if len(version_result.stdout.split()) > 2 else 'unknown'}")
            except FileNotFoundError:
                error_msg = "FFmpeg is not installed or not found in PATH"
                logging.error(error_msg)
                return False, error_msg
            except subprocess.CalledProcessError as e:
                error_msg = f"FFmpeg version check failed: {e}"
                logging.error(error_msg)
                return False, error_msg
            
            # Execute FFmpeg command
            logging.info("Executing FFmpeg conversion...")
            logging.debug(f"FFmpeg command: {' '.join(command)}")
            if working_dir:
                logging.debug(f"Working directory: {working_dir}")
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600,  # 1 hour timeout for large files
                cwd=str(working_dir) if working_dir else None  # Set working directory
            )
            
            # Log FFmpeg output for debugging
            if result.stdout:
                logging.debug(f"FFmpeg stdout: {result.stdout[:500]}")  # First 500 chars
            if result.stderr:
                logging.debug(f"FFmpeg stderr (first 500 chars): {result.stderr[:500]}")
                # Log full stderr if there's an error
                if result.returncode != 0:
                    logging.error(f"FFmpeg full stderr: {result.stderr}")
            
            if result.returncode == 0:
                logging.info("FFmpeg conversion completed successfully")
                # Log the full stderr for successful conversions too (contains useful info)
                if result.stderr:
                    logging.debug(f"FFmpeg full output: {result.stderr}")
                return True, result.stderr
            else:
                error_msg = f"FFmpeg failed with return code {result.returncode}"
                logging.error(error_msg)
                logging.error(f"FFmpeg error output: {result.stderr}")
                return False, f"{error_msg}: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg conversion timed out after 1 hour"
            logging.error(error_msg)
            return False, error_msg
        except PermissionError as e:
            error_msg = f"Permission denied executing FFmpeg: {e}"
            logging.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error executing FFmpeg: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return False, error_msg
    
    def convert_to_hls(self, input_mp4: Path, output_dir: Path) -> ConversionResult:
        """
        Orchestrate conversion of MP4 to HLS format.
        
        Args:
            input_mp4: Path to the input MP4 file
            output_dir: Path to the output directory
            
        Returns:
            ConversionResult with success status and file paths
        """
        try:
            logging.info(f"Starting HLS conversion: {input_mp4.name}")
            logging.debug(f"Input file: {input_mp4}")
            logging.debug(f"Output directory: {output_dir}")
            
            # Validate input file
            if not input_mp4.exists():
                error_msg = f"Input MP4 file does not exist: {input_mp4}"
                logging.error(error_msg)
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=output_dir / "video" / "video.m3u8",
                    init_file=output_dir / "video" / "init.mp4",
                    segment_files=[],
                    error_message=error_msg
                )
            
            if not input_mp4.is_file():
                error_msg = f"Input path is not a file: {input_mp4}"
                logging.error(error_msg)
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=output_dir / "video" / "video.m3u8",
                    init_file=output_dir / "video" / "init.mp4",
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
            playlist_file = video_dir / "video.m3u8"
            init_file = video_dir / "init.mp4"
            
            # Build and execute FFmpeg command
            # Run FFmpeg with video_dir as working directory so relative paths work correctly
            command = self._build_ffmpeg_command(input_mp4, output_dir)
            success, output = self._execute_ffmpeg(command, working_dir=video_dir)
            
            if not success:
                logging.error(f"Conversion failed for {input_mp4.name}")
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=playlist_file,
                    init_file=init_file,
                    segment_files=[],
                    error_message=output
                )
            
            # Collect segment files
            try:
                logging.debug(f"Collecting output files from {video_dir}")
                
                # List ALL files created in video_dir for debugging
                all_files = list(video_dir.iterdir()) if video_dir.exists() else []
                logging.debug(f"Files in video directory: {[f.name for f in all_files]}")
                
                segment_files = sorted(video_dir.glob("video*.m4s"))
                
                if not segment_files:
                    error_msg = "No segment files were generated"
                    logging.error(error_msg)
                    return ConversionResult(
                        success=False,
                        output_path=output_dir,
                        playlist_file=playlist_file,
                        init_file=init_file,
                        segment_files=[],
                        error_message=error_msg
                    )
                
                logging.info(f"Conversion successful: generated {len(segment_files)} segments")
                logging.debug(f"Segment files: {[f.name for f in segment_files]}")
                
                # Verify init.mp4 was created and has content
                if init_file.exists():
                    init_size = init_file.stat().st_size
                    logging.info(f"Init file created: {init_file.name} ({init_size} bytes)")
                    if init_size == 0:
                        error_msg = "Init file was created but is empty"
                        logging.error(error_msg)
                        return ConversionResult(
                            success=False,
                            output_path=output_dir,
                            playlist_file=playlist_file,
                            init_file=init_file,
                            segment_files=segment_files,
                            error_message=error_msg
                        )
                else:
                    error_msg = "Init file was not created by FFmpeg"
                    logging.error(error_msg)
                    return ConversionResult(
                        success=False,
                        output_path=output_dir,
                        playlist_file=playlist_file,
                        init_file=init_file,
                        segment_files=segment_files,
                        error_message=error_msg
                    )
                
                # Log segment file sizes
                total_segment_size = sum(f.stat().st_size for f in segment_files)
                logging.debug(f"Total segment size: {total_segment_size / (1024*1024):.2f} MB")
                
                return ConversionResult(
                    success=True,
                    output_path=output_dir,
                    playlist_file=playlist_file,
                    init_file=init_file,
                    segment_files=segment_files,
                    error_message=None
                )
                
            except Exception as e:
                error_msg = f"Error collecting segment files: {str(e)}"
                logging.error(error_msg, exc_info=True)
                return ConversionResult(
                    success=False,
                    output_path=output_dir,
                    playlist_file=playlist_file,
                    init_file=init_file,
                    segment_files=[],
                    error_message=error_msg
                )
                
        except Exception as e:
            error_msg = f"Unexpected error during conversion: {str(e)}"
            logging.error(error_msg, exc_info=True)
            return ConversionResult(
                success=False,
                output_path=output_dir,
                playlist_file=output_dir / "video" / "video.m3u8",
                init_file=output_dir / "video" / "init.mp4",
                segment_files=[],
                error_message=error_msg
            )


class Validator:
    """Validates converted HLS files for playability and completeness."""
    
    def __init__(self):
        """Initialize Validator for HLS output validation."""
        logging.info("Validator initialized")
    
    def _check_playlist_exists(self, playlist_path: Path) -> bool:
        """
        Verify that video.m3u8 playlist file exists.
        
        Args:
            playlist_path: Path to the video.m3u8 file
            
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
            playlist_path: Path to the video.m3u8 file
            
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
            playlist_path: Path to the video.m3u8 file
            
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
            # This command attempts to read the playlist without producing output
            command = [
                "ffmpeg",
                "-v", "error",  # Only show errors
                "-i", str(playlist_path),
                "-f", "null",  # No output
                "-"
            ]
            
            logging.debug(f"Running FFmpeg validation: {' '.join(command)}")
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30  # 30 second timeout
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
        
        # Step 2: Parse playlist and verify segment references
        playlist_segments = self._parse_playlist(conversion_result.playlist_file)
        if not playlist_segments:
            error_msg = "No segments found in playlist file"
            logging.error(error_msg)
            return ValidationResult(
                valid=False,
                playlist_valid=True,
                segments_valid=False,
                ffmpeg_playable=False,
                error_message=error_msg
            )
        
        # Step 3: Check if init.mp4 exists and is not empty
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
        
        # Step 4: Check if all segment files exist
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
        
        # Step 5: Validate with FFmpeg
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


class ZipCompressor:
    """Creates ZIP archives from directory contents."""
    
    def __init__(self):
        """Initialize ZipCompressor for creating ZIP archives."""
        logging.info("ZipCompressor initialized")
    
    def compress_folder(self, folder_path: Path, output_path: Path) -> bool:
        """
        Create ZIP archive from directory contents.
        
        Args:
            folder_path: Path to the folder to compress
            output_path: Path where the ZIP file should be created
            
        Returns:
            True if compression succeeded, False otherwise
        """
        import zipfile
        
        try:
            logging.debug(f"Starting compression of {folder_path.name}")
            
            if not folder_path.exists():
                logging.error(f"Folder to compress does not exist: {folder_path}")
                return False
            
            if not folder_path.is_dir():
                logging.error(f"Path is not a directory: {folder_path}")
                return False
            
            logging.info(f"Compressing {folder_path.name} to {output_path.name}")
            
            # Create ZIP archive
            file_count = 0
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Walk through all files in the folder
                for file_path in folder_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            # Calculate relative path to preserve directory structure
                            arcname = file_path.relative_to(folder_path.parent)
                            zipf.write(file_path, arcname=arcname)
                            file_count += 1
                            logging.debug(f"Added to ZIP: {arcname}")
                        except Exception as e:
                            logging.error(f"Error adding {file_path.name} to ZIP: {e}")
            
            logging.info(f"Successfully created ZIP archive: {output_path} ({file_count} files)")
            return True
        
        except PermissionError as e:
            logging.error(f"Permission denied creating ZIP archive: {e}")
            return False
        except OSError as e:
            logging.error(f"OS error creating ZIP archive: {e}")
            return False
        except Exception as e:
            logging.error(f"Error creating ZIP archive: {e}", exc_info=True)
            return False
    
    def get_compressed_size(self, zip_path: Path) -> int:
        """
        Return ZIP file size in bytes.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            Size of ZIP file in bytes, or 0 if file doesn't exist or error occurs
        """
        try:
            if not zip_path.exists():
                logging.error(f"ZIP file does not exist: {zip_path}")
                return 0
            
            if not zip_path.is_file():
                logging.error(f"Path is not a file: {zip_path}")
                return 0
            
            size = zip_path.stat().st_size
            logging.debug(f"ZIP file {zip_path.name} size: {size} bytes")
            return size
            
        except Exception as e:
            logging.error(f"Error getting ZIP file size: {e}")
            return 0


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
        logging.info("StatsTracker initialized")
    
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
        # Convert bytes to gigabytes (1 GB = 1,073,741,824 bytes)
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
        
        print("\n" + "=" * 60)
        print("CONVERSION STATISTICS SUMMARY")
        print("=" * 60)
        print(f"Total Source Size:        {summary.total_source_gb:.2f} GB")
        print(f"Total Output Size:        {summary.total_output_gb:.2f} GB")
        print(f"Compression Ratio:        {summary.compression_ratio:.2%}")
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
            f"{summary.skipped_folders} skipped"
        )


class ConfigManager:
    """Manages loading and validation of configuration from config.json."""
    
    REQUIRED_FIELDS = [
        "compress",
        "delete_mp4",
        "output_directory_path",
        "input_directory_path"
    ]
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize ConfigManager with path to configuration file.
        
        Args:
            config_path: Path to the JSON configuration file (default: "config.json")
        """
        self.config_path = Path(config_path)
        self._config = None
        self._load_and_validate()
    
    def _load_and_validate(self):
        """Load and validate configuration on initialization."""
        try:
            logging.info(f"Loading configuration from {self.config_path}")
            self._config = self.load_config()
            if not self.validate_config(self._config):
                raise ConfigurationError("Configuration validation failed")
            logging.info("Configuration loaded and validated successfully")
        except ConfigurationError:
            logging.error(f"Configuration error: Failed to load or validate {self.config_path}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error loading configuration: {e}")
            raise ConfigurationError(f"Unexpected error loading configuration: {e}")
    
    def load_config(self) -> dict:
        """
        Read and parse JSON configuration from file.
        
        Returns:
            Dictionary containing configuration data
            
        Raises:
            ConfigurationError: If file is missing or contains invalid JSON
        """
        try:
            if not self.config_path.exists():
                error_msg = f"Configuration file not found: {self.config_path}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug(f"Reading configuration file: {self.config_path}")
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            logging.info(f"Configuration loaded from {self.config_path}")
            logging.debug(f"Configuration contents: {config}")
            return config
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file: {e}"
            logging.error(error_msg)
            raise ConfigurationError(error_msg)
        except ConfigurationError:
            raise
        except Exception as e:
            error_msg = f"Error reading configuration file: {e}"
            logging.error(error_msg)
            raise ConfigurationError(error_msg)
    
    def validate_config(self, config: dict) -> bool:
        """
        Verify that all required fields exist and are valid.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If validation fails
        """
        try:
            logging.debug("Starting configuration validation")
            
            # Check for missing required fields
            missing_fields = [
                field for field in self.REQUIRED_FIELDS 
                if field not in config
            ]
            
            if missing_fields:
                error_msg = f"Missing required configuration fields: {', '.join(missing_fields)}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug("All required fields present")
            
            # Validate boolean fields
            if not isinstance(config["compress"], bool):
                error_msg = f"'compress' must be a boolean, got {type(config['compress']).__name__}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            if not isinstance(config["delete_mp4"], bool):
                error_msg = f"'delete_mp4' must be a boolean, got {type(config['delete_mp4']).__name__}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug("Boolean fields validated")
            
            # Validate directory paths
            if not isinstance(config["input_directory_path"], str):
                error_msg = f"'input_directory_path' must be a string, got {type(config['input_directory_path']).__name__}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            if not isinstance(config["output_directory_path"], str):
                error_msg = f"'output_directory_path' must be a string, got {type(config['output_directory_path']).__name__}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug("Directory path types validated")
            
            # Validate that input directory exists
            input_path = Path(config["input_directory_path"])
            if not input_path.exists():
                error_msg = f"Input directory does not exist: {input_path}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            if not input_path.is_dir():
                error_msg = f"Input path is not a directory: {input_path}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug(f"Input directory validated: {input_path}")
            
            # Validate that output directory path is valid (create if doesn't exist)
            output_path = Path(config["output_directory_path"])
            try:
                # Check if parent directory exists for output path
                if output_path.exists() and not output_path.is_dir():
                    error_msg = f"Output path exists but is not a directory: {output_path}"
                    logging.error(error_msg)
                    raise ConfigurationError(error_msg)
                
                logging.debug(f"Output directory path validated: {output_path}")
                
            except ConfigurationError:
                raise
            except Exception as e:
                error_msg = f"Invalid output directory path: {e}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.info("Configuration validation successful")
            return True
            
        except ConfigurationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during configuration validation: {e}"
            logging.error(error_msg)
            raise ConfigurationError(error_msg)
    
    @property
    def compress(self) -> bool:
        """Get the compress configuration value."""
        return self._config["compress"]
    
    @property
    def delete_mp4(self) -> bool:
        """Get the delete_mp4 configuration value."""
        return self._config["delete_mp4"]
    
    @property
    def input_directory(self) -> Path:
        """Get the input directory path as a Path object."""
        return Path(self._config["input_directory_path"])
    
    @property
    def output_directory(self) -> Path:
        """Get the output directory path as a Path object."""
        return Path(self._config["output_directory_path"])


def main():
    """Main entry point for the MP4 to HLS converter."""
    # Initialize logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("MP4 to HLS Video Converter - Starting")
    logger.info("=" * 60)
    
    try:
        # Load configuration using ConfigManager
        logger.info("Loading configuration...")
        config = ConfigManager()
        logger.info(f"Configuration loaded successfully")
        logger.info(f"  - Compression: {'enabled' if config.compress else 'disabled'}")
        logger.info(f"  - Source deletion: {'enabled' if config.delete_mp4 else 'disabled'}")
        logger.info(f"  - Input directory: {config.input_directory}")
        logger.info(f"  - Output directory: {config.output_directory}")
        
        # Create output directory if it doesn't exist
        try:
            config.output_directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory ready: {config.output_directory}")
        except Exception as e:
            logger.error(f"Failed to create output directory: {e}")
            return 1
        
        # Initialize StatsTracker instance
        stats = StatsTracker()
        
        # Initialize FileProcessor with input/output directories
        file_processor = FileProcessor(config.input_directory, config.output_directory)
        
        # Call find_source_folders() to get list of subdirectories
        source_folders = file_processor.find_source_folders()
        
        if not source_folders:
            logger.warning("No subdirectories found in input directory")
            stats.print_summary()
            return 0
        
        # Filter folders - only process folders with exactly 1 MP4 file
        valid_folders = []
        for folder in source_folders:
            is_valid, reason = file_processor.has_single_mp4_file(folder)
            if is_valid:
                valid_folders.append(folder)
            elif reason == "no_mp4":
                logger.info(f"Skipping {folder.name}: No MP4 files found")
                stats.record_skipped_no_mp4()
            elif reason == "multiple_mp4":
                logger.warning(f"Skipping {folder.name}: Multiple MP4 files found (only 1 allowed)")
                stats.record_skipped_multiple_mp4()
        
        if not valid_folders:
            logger.warning("No valid folders to process (folders must contain exactly 1 MP4 file)")
            stats.print_summary()
            return 0
        
        skipped_count = len(source_folders) - len(valid_folders)
        logger.info(f"Found {len(valid_folders)} valid folders to process")
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} folders (see details above)")
        
        # Iterate through each valid folder
        for idx, folder in enumerate(valid_folders, 1):
            logger.info("=" * 60)
            logger.info(f"Processing folder {idx}/{len(valid_folders)}: {folder.name}")
            logger.info("=" * 60)
            
            try:
                # Get MP4 file path using get_mp4_file()
                logger.debug(f"Retrieving MP4 file from {folder.name}")
                mp4_file = file_processor.get_mp4_file(folder)
                if not mp4_file:
                    logger.error(f"Failed to get MP4 file from {folder.name}")
                    stats.record_failure()
                    continue
                
                # Track source file size using get_folder_size()
                logger.debug(f"Calculating source folder size for {folder.name}")
                source_size = file_processor.get_folder_size(folder)
                stats.add_source_size(source_size)
                logger.info(f"Source folder size: {source_size / (1024*1024):.2f} MB")
                
                # Create output structure using create_output_structure()
                logger.debug(f"Creating output structure for {folder.name}")
                try:
                    output_folder = file_processor.create_output_structure(folder.name)
                except Exception as e:
                    logger.error(f"Failed to create output structure for {folder.name}: {e}")
                    stats.record_failure()
                    continue
                
                # Initialize VideoConverter and call convert_to_hls()
                logger.info(f"Starting video conversion for {folder.name}")
                converter = VideoConverter(segment_duration=5)
                conversion_result = converter.convert_to_hls(mp4_file, output_folder)
                
                # Handle conversion errors and continue to next folder on failure
                if not conversion_result.success:
                    logger.error(f"Conversion failed for {folder.name}")
                    logger.error(f"Error details: {conversion_result.error_message}")
                    stats.record_failure()
                    continue
                
                logger.info(f"Conversion completed successfully for {folder.name}")
                
                # Initialize Validator and call validate_hls_output() on conversion result
                logger.info(f"Starting validation for {folder.name}")
                validator = Validator()
                validation_result = validator.validate_hls_output(conversion_result)
                
                # Copy non-MP4 files using copy_non_mp4_files() only if validation succeeds
                if validation_result.valid:
                    logger.info(f"Validation passed for {folder.name}")
                    logger.debug(f"Copying non-MP4 files for {folder.name}")
                    file_processor.copy_non_mp4_files(folder, output_folder)
                    
                    # Track output size using get_folder_size()
                    logger.debug(f"Calculating output folder size for {folder.name}")
                    output_size = file_processor.get_folder_size(output_folder)
                    stats.add_output_size(output_size)
                    logger.info(f"Output folder size: {output_size / (1024*1024):.2f} MB")
                    
                    # Record success or failure in StatsTracker based on validation result
                    stats.record_success()
                    logger.info(f"Successfully processed {folder.name}")
                    
                    # Check if compress flag is enabled in configuration
                    if config.compress:
                        logger.info(f"Compression enabled, creating ZIP archive for {folder.name}")
                        
                        try:
                            # Initialize ZipCompressor if compression is enabled
                            compressor = ZipCompressor()
                            
                            # Call compress_folder() to create ZIP archive of output folder
                            zip_path = config.output_directory / f"{folder.name}.zip"
                            compression_success = compressor.compress_folder(output_folder, zip_path)
                            
                            if compression_success:
                                # Update output size tracking with compressed size
                                compressed_size = compressor.get_compressed_size(zip_path)
                                # Subtract uncompressed size and add compressed size
                                stats.add_output_size(compressed_size - output_size)
                                logger.info(f"Compressed size: {compressed_size / (1024*1024):.2f} MB")
                                logger.info(f"Compression ratio: {(compressed_size / output_size * 100):.1f}%")
                                
                                # Delete uncompressed folder after successful compression
                                import shutil
                                try:
                                    logger.debug(f"Deleting uncompressed folder: {output_folder}")
                                    shutil.rmtree(output_folder)
                                    logger.info(f"Deleted uncompressed folder: {output_folder.name}")
                                except PermissionError as e:
                                    logger.error(f"Permission denied deleting uncompressed folder: {e}")
                                except Exception as e:
                                    logger.error(f"Error deleting uncompressed folder: {e}")
                            else:
                                logger.error(f"Compression failed for {folder.name}, keeping uncompressed output")
                        
                        except Exception as e:
                            logger.error(f"Error during compression process for {folder.name}: {e}")
                            logger.info(f"Keeping uncompressed output due to compression error")
                    
                    # Check if delete_mp4 flag is enabled in configuration
                    # Only proceed with deletion if validation succeeded
                    if config.delete_mp4:
                        logger.info(f"Source deletion enabled, removing source folder: {folder.name}")
                        
                        try:
                            # Call delete_source_folder() to remove source directory
                            file_processor.delete_source_folder(folder)
                            
                            # Log deletion action for audit trail
                            logger.info(f"Source folder deleted: {folder.name}")
                        except Exception as e:
                            logger.error(f"Failed to delete source folder {folder.name}: {e}")
                            logger.warning(f"Source folder preserved due to deletion error: {folder.name}")
                    else:
                        logger.debug(f"Source deletion disabled, preserving folder: {folder.name}")
                else:
                    logger.error(f"Validation failed for {folder.name}")
                    logger.error(f"Validation error details: {validation_result.error_message}")
                    stats.record_failure()
                    logger.warning(f"Source folder preserved due to validation failure: {folder.name}")
                
            except KeyboardInterrupt:
                logger.warning("Process interrupted by user")
                logger.info("Saving current statistics before exit...")
                stats.print_summary()
                return 130  # Standard exit code for SIGINT
            except Exception as e:
                logger.error(f"Unexpected error processing folder {folder.name}: {e}", exc_info=True)
                stats.record_failure()
                logger.info(f"Continuing to next folder...")
                continue
        
        # Call print_summary() on StatsTracker after all folders processed
        # Display total source GB, output GB, success count, and failure count
        logger.info("=" * 60)
        logger.info("All folders processed")
        logger.info("=" * 60)
        stats.print_summary()
        
        logger.info("=" * 60)
        logger.info("MP4 to HLS Video Converter completed successfully")
        logger.info("=" * 60)
        return 0
        
    except ConfigurationError as e:
        logger.error("=" * 60)
        logger.error(f"CONFIGURATION ERROR: {e}")
        logger.error("=" * 60)
        logger.error("Please check your config.json file and try again")
        return 1
    except KeyboardInterrupt:
        logger.warning("=" * 60)
        logger.warning("Process interrupted by user")
        logger.warning("=" * 60)
        return 130
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"FATAL ERROR: Unexpected error during initialization")
        logger.error(f"Error details: {e}")
        logger.error("=" * 60)
        logger.error("Stack trace:", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
