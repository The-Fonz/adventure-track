import os
import uuid
import json
import asyncio
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.ext.filters import Filters
from autobahn.wamp.exception import ApplicationError

from .replies import MSGS
from ..utils import getLogger

logger = getLogger('telegrambot.bot')


def main(wampsess, loop):
    "Telegram bot runs in separate thread"
    try:
        token = os.environ['AT_TELEGRAM_TOKEN'].strip()
    except KeyError:
        raise KeyError("Please define token as env var")

    def runcoro(coro):
        return asyncio.run_coroutine_threadsafe(coro, loop)

    updater = Updater(token=token)

    def start(bot, update, args):
        cid = update.message.chat_id
        telegram_user = update.message.from_user
        telegram_id = telegram_user.id
        bot.sendMessage(chat_id=cid, text=MSGS['welcome'])
        # Check if user is linked already
        fut = runcoro(wampsess.db.get_link(telegram_id=telegram_id))
        already_linked = fut.result()
        if already_linked:
            bot.sendMessage(chat_id=cid, text=MSGS['already_auth'])
        # Not linked, we need to authenticate
        else:
            # Check if user followed an auth link with "<user_auth_code>"
            if len(args):
                try:
                    user_auth_code = args
                except ValueError:
                    bot.sendMessage(chat_id=cid, text=MSGS['authcode_invalid'])
                    return
                # Returns a future
                auth = wampsess.call('at.users.get_user_id_by_authcode', user_auth_code)
                # Must specify timeout!
                auth = runcoro(asyncio.wait_for(auth, 2))
                user_id = auth.result()
                # Is falsy if not successful
                if user_id:
                    # Add link
                    runcoro(wampsess.db.insertlink(user_id=user_id, telegram_id=telegram_id))
                    bot.sendMessage(chat_id=cid, text=MSGS['authcode_successful'])
                else:
                    bot.sendMessage(chat_id=cid, text=MSGS['authcode_failed'])
                    logger.warning("Auth code failed, is %s", auth)
            else:
                bot.sendMessage(chat_id=cid, text=MSGS['please_auth'])

    def onmsg(bot, update):
        mediapath = os.path.abspath(os.path.normpath(os.environ['AT_MEDIA_ROOT']))
        vid_root = os.path.join(mediapath, 'video_original')
        img_root = os.path.join(mediapath, 'image_original')
        aud_root = os.path.join(mediapath, 'audio_original')
        # Make dirs if non-existent
        os.makedirs(vid_root, exist_ok=True)
        os.makedirs(img_root, exist_ok=True)
        os.makedirs(aud_root, exist_ok=True)
        cid = update.message.chat_id
        telegram_user = update.message.from_user
        telegram_id = telegram_user.id
        # Check if user is linked already
        fut = runcoro(wampsess.db.get_link(telegram_id=telegram_id))
        link = fut.result()
        if not link:
            bot.sendMessage(chat_id=cid, text=MSGS['please_auth'])
            return
        if not update.message:
            logger.info("No update.message, maybe update?")
            return

        t = update.message
        msg = dict()
        msg['text'] = t.text or t.caption
        try:
            msg['telegram_message'] = json.dumps(t.to_dict())
        except Exception:
            pass
        # Serialize to ISO format so WAMP can send it over the wire
        msg['timestamp'] = t.date.isoformat()
        msg['user_id'] = link['user_id']
        if t.video:
            vid = t.video
            reply = "Received vid of {}s resolution {}x{} mimetype {} filesize {:.2f}MB".format(vid.duration, vid.width, vid.height, vid.mime_type, vid.file_size/1E6)
            bot.sendMessage(chat_id=cid, text=reply)
            vidfile = bot.get_file(vid.file_id)
            # Get original extension and remove leading dot (if any)
            ext = os.path.splitext(vidfile.file_path)[1].replace('.','')
            fn = "{}_{}.{}".format(msg['timestamp'], uuid.uuid4(), ext)
            vidpath = os.path.join(vid_root, fn)
            vidfile.download(custom_path=vidpath)
            # Save path relative to media root, to avoid issues when moving stuff around
            msg['video_original'] = os.path.relpath(vidpath, start=mediapath)
            logger.debug("Saved video as {}".format(vidpath))
        # Is PhotoSize array
        if t.photo:
            # Choose largest (is usually at the end, but scan all just to be sure)
            maxwidth = 0
            for p in t.photo:
                if p.width > maxwidth:
                    img = p
            bot.sendMessage(chat_id=cid, text="Received {}x{} photo of {:.2f}MB".format(img.width, img.height, img.file_size/1E6))
            imgfile = bot.get_file(img.file_id)
            ext = os.path.splitext(imgfile.file_path)[1].replace('.', '')
            fn = "{}_{}.{}".format(msg['timestamp'], uuid.uuid4(), ext)
            imgpath = os.path.join(img_root, fn)
            imgfile.download(custom_path=imgpath)
            msg['image_original'] = os.path.relpath(imgpath, start=mediapath)
            logger.debug("Saved img as {}".format(imgpath))
        if t.audio or t.voice:
            if t.voice:
                avmsg = t.voice
                typ = 'voice'
            elif t.audio:
                avmsg = t.audio
                typ = 'audio'
            file_id = avmsg.file_id
            reply = "Received {} message of {}s mimetype {} filesize {:.2f}MB".format(typ, avmsg.duration,
                                                                                                avmsg.mime_type,
                                                                                                avmsg.file_size / 1E6)
            bot.sendMessage(chat_id=cid, text=reply)
            audfile = bot.get_file(file_id)
            # Get original extension and remove leading dot (if any)
            ext = os.path.splitext(audfile.file_path)[1].replace('.', '')
            fn = "{}_{}.{}".format(msg['timestamp'], uuid.uuid4(), ext)
            audpath = os.path.join(aud_root, fn)
            audfile.download(custom_path=audpath)
            # Save path relative to media root, to avoid issues when moving stuff around
            msg['audio_original'] = os.path.relpath(audpath, start=mediapath)
            logger.debug("Saved audio as {}".format(audpath))
        if t.location:
            # TODO: Send location to location service
            logger.debug(t.location)
            bot.sendMessage(chat_id=cid, text="Location not supported yet")
        try:
            fut = wampsess.call('at.messages.insertmsg', msg)
            fut = runcoro(asyncio.wait_for(fut, 2))
            logger.debug("Message inserted")
            bot.sendMessage(chat_id=cid, text="Your message was successfully saved")
        except (ApplicationError, asyncio.TimeoutError):
            logger.exception("Failed inserting message")
            bot.sendMessage(chat_id=cid, text="Your message could not be saved. We've been notified of this issue. Please try again later.")


    start_handler = CommandHandler('start', start, pass_args=True)
    message_handler = MessageHandler(Filters.all, onmsg)
    updater.dispatcher.add_handler(start_handler)
    updater.dispatcher.add_handler(message_handler)

    # Non-blocking
    updater.start_polling(timeout=60)

    return updater


if __name__=="__main__":
    main()
