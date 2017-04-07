import os
import uuid
import asyncio
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.ext.filters import Filters

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
            # Check if user followed an auth link with "<user_id_hash> <user_auth_code>"
            if len(args):
                try:
                    user_id_hash, user_auth_code = args
                except ValueError:
                    bot.sendMessage(chat_id=cid, text=MSGS['authcode_invalid'])
                    return
                # Returns a future
                auth = wampsess.call('at.users.check_user_authcode', user_id_hash, user_auth_code)
                # Must specify timeout!
                auth = runcoro(asyncio.wait_for(auth, 2))
                auth = auth.result()
                if auth == True:
                    # Retrieve true user id
                    fut = wampsess.call('at.users.get_user_id_by_hash', user_id_hash)
                    fut = runcoro(asyncio.wait_for(fut, 2))
                    user_id = fut.result()
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
        # Make dirs if non-existent
        os.makedirs(vid_root, exist_ok=True)
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
        # Serialize to ISO format so WAMP can send it over the wire
        msg['timestamp'] = t.date.isoformat()
        msg['user_id'] = link['user_id']
        if t.video:
            vid = t.video
            vidfile = bot.get_file(vid.file_id)
            reply = "Received vid of {}s resolution {}x{} mimetype {} filesize {:.2f}MB".format(vid.duration, vid.width, vid.height, vid.mime_type, vid.file_size/1E6)
            logger.debug(t.video)
            # Get original extension and remove leading dot (if any)
            ext = os.path.splitext(vidfile.file_path)[1].replace('.','')
            bot.sendMessage(chat_id=cid, text=reply)
            fn = "{}_{}.{}".format(msg['timestamp'], uuid.uuid4(), ext)
            vidpath = os.path.join(vid_root, fn)
            vidfile.download(custom_path=vidpath)
            # Save path relative to media root, to avoid issues when moving stuff around
            msg['video_original'] = os.path.relpath(vidpath, start=mediapath)
            logger.debug("Saved video as {}".format(vidpath))
        if t.photo:
            logger.debug(t.photo)
            bot.sendMessage(chat_id=cid, text="Received photo")
        if t.audio or t.voice:
            logger.debug(t.audio)
            logger.debug(t.voice)
            bot.sendMessage(chat_id=cid, text="Audio and voice not supported yet")
        if t.location:
            logger.debug(t.location)
            bot.sendMessage(chat_id=cid, text="Location not supported yet")
        fut = wampsess.call('at.messages.insertmsg', msg)
        fut = runcoro(asyncio.wait_for(fut, 2))
        bot.sendMessage(chat_id=cid, text="Your message was successfully saved")
        logger.debug("Message inserted")


    start_handler = CommandHandler('start', start, pass_args=True)
    message_handler = MessageHandler(Filters.all, onmsg)
    updater.dispatcher.add_handler(start_handler)
    updater.dispatcher.add_handler(message_handler)

    # Non-blocking
    updater.start_polling(timeout=60)

    return updater


if __name__=="__main__":
    main()
