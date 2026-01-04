Description:
The m3u8-converter service needs to be updated to add a "preview" trailer functionality and improve the management of attached files during the conversion process.
1. Video Trailer Generation (.mp4)
Requirement: Generate a 4-second video clip to serve as a web cover preview.
Technical Specifications:
Format: .mp4.
Audio: The trailer must not have audio (muted).
Quality: It must be in low quality (low bitrate/resolution) to ensure a very small file size, similar to the reference example.
Quantity: Only one single trailer file is to be generated, regardless of whether the video is processed for HLS or VP9. It must be saved in the same location where the thumbnails are extracted.
Visual Reference: trailer.mp4
 
2. Conditional Extraction Logic
Business Rule:
If the original video duration to be converted is > 60 seconds: Generate trailer + 3 images.
If the original video duration to be converted is <= 60 seconds: Generate only the 3 images (skip trailer creation).
3. data.json File Preservation
Input Path: Videos and files will be pulled from the path m3u8-converter\input.
Input Structure: A folder named by ID (e.g., 4050/) containing the .mp4 video and a data.json file.
Expected Behavior: The process must detect the data.json file, preserve it, and compress it at the end of the process along with the conversion results, respecting the original structure.
Expected Output Reference: Monosnap e8c0a21ef0e0f5101a0d9e590435203ca7bf96af 2026-01-03 23-11-09.png 
Acceptance Criteria
[ ] The trailer is generated without audio and with high compression for minimum file size.
[ ] The trailer is generated only if the original video exceeds one minute in duration.
[ ] The data.json file is included in the final compressed package without alterations.
[ ] A single .mp4 preview file is generated even if multiple quality outputs (HLS/VP9) exist.