==============
Developer Login
==============

Quick admin login button for development environment to improve developer experience.

Features
========

* Adds a "Login as Admin" button to the login page
* One-click admin authentication for development
* Multiple security layers to prevent production use
* Only visible in debug/development mode

Security Features
=================

This module implements several security measures to ensure it's only used in development:

1. **Development Mode Check**: Only works when ``dev_mode`` is enabled in Odoo configuration
2. **Debug Mode Requirement**: Button only appears when debug mode is active
3. **Production Prevention**: Controller returns 403 Forbidden if not in development mode
4. **Logging**: All attempts are logged for security auditing

Installation
============

1. Copy the module to your addons directory
2. Enable developer mode in Odoo (add ``?debug=1`` to URL or use developer tools)
3. Install the module from Apps menu
4. Navigate to login page - you should see the "Login as Admin" button

Usage
=====

1. Go to the login page (``/web/login``)
2. Ensure debug mode is enabled (``?debug=1``)
3. Click the "Login as Admin" button
4. You'll be automatically logged in as admin and redirected to the web client

Configuration
=============

No additional configuration required. The module automatically detects:

* Admin user by login name 'admin'
* Falls back to superuser (ID 1) if admin user not found
* Requires Odoo to be running with ``--dev`` flag or development configuration

**WARNING**: This module should NEVER be installed in production environments!

Technical Details
=================

Backend
-------

* Controller: ``/dev_login/admin`` (POST only)
* Security checks for development mode
* Automatic user authentication and session management
* Error handling and logging

Frontend
--------

* JavaScript integration with Odoo web client
* Dynamic button visibility based on debug mode
* Form submission handling
* Loading states and user feedback

Dependencies
============

* ``base``: Core Odoo functionality
* ``web``: Web client and login templates

License
=======

LGPL-3

Author
======

KMITL Development Team