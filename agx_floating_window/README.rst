===============
Floating Window
===============

Opens a client action in a floating window instead of a modal dialog. The
window has no backdrop, so the page behind it stays usable. It can be dragged
by its header, resized from its corner and maximized, and several windows can
be open at once (clicking one brings it to the front, Esc closes it).

Return the ``agx_floating_window`` client action and name the client action to
show in ``params.tag``; the action's ``name`` and ``context`` are passed on::

    return {
        "type": "ir.actions.client",
        "tag": "agx_floating_window",
        "name": "My report",
        "params": {"tag": "my_client_action"},
        "context": {...},
    }

From JavaScript, call the service directly::

    env.services.agx_floating_window.open({title, Component, props});
