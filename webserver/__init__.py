"""
GPGCloud backend uses NGINX_ with gunicorn_ as its web server.

NGINX_ on Mac OS X
==================

Install NGINX_ using Mac ports.

.. code-block:: bash

    sudo port install nginx +ssl

Copy example configuration.

.. code-block:: bash

    sudo cp nginx.conf /opt/local/etc/nginx

Configuration file:

.. literalinclude:: ../webserver/nginx.conf

See NGINX_ documentation for more information about other configuration
options.

Create self-signed test certificates.

.. code-block:: bash

    cd /opt/local/etc/nginx
    sudo openssl genrsa -out server.key 2048
    sudo openssl req -new -key server.key -out server.csr
    sudo openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

Start NGINX_.

.. code-block:: bash

    sudo launchctl load -F /Library/LaunchDaemons/org.macports.nginx.plist

gunicorn_
=========

gunicorn_ is installed as part of python requirements.

Start gunicorn_ in GPGCloud project directory.

.. code-block:: bash

    gunicorn -w 4 -b 127.0.0.1:8000 cryptoengine.server:app --reload

See gunicorn_ documentation for more information about other options.

"""