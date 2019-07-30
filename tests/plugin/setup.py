from setuptools import setup

setup(
    name='precept_plugin_test',
    entry_points={
        'plugin_test.plugins': ['my_plugin = plug:plugin']
    }
)
