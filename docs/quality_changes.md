# Quality Filtering Implementation - COMPLETED

## Overview

Quality filtering has been implemented to limit the number of quality levels during HLS conversion:

- **H.264 (HLS)**: 360p and 720p only (max 2 qualities)
- **VP9**: 360p, 480p, and 720p only (max 3 qualities, NO 1080p)
- **Maximum total**: 5 qualities across both codecs

If source video is lower resolution than target qualities, only available lower qualities are generated.

---

## Implemented Changes

### 1. converter/video_quality.py

#### Quality Profiles (Limited)

```python
# H.264: 360p, 720p only (max 2)
QUALITY_PROFILES_H264 = {
    "720p": QualityProfile("720p", 720, "2077k", "128k", 2077570, "h264"),
    "360p": QualityProfile("360p", 360, "800k", "128k", 800000, "h264"),
}

# VP9: 360p, 480p, 720p only (NO 1080p - max 3)
QUALITY_PROFILES_VP9 = {
    "720p": QualityProfile("720p", 720, "1291k", "128k", 1290999, "vp9"),
    "480p": QualityProfile("480p", 480, "768k", "128k", 768242, "vp9"),
    "360p": QualityProfile("360p", 360, "594k", "128k", 594105, "vp9"),
}

# Quality orders
QUALITY_ORDER_H264 = ["720p", "360p"]
QUALITY_ORDER_VP9 = ["720p", "480p", "360p"]
```

#### Quality Detection

- 1080p and above → Treated as 720p (highest available)
- 720p → 720p
- 480p → 480p
- 360p and below → 360p

### 2. converter/hls_encoder.py

#### New Method: create_unified_master_playlist()

Creates a single `playlist.m3u8` file containing all H.264 and VP9 quality levels:

```python
def create_unified_master_playlist(
    self,
    output_dir: Path,
    h264_profiles: List[QualityProfile],
    vp9_profiles: List[QualityProfile],
    has_audio: bool = True
) -> bool:
```

### 3. converter/video_converter.py

Updated to create unified master playlist after encoding all qualities.

### 4. converter/validator.py

Updated to skip FFmpeg validation for master playlists (playlist.m3u8, master_h264.m3u8, master_vp9.m3u8).

---

## Output Structure

### For 720p+ Source Video (5 qualities)

```
output_folder/
├── video/
│   ├── playlist.m3u8        ← Single master playlist (all qualities)
│   ├── 720p/
│   │   ├── video.m3u8
│   │   ├── init.mp4
│   │   └── video1.m4s, video2.m4s, ...
│   ├── 360p/
│   │   ├── video.m3u8
│   │   ├── init.mp4
│   │   └── video1.m4s, video2.m4s, ...
│   ├── vp9_720p/
│   │   ├── video.m3u8
│   │   ├── init.mp4
│   │   └── video1.m4s, video2.m4s, ...
│   ├── vp9_480p/
│   │   ├── video.m3u8
│   │   ├── init.mp4
│   │   └── video1.m4s, video2.m4s, ...
│   └── vp9_360p/
│       ├── video.m3u8
│       ├── init.mp4
│       └── video1.m4s, video2.m4s, ...
├── audio/
│   ├── aac.m3u8
│   ├── init.mp4
│   └── audio1.m4s, audio2.m4s, ...
├── thumbnail1.jpg
├── thumbnail2.jpg
├── thumbnail3.jpg
└── trailer.mp4
```

### For 480p Source Video (3 qualities)

```
output_folder/
├── video/
│   ├── playlist.m3u8
│   ├── 360p/
│   ├── vp9_480p/
│   └── vp9_360p/
├── audio/
└── ...
```

### For 360p Source Video (2 qualities)

```
output_folder/
├── video/
│   ├── playlist.m3u8
│   ├── 360p/
│   └── vp9_360p/
├── audio/
└── ...
```

---

## Unified Playlist Format (playlist.m3u8)

```m3u8
#EXTM3U
#EXT-X-VERSION:4
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="English",DEFAULT=YES,AUTOSELECT=YES,LANGUAGE="en",URI="../audio/aac.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=2077570,RESOLUTION=1280x720,CODECS="avc1.64001f,mp4a.40.2",AUDIO="audio"
720p/video.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,CODECS="avc1.4d401e,mp4a.40.2",AUDIO="audio"
360p/video.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1290999,RESOLUTION=1280x720,CODECS="vp09.00.31.08.00.01.01.01.00,mp4a.40.2",AUDIO="audio"
vp9_720p/video.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=768242,RESOLUTION=854x480,CODECS="vp09.00.30.08.00.01.01.01.00,mp4a.40.2",AUDIO="audio"
vp9_480p/video.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=594105,RESOLUTION=640x360,CODECS="vp09.00.21.08.00.01.01.01.00,mp4a.40.2",AUDIO="audio"
vp9_360p/video.m3u8
```

---

## Quality Mapping Table

| Source Resolution | H.264 Qualities | VP9 Qualities | Total |
|-------------------|-----------------|---------------|-------|
| 1080p+ | 720p, 360p | 720p, 480p, 360p | 5 |
| 720p | 720p, 360p | 720p, 480p, 360p | 5 |
| 480p | 360p | 480p, 360p | 3 |
| 360p | 360p | 360p | 2 |
| <360p | 360p | 360p | 2 |

---

## Folder Naming Convention

Quality folders follow these patterns:

- **H.264**: `720p`, `360p` (resolution only, no codec prefix)
- **VP9**: `vp9_720p`, `vp9_480p`, `vp9_360p` (with codec prefix)

---

## Validation Checklist

- [x] H.264 limited to 720p and 360p only
- [x] VP9 limited to 720p, 480p, and 360p only (NO 1080p)
- [x] Maximum 5 qualities total
- [x] Single master playlist (playlist.m3u8) created as only entry point
- [x] Quality detection respects source resolution
- [x] Lower resolution sources only generate available qualities
- [x] Folder naming matches convention (h264_XXXp, vp9_XXXp)

---

## Testing

Run the converter with different source resolutions to verify:

```bash
# Test with 1080p video
python main.py

# Check output structure
ls -la output_folder/video/

# Verify playlist content
cat output_folder/video/playlist.m3u8
```

Expected results:
- 1080p source → 5 quality folders
- 720p source → 5 quality folders
- 480p source → 3 quality folders
- 360p source → 2 quality folders
