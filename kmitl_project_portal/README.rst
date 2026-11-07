======================
KMITL Project — Portal
======================

Portal (frontend) pages for ``kmitl.project``, split out of ``kmitl_project`` so
the portal can evolve and be upgraded without touching the core module.

* ``/projects`` — public list of approved projects, grouped by fiscal year
* ``/project/<id>`` — public project detail
* ``/my/kmitl-projects`` and ``/my/kmitl-project/<id>`` — the user's own projects
* ``/project/dashboard`` — project dashboard by department

Installs automatically with ``kmitl_project``. Being a new module, an existing
database needs an explicit ``-i kmitl_project_portal`` (``-u`` does not install
new auto-install modules).
