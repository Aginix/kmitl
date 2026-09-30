=============
Photo Viewer
=============

Opens attachments in a draggable / resizable / zoomable photo viewer
(`nzbin/photoviewer <https://github.com/nzbin/photoviewer>`_ 3.11.1, MIT,
bundled in ``static/lib/photoviewer``).

* ``many2many_binary`` fields: hovering an attachment shows a zoom cursor and
  clicking it opens the viewer instead of downloading the file.
* Files that cannot be rendered open too, with a "not supported" message
  naming the file type; the Download button stays available.
* Chatter: clicking an attachment opens the viewer.
* The previous / next buttons walk through all the previewable attachments of
  the list, images and files alike. The modal can be resized freely.

Other file types can be added by registering a renderer::

    registry.category("agx_photoviewer.renderers").add("my_type", {
        match: (attachment) => attachment.mimetype === "...",
        render: (attachment, page) => { /* replace the page content */ },
    });

See ``agx_photoviewer_filetypes`` for PDF, video, Word, Excel and PowerPoint.
