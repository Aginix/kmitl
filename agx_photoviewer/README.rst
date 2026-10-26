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
  the list, images and files alike, and a thumbnail strip above the footer
  jumps straight to any of them. The modal can be resized freely.

Other file types can be added by registering a renderer::

    registry.category("agx_photoviewer.renderers").add("my_type", {
        match: (attachment) => attachment.mimetype === "...",
        render: (attachment, page) => { /* replace the page content */ },
        // Optional:
        leave: (attachment, page) => { /* the viewer left the file */ },
        decorateThumbnail: (attachment, button) => { /* add a badge */ },
    });

A renderer matching an image takes it over from the native image stage.

See ``agx_photoviewer_filetypes`` for PDF, video, Word, Excel and PowerPoint, and
``agx_photoviewer_annotation`` to mark up images and PDFs.
