import os
import re
import asyncio
import tempfile
import os.path as osp
import asyncio.subprocess
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

from ..utils import getLogger
from .mediaconfig import *

logger = getLogger('transcode.transcoder')


class Transcoder:
    "Nice object-oriented style transcoder implementation"
    @classmethod
    async def create(cls, loop=None):
        tc = cls()
        tc.loop = loop or asyncio.get_event_loop()
        # Call this method to allow subclasses to initialize specific things, e.g. ThreadPoolExecutor
        tc.init()
        tc.media_root = osp.abspath(os.environ['AT_MEDIA_ROOT'])
        tc.proc = None
        tc.m = None
        return tc

    def init(self):
        "Can be overridden in subclass"
        pass

    async def consume(self, pq, resq):
        "Priority queue for input, result queue for output"
        self.pq = pq
        logger.debug("%s consuming from queue", self)
        while True:
            # Store on self for retrieval on unexpected exit
            self.m = await self.pq.get()
            logger.debug("Consumed from queue: %s", self.m)
            try:
                media = self.m[2]
                media_transcoded = media.copy()
                conf = self.m[3]
                media_transcoded['update'] = conf.get('update', True)
                src = media['path']
                # Paths can be absolute or relative to media root
                if not osp.isabs(src):
                    src = osp.abspath(osp.join(os.environ['AT_MEDIA_ROOT'], media['path']))
                tmpdir = tempfile.mkdtemp(prefix='transcode-')
                # Construct entire filename
                n, ext = osp.splitext(osp.basename(src))
                # Make <tmpdir>/<originalname>-video.<newext>
                dest_tmp = osp.join(tmpdir, '{}-{}.{}'.format(n, conf['name'], conf['ext']))
                # Returns dict with possible keys: timestamp, duration, width, height, log
                logger.debug("Starting transcode for %s with conf %s", media, conf)
                stat = await self.transcode(src, dest_tmp, conf)
                logger.debug("Finished transcode for %s with conf %s", media, conf)
                media_transcoded.update(stat)
                # Move from temp folder to e.g. <media_root>/video/<filename>
                dest_perm = osp.join(self.media_root, media['type'], osp.basename(dest_tmp))
                # Make dir if non-existent
                os.makedirs(osp.dirname(dest_perm), exist_ok=True)
                # Use replace instead of rename to overwrite target
                os.replace(dest_tmp, dest_perm)
                # Make path relative to media root and store in media obj
                media_transcoded['path'] = osp.relpath(dest_perm, self.media_root)
                media_transcoded['conf_name'] = conf['name']
                # Put in result queue
                await resq.put(media_transcoded)
            except Exception:
                logger.exception("Error in transcoding process for media %s", self.m)
            # Let queue counter decrease
            self.pq.task_done()
            self.m = None

    def stop(self):
        "Stops any process, returns any unfinished business or None"
        if self.proc:
            self.proc.kill()
        return self.m

    async def transcode(self, *args, **kwargs):
        raise Warning("Method not implemented")

    async def run_subprocess(self, cmd_list, ignore_returncode=False):
        "Run a subprocess as coroutine"
        logger.info("Running command > {}".format(' '.join(cmd_list)))
        # TODO: Use asyncio.wait_for to specify a timeout
        proc = await asyncio.create_subprocess_exec(
            *cmd_list,
            # Capture stdout, stderr to avoid dirty logs
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        # Save proc to be able to end it
        self.proc = proc
        await proc.wait()
        # Process is over now
        self.proc = None
        stdout, stderr = await proc.communicate()
        if proc.returncode and not ignore_returncode:
            raise Warning("Return code {} is nonzero, stdout={} stderr={}".format(proc.returncode, stdout, stderr))
        # stdout is bytes, conver to string for json serialization
        return stderr.decode('utf-8')


class VidThumbTranscoder(Transcoder):
    async def transcode(self, src, dest, conf):
        "Generate thumbnail for video"
        cmd = ("ffmpeg -y -i {src} -vf "
               "thumbnail,scale=w='min(iw,{conf[wh][0]})':h='min(ih,{conf[wh][1]})':force_original_aspect_ratio=decrease "
               "-frames:v 1 -an {dest}").format(
            src=src, dest=dest, conf=conf)
        stdout = await self.run_subprocess(cmd.split())
        width, height = None, None
        return {'width': width, 'height': height, 'log': stdout}


class VidTranscoder(Transcoder):
    async def transcode(self, src, dest, conf, cutfromto=None):
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
        # TODO: Find src file timestamp, duration, resolution
        # TODO: Only transcode if resolution smaller than original
        cut = "-ss {cut[0]} -to {cut[1]}".format(cut=cutfromto) if cutfromto else ''
        # See https://trac.ffmpeg.org/wiki/Scaling%20(resizing)%20with%20ffmpeg for info on keeping aspect ratio
        cmd = ("ffmpeg -y -i {src} {cut} -c:v libx264 -movflags +faststart -vf "
               "scale=w='min(iw,{conf[wh][0]})':h='min(ih,{conf[wh][1]})':force_original_aspect_ratio=decrease -crf 26 -c:a copy {dest}"
                .format(src=src, cut=cut, conf=conf, dest=dest))
        stdout = await self.run_subprocess(cmd.split())
        # TODO: Find dest file width, height
        return {'timestamp': None, 'duration': None, 'width': None, 'height': None, 'log': stdout}


class ImageTranscoder(Transcoder):
    def init(self):
        # Just one thread, make concurrent by instantiating multiple ImageTranscoder classes
        self.executor = ThreadPoolExecutor(1)

    def _transcode(self, src, dest, conf):
        """
        Run this blocking function in ThreadPoolExecutor.
        Not sure how and when the termination signal propagates to child threads.
        """
        logger.debug("Running _transcode")
        im = Image.open(src)
        newim = im.copy()
        # Modifies in-place
        newim.thumbnail(conf['wh'])
        newim.save(dest, format='JPEG')
        # TODO: Find src file timestamp
        # TODO: Find dest file width/height
        return {'timestamp': None, 'width': None, 'height': None}

    async def transcode(self, *args):
        # Avoid blocking eventloop
        logger.debug("Running transcode in ThreadPoolExecutor")
        return await self.loop.run_in_executor(self.executor, self._transcode, *args)


class AudioTranscoder(Transcoder):
    async def transcode(self, src, dest, conf):
        "Keep same bitrate preferably"
        # Ignore returncode as ffmpeg will show info but exit saying it needs output file
        info = await self.run_subprocess(['ffmpeg', '-i', src], ignore_returncode=True)
        bitrate = 1000
        try:
            res = re.search('bitrate:\s*([\d\.]+)\s*kb\/s', info)
            bitrate = int(res.group(1))
        except (AttributeError, ValueError) as e:
            logger.warning("Could not find audio bitrate in ffmpeg info string: %s\nError: %s", info, str(e))
        bitrate = min(bitrate, conf.get('max-bitrate', 128))
        # Encode as AAC, add some flags to move metadata to start of file for fast playback start
        log = await self.run_subprocess(
            ['ffmpeg', '-i', src, '-c:a', 'aac', '-movflags', '+faststart', '-b:a', '{:.0f}k'.format(bitrate), dest])
        duration = None
        try:
            res = re.search('Duration:\s*(\d+):(\d+):([\d\.]+)', log)
            # The simplicity, I love it!
            duration = float(res.group(1))*3600 + float(res.group(2))*60 + float(res.group(3))
        except (AttributeError, ValueError):
            logger.warning("Could not find duration of audio file in log %s", log)
        return {'timestamp': None, 'duration': duration, 'log': log}
