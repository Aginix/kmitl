============================
Mail Activity Todo - Discuss
============================

Makes the unified Todo inbox (from ``mail_activity_todo``) a first-class
destination **inside Discuss**, so every piece of incoming work addressed to
the user — chat messages, mailbox notifications and actionable Todos — lives in
one place.

Features
========

* A **Todos** row in the Discuss sidebar, next to Inbox / Starred / History,
  with a live unread count and active-state highlight that behave like the
  native mailbox rows.
* Clicking it opens the Todo inbox in the Discuss **main content pane** (not a
  cramped sidebar list): the user's open Todos (up to 100, earliest deadline
  first), each with its source-app icon, subject, source record and a
  colour-coded deadline (overdue / today / planned).
* Click a Todo to jump straight to its source document.
* A header button and footer link open the full Todo app for the remainder
  (``View all (N)`` when more than 100 Todos exist).
* The activity **systray** routes here too: clicking it opens the Todos page
  inside Discuss rather than the backend list.
* Live refresh via the existing ``mail_activity_todo`` bus notification.
* Selecting a mailbox/channel automatically leaves the Todo view, and vice
  versa — they are never highlighted at once.

How it works
============

* ``res.users.get_my_todos`` (added here) provides the list payload, reusing
  ``mail_activity_todo``'s ``_my_todo_count_domain`` so the page, the sidebar
  count and the Todo app all select the same Todos.
* A ``registerPatch`` on the legacy mail ``Discuss`` model adds an
  ``isTodoActive`` flag and an ``openTodos()`` method (mirroring ``openThread``);
  the Discuss content/sidebar templates are extended via ``t-inherit`` to render
  the Todo view and the sidebar row.

Configuration
=============

No configuration required. Install the module; the Todos destination appears
for every user in Discuss (desktop layout).
