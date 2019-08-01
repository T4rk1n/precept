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
application. If no command was supplied, py:func:`~precept.Precept.main`
will be called instead.

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

Config format
-------------

Precept can read and write three config format, default being yaml:

:py:class:`~precept.ConfigFormat`

- yaml
- ini
- json, doesn't support comments.

.. seealso::

    :ref:`concepts`
