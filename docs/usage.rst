*****
Usage
*****

Install
=======

Install with pip:

``pip install precept``

Write async console applications
================================

Precept comes with many classes and functions to build async applications,
the main class consist of :py:class:`~precept.Precept` which you
subclass to create your application. Methods of this class decorated with
:py:class:`~precept.Command` are automatically added as sub command to the
application.

Basic example defining an echo command:

.. code-block:: python

    from precept import Precept, Command, Argument

    class App(Precept):
        @Command(
            Argument('name'),
        )
        async def echo(self, name):
            print(f'Hello {name}')

Then call from the terminal like this: ``app echo bob`` -> Prints ``Hello bob``

.. note::

    If no command was supplied, ``main`` will be called instead.

Starting the application
------------------------

To create a console application from a precept app you need to add function
that will create an instance of your precept subclass and call start
then add it to ``setup.py``.


:app.py:
    .. code-block:: python

        def cli():
            App().start()

:setup.py:
    .. code-block:: python

        from setuptools import setup

        setup(
            entry_points: {
                'console_scripts': ['cli = app:cli']
            }
        )

*You can also create a global instance of the app and assign the entrypoint to it's start method*

Configs
=======

Precept comes with a built in config system, create a subclass of
:py:class:`~precept.Config` with members as config. You can nest classes
definition to create sub sections.

Example
-------

.. code-block:: python

    from precept import Config, Nestable, ConfigProperty

    class MyConfig(Config):
        my_config = ConfigProperty(comment='comment', config_type=str)

        class SubConfig(Nestable):
            nested = ConfigProperty(default='Default')

        sub_config: SubConfig  # A class member will be auto created.

Then you use it in the precept class like so:

.. code-block:: python

    from precept import Precept

    class MyApp(Precept):
        config = MyConfig()

Config file
-----------

To use the config with files, add a ``config_file`` argument to precept init:

.. code-block:: python

    from precept import Precept

    class MyApp(Precept):
        def __init__(self):
            super().__init__(
                config_file='config.yml',
            )


Precept will automatically add a ``--config-file`` global argument for the user
to override.

It will also add a ``dump-config`` command to dump the default config for first
use.

.. note::

    The ``config_file`` argument can also be a list, in which case the first
    file found will be used.

Config format
-------------

Precept can read and write three config format, default being yaml:

:py:class:`~precept.ConfigFormat`

- yaml
- ini
- json, doesn't support comments.

.. seealso::

    :ref:`concepts`
