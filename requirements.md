Detailed Requirements
 

Customizable Thumbnail Extraction:

Implement functionality to extract three (3) distinct thumbnails from the source video.

This extraction process must be configurable using percentages of the total video duration, rather than fixed time points (e.g., for a 10-minute video, the default extraction points might be 30%, 50%, and 70%).

The current example (3, 5, and 7 minutes for a 10-minute video) should map to the default percentage settings.
=============================================


Video Quality Generation:

H.264 (HLS): Generate video qualities 360p and 720p.

VP9: Generate all available qualities: 360p, 480p, 720p, and 1080p (if the source resolution permits).

Note: The process must handle legacy/older videos that may have source resolutions below 360p or 480p gracefully.

Master Manifest Creation:

Generate two (2) separate master manifest files:

master_vp9.m3u8




#EXTM3U
#EXT-X-VERSION:4
#EXT-X-STREAM-INF:BANDWIDTH=2905000,AVERAGE-BANDWIDTH=2905000,RESOLUTION=1080x1920,FRAME-RATE=30,CODECS="vp09.00.41.08.00.01.01.01.00,mp4a.40.2"
vp9_1080p/video.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1290999,RESOLUTION=720x1280,CODECS="vp09.00.31.08.00.01.01.01.00,mp4a.40.2"
vp9_720p/video.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=768242,RESOLUTION=480x854,CODECS="vp09.00.30.08.00.01.01.01.00,mp4a.40.2"
vp9_480p/video.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=594105,RESOLUTION=360x640,CODECS="vp09.00.21.08.00.01.01.01.00,mp4a.40.2"
vp9_360p/video.m3u8



master_h264.m3u8




#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=2077570,RESOLUTION=720x1280,CODECS="avc1.64001f,mp4a.40.2"
h264_720p/video.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=360x640,CODECS="avc1.4d401e,mp4a.40.2"
h264_360p/video.m3u8



Audio Extraction:

Extract one (1) single audio track in the AAC-LC format. 

Only one audio file is used for all qualities and codecs.



video_slug/
├── master_vp9.m3u8
├── master_h264.m3u8
├── vp9_1080p/
│   └── video.m3u8
├── vp9_720p/
│   └── video.m3u8
├── vp9_480p/
│   └── video.m3u8
├── vp9_360p/
│   └── video.m3u8
├── h264_720p/
│   └── video.m3u8
├── h264_360p/
│   └── video.m3u8
└── audio/
    └── aac.m3u8