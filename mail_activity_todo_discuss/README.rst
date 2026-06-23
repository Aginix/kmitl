============================
Mail Activity Todo - Discuss
============================

Makes the unified Todo inbox (from ``mail_activity_todo``) a first-class
destination **inside Discuss**, so every piece of incoming work addressed to
the user — chat messages, mailbox notifications and actionable Todos — lives in
one place.

Features
========

* A collapsible **Todos** section in the Discuss sidebar, next to Inbox /
  Starred / History, listing pending Todos **grouped by source app** with live
  counts and an overdue / today / upcoming breakdown — with active-state
  highlight like the native mailbox rows.
* Clicking the header opens the Todo inbox in the Discuss **main content pane**
  (not a cramped sidebar list); clicking an app group opens it **filtered to
  that app**.
* The page lists the user's open Todos (up to 100, earliest deadline first),
  each with its source-app icon, subject, **app, source record, activity type,
  category, assignee, note** and a colour-coded deadline (overdue / today /
  planned).
* Click a Todo to jump straight to its source document.
* A header button and footer link open the full Todo app for the remainder
  (``Showing N of M`` when more than 100 Todos exist).
* The activity **systray** routes here too: clicking it opens the Todos page
  inside Discuss rather than the backend list.
* Live refresh via the existing ``mail_activity_todo`` bus notification.
* Selecting a mailbox/channel automatically leaves the Todo view, and vice
  versa — they are never highlighted at once.

How it works
============

* ``res.users.get_my_todos`` (added here) provides the list payload (optionally
  filtered to one ``res_model``), reusing ``mail_activity_todo``'s
  ``_my_todo_count_domain`` so the page, the sidebar group counts and the Todo
  app all select the same Todos.
* A ``registerPatch`` on the legacy mail ``Discuss`` model adds ``isTodoActive``
  / ``todoResModel`` flags and an ``openTodos(resModel)`` method (mirroring
  ``openThread``); the Discuss content/sidebar templates are extended via
  ``t-inherit`` to render the Todo view and the grouped sidebar panel.

Configuration
=============

No configuration required. Install the module; the Todos destination appears
for every user in Discuss (desktop layout).
