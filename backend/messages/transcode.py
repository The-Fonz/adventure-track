import os
import asyncio
import asyncio.subprocess

from PIL import Image


async def run(cmd):
    "Run a subprocess as coroutine"
    print("Running command > {}".format(cmd))
    # TODO: Use asyncio.wait_for to specify a timeout
    proc = await asyncio.create_subprocess_exec(
        *cmd.split(),
        # Capture stdout, stderr to avoid dirty logs
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await proc.wait()
    if proc.returncode:
        stdout, stderr = await proc.communicate()
        raise Warning("Return code {} is nonzero, stdout={} stderr={}".format(proc.returncode, stdout, stderr))


async def transcode(q, mediatype):
    "Consume transcode tasks from PriorityQUeue"
    if mediatype not in {'video', 'image', 'audio'}:
        raise Warning("Media type {} not recognized".format(mediatype))
    while True:
        m = await q.get()
        # m[0] is priority value
        fut = m[1]
        # Stop signal
        if fut == None:
            q.task_done()
            break
        original = m[2]
        res = m[3]
        # Convert only from slicevid[0] to slicevid[1] seconds
        slicevid = m[4]
        # TODO: Different folder
        basefn = os.path.splitext(original)[0]
        if mediatype == 'video':
            if 'thumb' in res['type']:
                versions = await video_thumb(original, basefn, res)
            else:
                versions = await video_ffmpeg(original, basefn, res, cutfrom=slicevid[0], cutto=slicevid[1])
        elif mediatype == 'image':
            versions = await convert_image(original, basefn, res)
        elif mediatype == 'audio':
            raise Warning("Transcoding audio not implemented")
        res = {
            'mediatype': 'video',
            'versions': versions
        }
        fut.set_result(res)
        q.task_done()


async def video_thumb(vidfile, basefn, wh):
    "Generate thumbnail for video"
    # Create thumbnail
    thumbfn = basefn + '-thumb.test.jpg'
    cmd = "ffmpeg -y -i {input} -vf thumbnail,scale=640:360 -frames:v 1 {output}".format(
        input=vidfile, output=thumbfn)
    await run(cmd)
    return {'thumb': thumbfn}


async def video_ffmpeg(vidfile, basefn, res, cutfrom=None, cutto=None):
    """

    Improvement ideas:
     - Normalize audio using https://github.com/slhck/ffmpeg-normalize or, better yet,
       demux audio and use *sox* for compression, normalization, then remux
     - GIF summary, see https://superuser.com/questions/556029/how-do-i-convert-a-video-to-gif-using-ffmpeg-with-reasonable-quality/556031#556031 and https://superuser.com/questions/538112/meaningful-thumbnails-for-a-video-using-ffmpeg

    :param input:   Video file
    :param cutfrom: Skip to this time [seconds]
    :param cutto:   Until this time [seconds]
    :return:
    """
    # TODO: copy audio stream if correct format, otherwise transcode
    outfn = basefn + "-{}.test.mp4".format(res['type'])
    scale = "{0}:{1}".format(*res['wh'])
    cmd = "ffmpeg -y -i {input} ".format(input=vidfile)
    if cutfrom != None and cutto != None:
        cmd += "-ss {} -to {} ".format(cutfrom, cutto)
    cmd += "-c:v libx264 -vf scale={scale} -crf 26 -c:a copy {output}".format(output=outfn, scale=scale)
    await run(cmd)
    return {res['type']: outfn}


def convert_image(input, basefn, res):
    im = Image.open(input)
    newim = im.copy()
    # Modifies in-place
    newim.thumbnail(res['wh'])
    # Make new filename
    impath = basefn + '-{}.jpg'.format(sizename)
    newim.save(impath, format='JPEG')
    return {res['type']: impath}


def convert_audio():
    # TODO. Best is not to convert if not necessary,
    # as lossy -> lossy audio conversion is not the best
    pass