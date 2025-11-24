#!/usr/bin/env python3
"""
MP4 to HLS Video Converter
Main entry point for the video conversion system.
"""

import logging
import shutil

from converter.config_manager import ConfigManager
from converter.file_processor import FileProcessor
from converter.video_converter import VideoConverter
from converter.validator import Validator
from converter.compressor import ZipCompressor
from converter.stats_tracker import StatsTracker


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
        # Load configuration
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
        
        # Initialize components
        stats = StatsTracker()
        file_processor = FileProcessor(config.input_directory, config.output_directory)
        
        # Find source folders
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
        
        # Process each valid folder
        for idx, folder in enumerate(valid_folders, 1):
            logger.info("=" * 60)
            logger.info(f"Processing folder {idx}/{len(valid_folders)}: {folder.name}")
            logger.info("=" * 60)
            
            try:
                # Get MP4 file
                logger.debug(f"Retrieving MP4 file from {folder.name}")
                mp4_file = file_processor.get_mp4_file(folder)
                if not mp4_file:
                    logger.error(f"Failed to get MP4 file from {folder.name}")
                    stats.record_failure()
                    continue
                
                # Track source file size
                logger.debug(f"Calculating source folder size for {folder.name}")
                source_size = file_processor.get_folder_size(folder)
                stats.add_source_size(source_size)
                logger.info(f"Source folder size: {source_size / (1024*1024):.2f} MB")
                
                # Create output structure
                logger.debug(f"Creating output structure for {folder.name}")
                try:
                    output_folder = file_processor.create_output_structure(folder.name)
                except Exception as e:
                    logger.error(f"Failed to create output structure for {folder.name}: {e}")
                    stats.record_failure()
                    continue
                
                # Convert video to HLS with multiple qualities
                logger.info(f"Starting video conversion for {folder.name}")
                converter = VideoConverter(segment_duration=6)
                conversion_result = converter.convert_to_hls(mp4_file, output_folder)
                
                # Handle conversion errors
                if not conversion_result.success:
                    logger.error(f"Conversion failed for {folder.name}")
                    logger.error(f"Error details: {conversion_result.error_message}")
                    stats.record_failure()
                    continue
                
                logger.info(f"Conversion completed successfully for {folder.name}")
                
                # Validate HLS output
                logger.info(f"Starting validation for {folder.name}")
                validator = Validator()
                validation_result = validator.validate_hls_output(conversion_result)
                
                # Copy non-MP4 files and extract thumbnails if validation succeeds
                if validation_result.valid:
                    logger.info(f"Validation passed for {folder.name}")
                    logger.debug(f"Copying non-MP4 files for {folder.name}")
                    file_processor.copy_non_mp4_files(folder, output_folder)
                    
                    # Extract thumbnails
                    logger.info(f"Extracting thumbnails for {folder.name}")
                    thumbnail_percentages = config.thumbnail_video_percentage
                    logger.debug(f"Thumbnail extraction points: {thumbnail_percentages}%")
                    thumbnail_success = converter.extract_thumbnails(mp4_file, output_folder, thumbnail_percentages)
                    if thumbnail_success:
                        logger.info(f"Thumbnails extracted successfully for {folder.name}")
                    else:
                        logger.warning(f"Thumbnail extraction had issues for {folder.name}")
                    
                    # Track output size
                    logger.debug(f"Calculating output folder size for {folder.name}")
                    output_size = file_processor.get_folder_size(output_folder)
                    stats.add_output_size(output_size)
                    logger.info(f"Output folder size: {output_size / (1024*1024):.2f} MB")
                    
                    # Record success
                    stats.record_success()
                    logger.info(f"Successfully processed {folder.name}")
                    
                    # Compress if enabled
                    if config.compress:
                        logger.info(f"Compression enabled, creating ZIP archive for {folder.name}")
                        
                        try:
                            compressor = ZipCompressor()
                            zip_path = config.output_directory / f"{folder.name}.zip"
                            compression_success = compressor.compress_folder(output_folder, zip_path)
                            
                            if compression_success:
                                compressed_size = compressor.get_compressed_size(zip_path)
                                stats.add_output_size(compressed_size - output_size)
                                logger.info(f"Compressed size: {compressed_size / (1024*1024):.2f} MB")
                                logger.info(f"Compression ratio: {(compressed_size / output_size * 100):.1f}%")
                                
                                # Delete uncompressed folder
                                try:
                                    logger.debug(f"Deleting uncompressed folder: {output_folder}")
                                    shutil.rmtree(output_folder)
                                    logger.info(f"Deleted uncompressed folder: {output_folder.name}")
                                except Exception as e:
                                    logger.error(f"Error deleting uncompressed folder: {e}")
                            else:
                                logger.error(f"Compression failed for {folder.name}, keeping uncompressed output")
                        
                        except Exception as e:
                            logger.error(f"Error during compression process for {folder.name}: {e}")
                            logger.info(f"Keeping uncompressed output due to compression error")
                    
                    # Delete source folder if enabled
                    if config.delete_mp4:
                        logger.info(f"Source deletion enabled, removing {folder.name}")
                        file_processor.delete_source_folder(folder)
                    
                else:
                    logger.error(f"Validation failed for {folder.name}")
                    logger.error(f"Validation error: {validation_result.error_message}")
                    stats.record_failure()
                    continue
                    
            except Exception as e:
                logger.error(f"Unexpected error processing {folder.name}: {e}", exc_info=True)
                stats.record_failure()
                continue
        
        # Print final statistics
        stats.print_summary()
        
        logger.info("=" * 60)
        logger.info("MP4 to HLS Video Converter - Completed")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
