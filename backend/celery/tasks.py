import os

from PIL import Image
import subprocess

from .mediaconfig import video_resolutions, image_resolutions


def update_video_versions():
    "Update listeners with media info"
    # TODO: RPC call to messages.service.add_media_detail
    pass


def run(cmd):
    p = subprocess.run(cmd.split())
    p.check_returncode()


def convert_video(input, cutfrom=None, cutto=None):
    video_versions = {}
    # TODO: Normalize audio using https://github.com/slhck/ffmpeg-normalize
    # Path without extension
    basefn = os.path.splitext(input)[0]
    # Create thumbnail
    thumbfn = basefn + '-thumb.jpg'
    cmd = "ffmpeg -y -i {input} -vf thumbnail,scale=640:360 -frames:v 1 {output}".format(input=input, output=thumbfn)
    run(cmd)
    video_versions["thumb"] = thumbfn

    # GIF summary, see https://superuser.com/questions/556029/how-do-i-convert-a-video-to-gif-using-ffmpeg-with-reasonable-quality/556031#556031
    # TODO: Extract meaningful frames first using
    # https://superuser.com/questions/538112/meaningful-thumbnails-for-a-video-using-ffmpeg
    # with tempfile.TemporaryDirectory() as tmpdirname:
    #     "ffmpeg -y -ss 30 -t 3 -i input.flv -vf fps=10,scale=320:-1:flags=lanczos,palettegen palette.png"

    # Convert to all desired formats
    # TODO: copy audio stream if correct format, otherwise transcode
    for resname, res in video_resolutions.items():
        outfn = basefn + "-{}.mp4".format(resname)
        scale = "{0}:{1}".format(*res)
        cmd = "ffmpeg -y -i {input} ".format(input=input)
        if cutfrom!=None and cutto!=None:
            cmd += "-ss {} -to {} ".format(cutfrom, cutto)
        cmd += "-c:v libx264 -vf scale={scale} -crf 26 -c:a copy {output}".format(output=outfn, scale=scale)
        run(cmd)
        video_versions[resname] = outfn
    return video_versions


def convert_audio():
    # TODO. Best is not to convert if not necessary,
    # as lossy -> lossy audio conversion is not the best
    pass


def convert_image(input):
    "Convert to all sizes specified in config"
    im = Image.open(input)
    image_versions = {}
    for sizename, size in image_resolutions.items():
        newim = im.copy()
        # Modifies in-place
        newim.thumbnail(size)
        # Make new filename
        impath = os.path.splitext(input)[0] + '-{}.jpg'.format(sizename)
        newim.save(impath, format='JPEG')
        # "<sizenamekey>": "<staticpath>"
        image_versions[sizename] = impath
    # New info back into db
    # TODO: update_video_versions()
    return image_versions
