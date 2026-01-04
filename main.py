#!/usr/bin/env python3
"""
MP4 to HLS Video Converter
Main entry point for the video conversion system.
"""

import logging
import shutil
from pathlib import Path

from converter.config_manager import ConfigManager
from converter.file_processor import FileProcessor
from converter.video_converter import VideoConverter
from converter.validator import Validator
from converter.compressor import ZipCompressor
from converter.stats_tracker import StatsTracker
from converter.progress_bar import ProgressBar
from converter.stop_flag import StopFlag


def main():
    """Main entry point for the MP4 to HLS converter."""
    # Initialize logging configuration - only show errors
    logging.basicConfig(
        level=logging.ERROR,
        format='[%(levelname)s] %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Initialize stop flag and register signal handlers
    stop_flag = StopFlag.get_instance()
    stop_flag.reset()
    stop_flag.register_signal_handlers()
    
    # Clean up any leftover stop signal file
    stop_file = Path(".converter_stop_signal")
    if stop_file.exists():
        try:
            stop_file.unlink()
        except Exception:
            pass
    
    print("=" * 60)
    print("MP4 to HLS Video Converter")
    print("=" * 60)
    print("Press Ctrl+C to stop after current video completes")
    print("=" * 60)
    
    try:
        # Load configuration
        config = ConfigManager()
        
        # Create output directory if it doesn't exist
        try:
            config.output_directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[ERROR] Failed to create output directory: {e}")
            return 1
        
        # Initialize components
        stats = StatsTracker()
        stats.start_timer()
        file_processor = FileProcessor(config.input_directory, config.output_directory)
        
        # Find source folders
        source_folders = file_processor.find_source_folders()
        
        if not source_folders:
            print("[ERROR] No subdirectories found in input directory")
            stats.print_summary()
            return 0
        
        # Filter folders - only process folders with exactly 1 MP4 file
        valid_folders = []
        for folder in source_folders:
            is_valid, reason = file_processor.has_single_mp4_file(folder)
            if is_valid:
                valid_folders.append(folder)
            elif reason == "no_mp4":
                stats.record_skipped_no_mp4()
            elif reason == "multiple_mp4":
                stats.record_skipped_multiple_mp4()
        
        if not valid_folders:
            print("[ERROR] No valid folders to process (folders must contain exactly 1 MP4 file)")
            stats.print_summary()
            return 0
        
        print(f"\nFound {len(valid_folders)} video(s) to process\n")
        
        # Process each valid folder
        for idx, folder in enumerate(valid_folders, 1):
            # Check if stop was requested before starting new video
            # Check both signal handler and stop file (for GUI)
            stop_file = Path(".converter_stop_signal")
            if stop_file.exists():
                stop_flag.request_stop()
                try:
                    stop_file.unlink()
                except Exception:
                    pass
            
            if stop_flag.is_stop_requested():
                print(f"\n[STOP] Stopping conversion - {len(valid_folders) - idx + 1} video(s) remaining")
                break
            
            progress = ProgressBar(folder.name, len(valid_folders), idx)
            progress.start()
            
            # Start timing this video
            stats.start_video_timer()
            
            try:
                # Phase 1: Validating folder
                progress.next_phase("Validating folder")
                mp4_file = file_processor.get_mp4_file(folder)
                if not mp4_file:
                    stats.end_video_timer()
                    progress.finish(success=False)
                    print(f"[ERROR] No MP4 file found in {folder.name}")
                    stats.record_failure()
                    continue
                
                source_size = file_processor.get_folder_size(folder)
                stats.add_source_size(source_size)
                
                try:
                    output_folder = file_processor.create_output_structure(folder.name)
                except Exception as e:
                    stats.end_video_timer()
                    progress.finish(success=False)
                    print(f"[ERROR] Failed to create output structure: {e}")
                    stats.record_failure()
                    continue
                
                # Phase 2: Detecting quality
                progress.next_phase("Detecting quality")
                converter = VideoConverter(segment_duration=6)
                
                # Phase 3: Separating audio
                progress.next_phase("Separating audio")
                
                # Phase 4: Creating HLS format
                progress.next_phase("Creating HLS format")
                
                # Phase 5: Creating VP9 format
                progress.next_phase("Creating VP9 format")
                
                # Perform actual conversion (phases 2-5 happen inside)
                conversion_result = converter.convert_to_hls(mp4_file, output_folder)
                
                if not conversion_result.success:
                    stats.end_video_timer()
                    progress.finish(success=False)
                    print(f"[ERROR] {conversion_result.error_message}")
                    stats.record_failure()
                    continue
                
                # Validate HLS output
                validator = Validator()
                validation_result = validator.validate_hls_output(conversion_result)
                
                if not validation_result.valid:
                    stats.end_video_timer()
                    progress.finish(success=False)
                    print(f"[ERROR] Validation failed - {validation_result.error_message}")
                    stats.record_failure()
                    continue
                
                # Copy non-MP4 files (including data.json)
                file_processor.copy_non_mp4_files(folder, output_folder)
                
                # Phase 6: Creating thumbnails
                progress.next_phase("Creating thumbnails")
                thumbnail_percentages = config.thumbnail_video_percentage
                converter.extract_thumbnails(mp4_file, output_folder, thumbnail_percentages)
                
                # Phase 7: Creating trailer (only if video > 60 seconds)
                video_duration = converter.get_video_duration(mp4_file)
                if video_duration is not None and video_duration > 60:
                    progress.next_phase("Creating trailer")
                    trailer_success = converter.generate_trailer(mp4_file, output_folder)
                    if not trailer_success:
                        print(f"[WARNING] Failed to generate trailer for {folder.name}")
                elif video_duration is not None:
                    logging.debug(f"Skipping trailer: video duration {video_duration:.1f}s <= 60s")
                
                # Track output size
                output_size = file_processor.get_folder_size(output_folder)
                stats.add_output_size(output_size)
                
                # Record success
                stats.record_success()
                
                # Compress if enabled
                if config.compress:
                    try:
                        compressor = ZipCompressor()
                        zip_path = config.output_directory / f"{folder.name}.zip"
                        compression_success = compressor.compress_folder(output_folder, zip_path)
                        
                        if compression_success:
                            compressed_size = compressor.get_compressed_size(zip_path)
                            stats.add_output_size(compressed_size - output_size)
                            
                            try:
                                shutil.rmtree(output_folder)
                            except Exception as e:
                                logger.error(f"Error deleting uncompressed folder: {e}")
                    except Exception as e:
                        logger.error(f"Error during compression: {e}")
                
                # Delete source folder if enabled
                if config.delete_mp4:
                    file_processor.delete_source_folder(folder)
                
                # End timing and show completion
                elapsed = stats.end_video_timer()
                progress.finish(success=True, elapsed_time=elapsed)
                    
            except Exception as e:
                stats.end_video_timer()
                progress.finish(success=False)
                print(f"[ERROR] Unexpected error: {e}")
                stats.record_failure()
                continue
        
        # Print final statistics
        stats.print_summary()
        
        print("=" * 60)
        if stop_flag.is_stop_requested():
            print("Conversion Stopped (completed current video)")
        else:
            print("Conversion Complete")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
