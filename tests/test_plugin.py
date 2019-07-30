from precept import Precept


def test_plugin():
    class PluginTest(Precept):
        pass

    app = PluginTest()
    assert app.plugged == 'PLUGGED'
