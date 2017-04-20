video_thumb_resolutions = [
    {'name': 'thumb', 'wh': [640, 360], 'ext': 'jpg', 'update': False}
]

video_resolutions = [
    # Priority ordering: first one gets encoded, then the rest
    {'name': '360', 'wh': [640, 360], 'ext': 'mp4'},
    {'name': '720', 'wh': [1280, 720], 'ext': 'mp4'},
    {'name': '1080', 'wh': [1920, 1080], 'ext': 'mp4'},
]

image_resolutions = [
    # For display in list
    {'name': 'thumb', 'wh': [640, 480], 'ext': 'jpg', 'update': False},
    # Half-screen
    {'name': '720', 'wh': [1280, 720], 'ext': 'jpg'},
    # For fullscreen use
    {'name': '1080', 'wh': [1920, 1080], 'ext': 'jpg'},
]

# Not implemented yet
audio_resolutions = [
    {'name': 'std', 'max-bitrate': 128, 'ext': 'm4a'}
]
