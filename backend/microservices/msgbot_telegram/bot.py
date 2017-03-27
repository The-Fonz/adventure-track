import os
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from telegram.ext import Updater, CommandHandler, MessageHandler

# Can be translated at some point
MSGS = {
    'welcome': "Hi there and welcome to AdventureTrack, the platform that lets you share the story of your adventure.",
    'please_auth': "Your Telegram ID is not known to us. Please follow the link in your email.",
    'already_auth': "Your Telegram ID has already been linked.",
    'authcode_successful': "Your Telegram ID has successfully been linked to your AdventureTrack account.",
    'authcode_failed': "We could not verify this authentication code."
}


def check_auth(telegram_id):
    return False


def authenticate(telegram_id, authcode):
    return False


def main():
    "Telegram bot runs in separate thread"
    updater = Updater(token=os.environ['AT_TELEGRAM_ADVENTURETRACKBOT_TOKEN'])

    def start(bot, update, args):
        cid = update.message.chat_id
        uid = update.message.from_user
        bot.sendMessage(chat_id=cid, text=MSGS['welcome'])
        # Check if user is linked already
        if check_auth(uid):
            bot.sendMessage(chat_id=cid, text=MSGS['already_auth'])
        # Not linked, we need to authenticate
        else:
            # Check if user followed an auth link with auth code as first arg
            if len(args):
                authcode = args[0].strip()
                if authenticate(uid, authcode):
                    bot.sendMessage(chat_id=cid, text=MSGS['authcode_successful'])
                else:
                    bot.sendMessage(chat_id=cid, text=MSGS['authcode_failed'])
                    # TD: Send Sentry error
            else:
                bot.sendMessage(chat_id=cid, text=MSGS['please_auth'])

    start_handler = CommandHandler('start', start, pass_args=True)
    updater.dispatcher.add_handler(start_handler)

    # Non-blocking
    updater.start_polling()


if __name__=="__main__":
    main()
