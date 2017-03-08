import pytest
import requests
from nameko.rpc import rpc
from nameko.testing.services import worker_factory
from nameko_sqlalchemy import Session


class MsgbotTelegramService:
    name = "msgbot_telegram_service"


