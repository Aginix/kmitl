=============
Photo Viewer
=============

Opens attachments in a draggable / resizable / zoomable photo viewer
(`nzbin/photoviewer <https://github.com/nzbin/photoviewer>`_ 3.11.1, MIT,
bundled in ``static/lib/photoviewer``).

* ``many2many_binary`` fields: hovering an attachment shows a zoom cursor and
  clicking it opens the viewer instead of downloading the file.
* Chatter: clicking an image attachment opens the viewer.

Other file types can be added by registering a renderer::

    registry.category("agx_photoviewer.renderers").add("my_type", {
        match: (attachment) => attachment.mimetype === "...",
        render: (attachment, container) => { /* replace container content */ },
    });

See ``agx_photoviewer_filetypes`` for PDF, video, Word, Excel and PowerPoint.
