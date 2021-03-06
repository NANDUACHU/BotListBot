# -*- coding: utf-8 -*-
import threading
import time
from logzero import logger as log
from telegram import Bot as TelegramBot
from telegram.ext import Updater
from telegram.utils.request import Request

import appglobals
import routing
import settings
import util
from components import admin, basic
from lib.markdownformatter import MarkdownFormatter


# def setup_logger():
#     logger = logging.getLogger('botlistbot')
#     logger.setLevel(logging.INFO)
#
#     console_formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
#     file_formatter = logging.Formatter(
#         "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
#
#     # create console handler and set level to info
#     handler = logging.StreamHandler()
#     handler.setLevel(logging.INFO)
#     handler.setFormatter(console_formatter)
#     logger.addHandler(handler)
#
#     # create debug file handler and set level to debug
#     handler = logging.FileHandler(settings.DEBUG_LOG_FILE, "w", encoding=None, delay="true")
#     handler.setLevel(logging.DEBUG)
#     handler.setFormatter(file_formatter)
#     logger.addHandler(handler)


class BotListBot(TelegramBot):
    def send_notification(self, message, **kwargs):
        self.send_message(
            settings.BOTLIST_NOTIFICATIONS_ID,
            util.escape_markdown(message),
            parse_mode='markdown',
            timeout=20,
            **kwargs
        )
        log.info(message)


# class BotListDispatcher(Dispatcher):
#     def process_update(self, update):
#         user = User.from_update(update)
#         update.callback_manager = CallbackManager(appglobals.redis, user)
#         update.callback_data = {}
#         return super(BotListDispatcher, self).process_update(update)


def main():
    # Start API
    # thread = threading.Thread(target=botlistapi.start_server)
    # thread.start()

    botchecker_context = {}

    bot_token = str(settings.BOT_TOKEN)

    botlistbot = BotListBot(bot_token, request=Request(
        read_timeout=8,
        connect_timeout=7,
        con_pool_size=settings.WORKER_COUNT + 4
    ))
    updater = Updater(
        bot=botlistbot,
        workers=settings.WORKER_COUNT,
    )
    # updater.dispatcher = BotListDispatcher(
    #     botlistbot,
    #     updater.update_queue,
    #     job_queue=updater.job_queue,
    #     workers=settings.WORKER_COUNT,
    #     exception_event=threading.Event())

    botlistbot.formatter = MarkdownFormatter(updater.bot)

    # Get the dispatcher to on_mount handlers
    dp = updater.dispatcher

    # message_queue = MessageQueue()
    # message_queue._is_messages_queued_default = True
    # updater.bot._is_messages_queued_default = True
    # updater.bot._msg_queue = message_queue
    # updater.bot.queuedmessage = messagequeue.queuedmessage
    # updater.bot.send_message = updater.bot.queuedmessage(updater.bot.send_message)

    bot_checker = None

    if settings.USE_USERBOT:
        from components.userbot import botchecker
        from components.userbot.botchecker import BotChecker

        bot_checker = BotChecker(
            event_loop=appglobals.loop,
            session_name=settings.USERBOT_SESSION,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            phone_number=settings.USERBOT_PHONE,
        )

        def start_userbot():
            log.info("Starting Userbot...")
            bot_checker.start()
            log.info("Userbot running.")

            if settings.RUN_BOTCHECKER:
                botchecker_context.update(
                    {'checker': bot_checker, 'stop': threading.Event()})
                updater.job_queue.run_repeating(
                    botchecker.ping_bots_job,
                    context=botchecker_context,
                    first=1.5,
                    interval=settings.BOTCHECKER_INTERVAL
                )

        threading.Thread(target=start_userbot, name="BotChecker").start()

    routing.register(dp, bot_checker)
    basic.register(dp)

    updater.job_queue.run_repeating(admin.last_update_job, interval=3600 * 24)
    updater.start_polling()

    log.info('Listening...')
    updater.bot.send_message(settings.ADMINS[0], "Ready to rock", timeout=10)

    # Idling
    updater.idle()
    updater.stop()
    log.info('Disconnecting...')


if __name__ == '__main__':
    main()
