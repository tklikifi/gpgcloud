"""
Crypto engine is the backend server that handles data encryption and
decryption. It uses celery_ task queue and redis_ database as the message
broker.

redis_ on Mac OS X
==================

Install redis_ using Mac ports.

.. code-block:: bash

    sudo port install redis

Start redis_ server.

.. code-block:: bash

    sudo port load redis

celery_
=======

celery_ is installed as part of python requirements.

Start celery_ in GPGCloud project directory.

.. code-block:: bash

    celery -A cryptoengine.server:celery worker -l info

"""