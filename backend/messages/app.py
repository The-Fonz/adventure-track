from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner


class MessagesComponent(ApplicationSession):
    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)
        print("component created")

    def onConnect(self):
        print("transport connected")
        self.join(self.config.realm)

    def onChallenge(self, challenge):
        print("authentication challenge received")

    def onJoin(self, details):
        print("session joined")

        def callback(*args):
            print("Callback called with args {}".format(args))
            return 'hi'

        self.register(callback, 'com.messages.getall')

    def onLeave(self, details):
        print("session left")

    def onDisconnect(self):
        print("transport disconnected")


if __name__=="__main__":
    runner = ApplicationRunner(url="ws://localhost:8080/ws", realm="realm1")
    runner.run(MessagesComponent)
