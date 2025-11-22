# MP4 to HLS Video Converter

A Python-based tool for converting MP4 videos to HLS (HTTP Live Streaming) format with optional compression and source file management.

## Features

- Convert MP4 videos to HLS format with fragmented MP4 segments
- Configurable segment duration (default: 5 seconds)
- Optional ZIP compression of output files
- Optional deletion of source files after successful conversion
- Comprehensive error handling and logging
- Simple GUI for easy configuration
- Batch processing of multiple folders

## Requirements

- Python 3.7 or higher
- FFmpeg installed and accessible in PATH
- tkinter (usually included with Python)

## Installation

1. Install Python from [python.org](https://www.python.org/)
2. Install FFmpeg:
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg` or equivalent

3. Verify FFmpeg installation:
   ```bash
   ffmpeg -version
   ```

## Usage

### GUI Mode (Recommended)

1. **Windows**: Double-click `launch.bat`
2. **macOS/Linux**: Run `python3 gui.py`

The GUI provides:
- Input directory selection (browse button)
- Output directory selection (browse button)
- Compress output checkbox
- Delete original files checkbox (with warning)
- Start/Stop conversion buttons
- Real-time log output
- Status bar

### Command Line Mode

```bash
python3 main.py
```

Configuration is read from `config.json`.

## Configuration

The `config.json` file contains the following settings:

```json
{
  "compress": true,
  "delete_mp4": false,
  "output_directory_path": "/path/to/output",
  "input_directory_path": "/path/to/input"
}
```

- **compress**: Create ZIP archives of output folders
- **delete_mp4**: Delete source folders after successful conversion (⚠️ irreversible!)
- **input_directory_path**: Path to directory containing source folders
- **output_directory_path**: Path where converted files will be saved

The GUI automatically updates `config.json` when you change settings.

## Input Structure

The converter expects the following structure:

```
input_directory/
├── folder1/
│   ├── video.mp4
│   ├── thumbnail.jpg
│   └── metadata.json
├── folder2/
│   ├── video.mp4
│   └── cover.jpg
└── folder3/
    └── video.mp4
```

## Output Structure

### Without Compression

```
output_directory/
├── folder1/
│   ├── video/
│   │   ├── video.m3u8      (HLS playlist)
│   │   ├── init.mp4        (⚠️ REQUIRED initialization segment)
│   │   ├── video1.m4s      (video segment 1)
│   │   ├── video2.m4s      (video segment 2)
│   │   └── ...
│   ├── thumbnail.jpg
│   └── metadata.json
└── folder2/
    └── ...
```

**Important:** The `init.mp4` file is REQUIRED for HLS playback. If this file is missing or empty (0 bytes), the video will not play.

### With Compression

```
output_directory/
├── folder1.zip
├── folder2.zip
└── folder3.zip
```

## Conversion Process

1. **Scan**: Find all subdirectories in input directory
2. **Filter**: Identify folders containing MP4 files
3. **Convert**: For each folder:
   - Create output structure with `video/` subdirectory
   - Convert MP4 to HLS format using FFmpeg
   - Validate output (playlist, segments, playability)
   - Copy non-MP4 files (images, JSON, etc.)
   - Optionally compress to ZIP
   - Optionally delete source folder
4. **Report**: Display statistics summary

## Error Handling

- Errors in one folder don't stop processing of other folders
- Source files are preserved if conversion or validation fails
- Comprehensive logging at INFO, WARNING, and ERROR levels
- Detailed error messages for troubleshooting

## Logging

Logs include:
- Configuration loading and validation
- Folder processing progress
- Conversion start/end with file sizes
- Validation results
- Compression status
- Deletion operations
- Error details with stack traces

## Statistics

After processing, the converter displays:
- Total source size (GB)
- Total output size (GB)
- Compression ratio
- Successful conversions
- Failed conversions
- Total conversions

## Safety Features

- Input directory validation
- Output validation before source deletion
- Confirmation dialog for deletion in GUI
- Graceful error handling
- Keyboard interrupt support (Ctrl+C)

## Verifying Output

After conversion, verify your output is correct:

### Quick Check Script

```bash
# Check all folders in output directory
python check_output.py U:\testoutput

# Or on macOS/Linux
python3 check_output.py /path/to/output
```

This will show you which folders have valid init.mp4 files and which need to be re-converted.

### Manual Verification

For each converted folder, check:

1. **init.mp4 exists and is NOT empty:**
   ```bash
   # Windows
   dir U:\testoutput\folder1\video\init.mp4
   
   # macOS/Linux
   ls -lh /path/to/output/folder1/video/init.mp4
   ```
   
   The file should be 1-5 KB (NOT 0 bytes!)

2. **Playlist references init.mp4:**
   ```bash
   # Windows
   type U:\testoutput\folder1\video\video.m3u8 | findstr init
   
   # macOS/Linux
   grep init /path/to/output/folder1/video/video.m3u8
   ```
   
   Should show: `#EXT-X-MAP:URI="init.mp4"`

3. **Test playback:**
   ```bash
   cd U:\testoutput\folder1\video
   ffplay video.m3u8
   ```

### Diagnostic Tool

For detailed diagnostics of a specific folder:

```bash
python diagnose_hls.py U:\testoutput\folder1\video
```

## Troubleshooting

### init.mp4 is missing or empty
- **Symptom:** Video won't play, FFplay shows "Failed to open initialization section"
- **Cause:** FFmpeg conversion failed or was interrupted
- **Solution:** 
  1. Delete the output folder
  2. Re-run the conversion
  3. Check logs for FFmpeg errors
  4. Verify input MP4 is valid

### FFmpeg not found
- Ensure FFmpeg is installed and in your system PATH
- Test with: `ffmpeg -version`

### Permission denied errors
- Check folder permissions
- Run with appropriate privileges
- Ensure output directory is writable

### Conversion failures
- Check FFmpeg output in logs
- Verify input MP4 files are valid
- Ensure sufficient disk space

### GUI doesn't start
- Verify Python installation: `python --version`
- Check tkinter is available: `python -c "import tkinter"`
- On Linux, install: `sudo apt-get install python3-tk`

## License

This project is provided as-is for video conversion purposes.

## Support

For issues or questions, check the log output for detailed error messages.
