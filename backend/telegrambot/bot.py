import os
import asyncio
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from telegram.ext import Updater, CommandHandler, MessageHandler

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

    start_handler = CommandHandler('start', start, pass_args=True)
    updater.dispatcher.add_handler(start_handler)

    # Non-blocking
    updater.start_polling()


if __name__=="__main__":
    main()
