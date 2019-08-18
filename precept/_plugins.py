class Plugin:
    """
    Plugin's are automatically added to a precept
    application upon installation.

    Set the entry point in setup to register the plugin:

        entry_point = {'{app_name}.plugins': ['plugin = my_plugin:plugin']}
    """
    name: str = ''

    async def setup(self, application):  # pragma: no cover
        """
        Setup the plugin

        :param application: The running precept application.
        :type application: precept.Precept
        :return:
        """
        raise NotImplementedError
