video_resolutions = [
    # Priority ordering: first one gets encoded, then the rest
    {'type': 'thumb', 'wh': [640, 360]},
    {'type': '360', 'wh': [640, 360]},
    {'type': '720', 'wh': [1280, 720]},
    {'type': '1080', 'wh': [1920, 1080]},
]

image_resolutions = [
    # For display in list
    {'type': 'thumb', 'wh': [640, 480]},
    # Half-screen
    {'type': '720', 'wh': [1280, 720]},
    # For fullscreen use
    {'type': '1080', 'wh': [1920, 1080]},
]
