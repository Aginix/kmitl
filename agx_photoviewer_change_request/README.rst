===============================
Photo Viewer - Change Requests
===============================

Pins Change requests (``agx_change_request``) on the image and PDF files of a
record that takes them, in the photo viewer of ``agx_photoviewer_annotation``.

* A reviewer ticks *Ask for a fix* on a Comment, and may assign it to the
  record's followers; most marks stay plain review marks. The pin wears a ring
  in the colour of the request's state and offers its response, close and
  reopen actions. Files of records that take no Change requests are annotated
  and commented on, never asked to be fixed.
* The viewer's **Change requests** panel lists the outstanding ones on every
  revision of the file (with ``agx_photoviewer_annotation_revision``); the
  record's side panel groups them by file and opens the viewer on their pin.
* Files show a ``! n`` badge of their outstanding requests. Removing a pin
  deletes its request; deleting the file cancels it, keeping its text and the
  file's name. Requests are left out of the viewer's session note: each of their
  steps is posted on its own.
