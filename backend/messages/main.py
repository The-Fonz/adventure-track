from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from .db import Db

class MessagesComponent(ApplicationSession):
    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)
        print("component created")

    def onConnect(self):
        print("transport connected")
        self.join(self.config.realm)

    def onChallenge(self, challenge):
        print("authentication challenge received")

    async def onJoin(self, details):
        print("session joined")

        db = Db()

        def fetchmsgs(user_id):
            return db.getmsgs(user_id)

        self.register(fetchmsgs, 'com.messages.fetchmsgs')

        def insertmsg(msgjson):
            # Save in db
            pass

        # register insert msg

        # Publish on insert message

    def onLeave(self, details):
        print("session left")

    def onDisconnect(self):
        print("transport disconnected")


if __name__=="__main__":
    runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")
    runner.run(MessagesComponent)
