from precept import Precept


def test_plugin():
    class PluginTest(Precept):
        pass

    app = PluginTest()
    # pylint: disable=no-member
    assert app.plugged == 'PLUGGED'
