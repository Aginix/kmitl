===============
Change Requests
===============

Whoever checks a record asks its maker to fix or explain something, and follows
each request until its author is satisfied. See ``CONTEXT.md`` (Change request,
Reply, Assignee) and ``docs/adr/0001``.

* A model takes Change requests by inheriting ``change.request.mixin`` besides
  ``mail.thread`` and ``mail.activity.mixin``. Its form then gets a **Change
  requests** button beside the action menu, with the count of outstanding ones,
  opening a side panel: always on the right (it hides a sided chatter while
  open, and floats over the form on smaller screens).
* Anyone who can read the record makes, answers and follows its requests; its
  author edits or deletes one at any time (earlier texts are kept) and closes or
  reopens it. Administrators, and whoever the record's module allows
  (``_change_request_can_close_on_behalf``), may close one on the author's
  behalf.
* Each request carries a conversation of **replies**: a reply from someone else
  answers it, its author replying to an answered one opens it again.
* **Assignees** get an activity to answer a request while it is open; its
  author gets none. Every step and reply is posted on the record's chatter as
  it happens.
* Outstanding requests (open or answered) never hold up a record by
  themselves; its module may refuse a step while
  ``record._get_outstanding_change_requests()`` is not empty.

``agx_photoviewer_change_request`` pins requests on the image and PDF files of a
record.
