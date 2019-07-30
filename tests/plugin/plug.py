from precept import Plugin


class MyPlugin(Plugin):

    async def setup(self, application):
        application.plugged = 'PLUGGED'


plugin = MyPlugin()
