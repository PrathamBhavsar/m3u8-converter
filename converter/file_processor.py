"""File system operations for MP4 conversion workflow."""

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Tuple


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
    
    def has_single_mp4_file(self, folder: Path) -> Tuple[bool, str]:
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
