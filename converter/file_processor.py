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
    
    def find_source_folders(self) -> List[Path]:
        """
        Scan input directory for subdirectories.
        
        Returns:
            List of Path objects representing subdirectories in input directory
        """
        try:
            if not self.input_dir.exists() or not self.input_dir.is_dir():
                return []
            
            source_folders = [
                item for item in self.input_dir.iterdir() 
                if item.is_dir()
            ]
            
            return source_folders
            
        except Exception:
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
                return False, "no_mp4"
            elif mp4_count == 1:
                return True, "valid"
            else:
                return False, "multiple_mp4"
        except Exception:
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
                return mp4_files[0]
            else:
                return None
        except Exception:
            return None
    
    def copy_non_mp4_files(self, source_folder: Path, dest_folder: Path) -> None:
        """
        Copy non-MP4 files (jpg, json, and other files) from source to destination.
        
        Args:
            source_folder: Path to the source folder
            dest_folder: Path to the destination folder
        """
        try:
            if not source_folder.exists() or not dest_folder.exists():
                return
            
            for item in source_folder.iterdir():
                if item.is_file() and item.suffix.lower() != '.mp4':
                    try:
                        dest_path = dest_folder / item.name
                        shutil.copy2(item, dest_path)
                    except Exception:
                        pass
                
        except Exception:
            pass
    
    def create_output_structure(self, folder_name: str) -> Path:
        """
        Create output folder with "video" subdirectory.
        
        Args:
            folder_name: Name of the folder to create in output directory
            
        Returns:
            Path to the created output folder
        """
        try:
            output_folder = self.output_dir / folder_name
            video_folder = output_folder / "video"
            
            # Create directories if they don't exist
            video_folder.mkdir(parents=True, exist_ok=True)
            
            return output_folder
            
        except Exception as e:
            raise IOError(f"Failed to create output structure: {e}")
    
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
            return total_size
        except Exception:
            return 0
    
    def delete_source_folder(self, folder: Path) -> None:
        """
        Safely remove source directory and all its contents.
        
        Args:
            folder: Path to the folder to delete
        """
        try:
            if folder.exists() and folder.is_dir():
                shutil.rmtree(folder)
        except Exception:
            pass
