.. _concepts:

Concepts
========

These concepts can be used to extend and interact with precept applications.

Events
------

Generic asyncio event consumer system.

The Precept instance and services both comes with an event dispatcher (``events`` member). You
can subscribe to events and handle them when they happen.

**Subscribe to events**

Subscribe to events that are dispatched.

.. code-block:: python

    app.events.subscribe('cli_started', lambda e: print('Started'))

**Dispatch events**

Send events with optional payload as keyword arguments.

.. code-block:: python

    app.events.dispatch('my_events', something='foo')

cli events
**********

These events are available when starting the application with `start`.

.. list-table:: Cli events
    :header-rows: 1

    *   - Event
        - Description
    *   - ``before_cli_start``
        - Called before everything else.
    *   - ``cli_parsed``
        - Called after parsing the arguments and before the command start, payload with the arguments.
    *   - ``cli_started``
        - The command has started, this is called at the same time.
    *   - ``cli_stopped``
        - The command has stopped and the application will quit after.

.. seealso::

    - :py:class:`~.events.Event`
    - :py:class:`~.events.EventDispatcher`
    - :py:class:`~.events.PreceptEvent`

Services
--------

Service's runs alongside the precept application, they are started and stopped
at the same time when calling :py:func:`~precept.Precept.start`.

Service events
**************

Services comes with three auto events starting with the service name.
If a service is called `dummy`, it will get:

- ``dummy_setup``, called with the running application before starting.
- ``dummy_start``, started before the application.
- ``dummy_stop``, stopped after the application.

.. note::

    If the application is not started with ``start``, you need to call the
    services methods:

    - ``setup_services``
    - ``start_services``
    - ``stop_services``

.. seealso::

    - :py:class:`~.Service`

Plugins
-------

Plugins automatically connect to precept applications during initialisation.

They have one method, :py:func:`~precept.Plugin.setup`, which takes the application
as argument you can use to set variables.

To add a plugin, you need to set it in `setup.py`, the entrypoint key needs to
be the snake cased version of ``prog_name`` variable of the precept application.

.. code-block:: python

    from setuptools import setup

    setup(
        entry_points={
            'precept_app.plugins': ['my_plugin = plug:plugin']
        }
    )

.. seealso::

    - :py:class:`~.Plugin`
