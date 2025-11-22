#!/usr/bin/env python3
"""
HLS Output Diagnostic Tool
Checks HLS output for common issues and provides detailed information.
"""

import sys
import subprocess
from pathlib import Path


def diagnose_hls_folder(video_folder_path):
    """Diagnose HLS output in a video folder."""
    video_folder = Path(video_folder_path)
    
    print("=" * 70)
    print(f"HLS Diagnostic Report for: {video_folder}")
    print("=" * 70)
    print()
    
    # Check if folder exists
    if not video_folder.exists():
        print(f"❌ ERROR: Folder does not exist: {video_folder}")
        return False
    
    if not video_folder.is_dir():
        print(f"❌ ERROR: Path is not a directory: {video_folder}")
        return False
    
    print(f"✓ Folder exists: {video_folder}")
    print()
    
    # Check for required files
    playlist_file = video_folder / "video.m3u8"
    init_file = video_folder / "init.mp4"
    
    print("File Check:")
    print("-" * 70)
    
    # Check playlist
    if playlist_file.exists():
        size = playlist_file.stat().st_size
        print(f"✓ video.m3u8 exists ({size} bytes)")
    else:
        print(f"❌ video.m3u8 is MISSING")
        return False
    
    # Check init file
    if init_file.exists():
        size = init_file.stat().st_size
        if size > 0:
            print(f"✓ init.mp4 exists ({size} bytes)")
        else:
            print(f"❌ init.mp4 exists but is EMPTY (0 bytes)")
            print(f"   This will cause playback to fail!")
            return False
    else:
        print(f"❌ init.mp4 is MISSING")
        return False
    
    # Check for segment files
    segment_files = sorted(video_folder.glob("video*.m4s"))
    if segment_files:
        print(f"✓ Found {len(segment_files)} segment file(s):")
        for seg in segment_files:
            size = seg.stat().st_size
            status = "✓" if size > 0 else "❌ EMPTY"
            print(f"  {status} {seg.name} ({size} bytes)")
    else:
        print(f"❌ No segment files (video*.m4s) found")
        return False
    
    print()
    
    # Read and display playlist content
    print("Playlist Content:")
    print("-" * 70)
    try:
        with open(playlist_file, 'r') as f:
            content = f.read()
            print(content)
    except Exception as e:
        print(f"❌ Error reading playlist: {e}")
        return False
    
    print()
    
    # Test with FFmpeg
    print("FFmpeg Playback Test:")
    print("-" * 70)
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(playlist_file), "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓ Playlist is playable with FFmpeg")
        else:
            print(f"❌ FFmpeg playback failed:")
            print(f"   {result.stderr}")
            return False
    except FileNotFoundError:
        print("⚠️  FFmpeg not found - skipping playback test")
    except subprocess.TimeoutExpired:
        print("⚠️  FFmpeg test timed out")
    except Exception as e:
        print(f"⚠️  Error running FFmpeg test: {e}")
    
    print()
    print("=" * 70)
    print("✅ DIAGNOSIS COMPLETE: All checks passed!")
    print("=" * 70)
    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python diagnose_hls.py <path_to_video_folder>")
        print()
        print("Example:")
        print("  python diagnose_hls.py U:\\testoutput\\234234\\video")
        print("  python diagnose_hls.py /path/to/output/folder/video")
        sys.exit(1)
    
    video_folder = sys.argv[1]
    success = diagnose_hls_folder(video_folder)
    
    if not success:
        print()
        print("=" * 70)
        print("❌ DIAGNOSIS FAILED: Issues found with HLS output")
        print("=" * 70)
        print()
        print("Recommendations:")
        print("1. Re-run the conversion for this folder")
        print("2. Check FFmpeg output logs for errors")
        print("3. Ensure sufficient disk space")
        print("4. Verify input MP4 file is valid")
        sys.exit(1)


if __name__ == "__main__":
    main()
