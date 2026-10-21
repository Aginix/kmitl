===================
Web Attachment Link
===================

Adds a *Link* button beside *Attach* on every ``many2many_binary`` attachment
field: the user enters a web address — a YouTube video, a Google Drive item, a
web page, or a document in this Odoo — and a name. The link is stored as a
standard ``url`` attachment; its kind is recognised from the address, never
stored (see ``docs/adr/0001-link-kind-derived-from-url.md``).

* A link to this Odoo is kept without its host and session parameters
  (``/web#model=…&id=…``), so it still works after the database is copied to
  another server.
* Fields limited by ``accepted_file_extensions`` do not offer links; any other
  field can opt out with ``options="{'no_link': true}"``.
* Clicking a link opens it in a new tab. With ``agx_photoviewer`` installed,
  ``agx_photoviewer_links`` opens it in the photo viewer instead.
