==================================
Mail Activity Todo - Discuss Panel
==================================

Surfaces the unified Todo inbox (from ``mail_activity_todo``) as a panel inside
the **Discuss** sidebar, so every piece of incoming work addressed to the user
— chat messages, mailbox notifications and actionable Todos — is reachable from
a single place.

Features
========

* A **Todos** section in the Discuss sidebar, below the Inbox / Starred /
  History mailboxes.
* Pending Todos grouped by source app, each with its app icon and a live
  count, mirroring the systray badge.
* Click a group to open the Todo list filtered to that source app.
* A **View all** link that opens the full Todo app.
* Live refresh: the panel updates in real time as Todos addressed to the user
  change (reuses the existing ``mail_activity_todo`` bus notification).
* Collapsible header to keep the sidebar tidy.

This module adds no new models or server logic — it reuses
``res.users.get_my_todo_count`` and the ``mail_activity_todo.action_my_todos``
action.

Configuration
=============

No configuration required. Install the module; the panel appears for every user
in Discuss (desktop layout).
