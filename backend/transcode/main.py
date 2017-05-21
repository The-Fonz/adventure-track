import asyncio
from itertools import count
cnt = count()

from ..utils import BackendAppSession, getLogger
from .transcoder import VidThumbTranscoder, VidTranscoder, ImageTranscoder, AudioTranscoder
from .mediaconfig import video_thumb_resolutions, video_resolutions, image_resolutions, audio_resolutions

logger = getLogger('transcode.main')


class TranscodeComponent(BackendAppSession):

    async def onJoin(self, details):
        logger.info("session joined")

        # Set up queues
        queue_video_thumb = asyncio.PriorityQueue()
        queue_video = asyncio.PriorityQueue()
        queue_image = asyncio.PriorityQueue()
        queue_audio = asyncio.PriorityQueue()

        # Remember for when shutting down
        self.queues = [queue_video_thumb, queue_video, queue_image, queue_audio]

        queue_results = asyncio.Queue()
        self.queue_results = queue_results

        # Note: can set up multiple queue consumers per queue if needed
        vtt = await VidThumbTranscoder.create()
        vt  = await VidTranscoder.create()
        it  = await ImageTranscoder.create()
        at  = await AudioTranscoder.create()

        # Remember for when shutting down
        self.transcoders = [vtt, vt, it, at]

        # Schedule all queue consumers
        tfs = []
        tfs += [asyncio.ensure_future(vtt.consume(queue_video_thumb, queue_results))]
        tfs += [asyncio.ensure_future(vt.consume(queue_video, queue_results))]
        tfs += [asyncio.ensure_future(it.consume(queue_image, queue_results))]
        tfs += [asyncio.ensure_future(at.consume(queue_audio, queue_results))]
        # Remember so we can wait on them to finish when cleaning up
        self.transcoder_futures = tfs

        async def transcode(m):

            async def put_queue(q, resolutions):
                for i, res in enumerate(resolutions):
                    # Priority from 1 to len(resolutions)
                    # Use unique count to make sure never to compare dict m or res when i is equal
                    await q.put((i+1, next(cnt), m, res))
            # Put tasks on queues
            mt = m['type']
            if mt == 'video':
                await put_queue(queue_video_thumb, video_thumb_resolutions)
                await put_queue(queue_video, video_resolutions)
            elif mt == 'image':
                await put_queue(queue_image, image_resolutions)
            elif mt == 'audio':
                await put_queue(queue_audio, audio_resolutions)
            else:
                raise Warning("Media type not recognized: %s", m)

        self.register(transcode, 'at.transcode.transcode')

        # Start publishing results queue
        while True:
            m = await queue_results.get()
            logger.info("Result of transcode: %s", m)
            # Exit signal
            if m == None:
                queue_results.task_done()
                break
            m = dict(m, original=False)
            self.publish('at.transcode.finished', m)
            queue_results.task_done()

    async def cleanup(self, loop):
        # TODO: Clean up, this code works but is pretty unwieldy
        logger.info("Cleaning up, stopping transcodes and saving non-completed ones...")
        unfinished_business = []
        for t in self.transcoders:
            m = t.stop()
            unfinished_business.append(m)
        for f in self.transcoder_futures:
            f.cancel()
        # Empty all queues
        unfinished_queues = []
        for q in self.queues:
            try:
                # Empty entire queue
                while True:
                    unfinished_queues.append(q.get_nowait())
            except asyncio.QueueEmpty:
                pass

        unsent_results = []
        try:
            while True:
                unsent_results.append(self.queue_results.get_nowait())
        except asyncio.QueueEmpty:
            pass
        # Should save unfinished business to file or db, and check on startup
        # For now just log err
        # unfinished_business can contain Nones
        if any(unfinished_business) or unfinished_queues or unsent_results:
            logger.error("Unfinished business! Unfinished queues: %s\n"
                         "Transcodes that failed because of exit: %s\n"
                         "Unsent results: %s",
                         unfinished_queues, unfinished_business, unsent_results)
        logger.info("Waiting for onJoin to exit...")
        # Exit signal
        await self.queue_results.put(None)
        logger.debug("Waiting for transcoders to exit...")
        await asyncio.wait(self.transcoder_futures)


if __name__=="__main__":
    TranscodeComponent.run_forever()
