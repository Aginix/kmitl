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
* Lists the user's pending Todos (up to 100, earliest deadline first), each
  with its source-app icon, subject, source record and a colour-coded
  deadline (overdue / today / planned). A live total count sits in the header,
  mirroring the systray badge.
* Click a Todo to jump straight to its source document.
* A **View all (N)** link opens the full Todo app for the remaining Todos.
* Live refresh: the panel updates in real time as Todos addressed to the user
  change (reuses the existing ``mail_activity_todo`` bus notification).
* Collapsible header, with the list scrolling within the panel so it never
  pushes the Channels / Direct Messages categories off-screen.

The list payload is provided by ``res.users.get_my_todos`` (added here),
which reuses ``mail_activity_todo``'s ``_my_todo_count_domain`` so the panel,
the systray badge and the Todo app all select the same Todos. Navigation
reuses ``mail.activity.action_open_document`` and the
``mail_activity_todo.action_my_todos`` action.

Configuration
=============

No configuration required. Install the module; the panel appears for every user
in Discuss (desktop layout).
