from PIL import Image
import subprocess

from .mediaconfig import video_versions, audio_versions, image_versions


def submit():
    "Update listeners with media info"
    # TODO: RPC call to messages.service.add_media_detail
    pass


def convert_video():
    # TODO
    pass


def convert_audio():
    # TODO
    pass


def convert_image(message_id, orifilename):
    "Convert to all sizes specified in config"
    # TODO: test
    im = Image.open(orifilename)
    out = {}
    for sizename, size in image_versions:
        newim = im.copy()
        # Modifies in-place
        newim.thumbnail(size)
        # Make new filename
        # TODO: use pathconfig
        impath = ''
        im.save(impath, format='JPEG')
        # "<sizenamekey>": "<staticpath>"
        out[sizename] = impath
    # New info back into db
    submit(message_id, out)
