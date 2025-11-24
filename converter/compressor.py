"""ZIP compression utilities."""

import logging
import zipfile
from pathlib import Path


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
