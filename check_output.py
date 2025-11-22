#!/usr/bin/env python3
"""
Quick script to check all output folders for init.mp4 files
"""

import sys
from pathlib import Path


def check_output_directory(output_dir):
    """Check all video folders in output directory for init.mp4."""
    output_path = Path(output_dir)
    
    if not output_path.exists():
        print(f"❌ Output directory does not exist: {output_dir}")
        return
    
    print(f"Checking output directory: {output_path}")
    print("=" * 70)
    
    # Find all video folders
    video_folders = []
    for item in output_path.iterdir():
        if item.is_dir():
            video_folder = item / "video"
            if video_folder.exists():
                video_folders.append(video_folder)
    
    if not video_folders:
        print("No video folders found in output directory")
        return
    
    print(f"Found {len(video_folders)} video folder(s)\n")
    
    missing_init = []
    empty_init = []
    valid_init = []
    
    for video_folder in sorted(video_folders):
        folder_name = video_folder.parent.name
        init_file = video_folder / "init.mp4"
        playlist_file = video_folder / "video.m3u8"
        
        print(f"📁 {folder_name}/video/")
        
        # Check playlist
        if playlist_file.exists():
            size = playlist_file.stat().st_size
            print(f"   ✓ video.m3u8 ({size} bytes)")
        else:
            print(f"   ❌ video.m3u8 MISSING")
        
        # Check init.mp4
        if init_file.exists():
            size = init_file.stat().st_size
            if size > 0:
                print(f"   ✓ init.mp4 ({size} bytes)")
                valid_init.append(folder_name)
            else:
                print(f"   ❌ init.mp4 EMPTY (0 bytes)")
                empty_init.append(folder_name)
        else:
            print(f"   ❌ init.mp4 MISSING")
            missing_init.append(folder_name)
        
        # Check segments
        segments = sorted(video_folder.glob("video*.m4s"))
        if segments:
            print(f"   ✓ {len(segments)} segment file(s)")
        else:
            print(f"   ❌ No segment files")
        
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total folders checked: {len(video_folders)}")
    print(f"✓ Valid init.mp4: {len(valid_init)}")
    print(f"❌ Empty init.mp4: {len(empty_init)}")
    print(f"❌ Missing init.mp4: {len(missing_init)}")
    
    if empty_init:
        print(f"\nFolders with EMPTY init.mp4:")
        for folder in empty_init:
            print(f"  - {folder}")
    
    if missing_init:
        print(f"\nFolders with MISSING init.mp4:")
        for folder in missing_init:
            print(f"  - {folder}")
    
    if empty_init or missing_init:
        print("\n⚠️  These folders need to be re-converted!")
        print("   Delete them and run the conversion again.")
    else:
        print("\n✅ All folders have valid init.mp4 files!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_output.py <output_directory>")
        print()
        print("Example:")
        print("  python check_output.py U:\\testoutput")
        print("  python check_output.py /path/to/output")
        sys.exit(1)
    
    check_output_directory(sys.argv[1])
