==============
Developer Login
==============

Quick admin login button for development and testing environments to improve developer experience.

Features
========

* Adds a "Login as Admin" button to the login page
* One-click admin authentication for development and testing
* Always available on login page for easy access
* Perfect for runbot and development instances

Target Environments
====================

This module is designed for development and testing environments including:

* Development instances
* Runbot environments
* Testing databases
* Local development setups

Installation
============

1. Copy the module to your addons directory
2. Install the module from Apps menu
3. Navigate to login page - you should see the "Login as Admin" button

Usage
=====

1. Go to the login page (``/web/login``)
2. Click the "Login as Admin" button
3. You'll be automatically logged in as admin and redirected to the web client

Configuration
=============

No additional configuration required. The module automatically detects:

* Admin user by login name 'admin'
* Falls back to superuser (ID 1) if admin user not found

**Note**: This module is intended for development and testing environments.

Technical Details
=================

Backend
-------

* Controller: ``/dev_login/admin`` (POST only)
* Automatic user authentication and session management
* Error handling and logging
* Simple and reliable login process

Frontend
--------

* JavaScript integration with Odoo web client
* Always visible on login page
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