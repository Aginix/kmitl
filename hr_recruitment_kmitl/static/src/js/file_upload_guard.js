odoo.define("hr_recruitment_kmitl.file_upload_guard", function () {
    "use strict";

    var MAX_BYTES = 25 * 1024 * 1024;

    function extensionsFromAccept(accept) {
        if (!accept) return null;
        var exts = [];
        accept.split(",").forEach(function (rawToken) {
            var token = rawToken.trim().toLowerCase();
            if (!token) return;
            if (token.charAt(0) === ".") {
                exts.push(token);
            }
        });
        return exts.length ? exts : null;
    }

    function matchesAccept(file, accept) {
        if (!accept) return true;
        var name = (file.name || "").toLowerCase();
        var type = (file.type || "").toLowerCase();
        var tokens = accept.split(",").map(function (t) {
            return t.trim().toLowerCase();
        });
        for (var i = 0; i < tokens.length; i++) {
            var tok = tokens[i];
            if (!tok) continue;
            if (tok.charAt(0) === ".") {
                if (name.endsWith(tok)) return true;
            } else if (tok.endsWith("/*")) {
                var prefix = tok.slice(0, -1);
                if (type.indexOf(prefix) === 0) return true;
            } else if (type === tok) {
                return true;
            }
        }
        return false;
    }

    function validate(input) {
        if (!input.files || !input.files.length) return true;
        var accept = input.getAttribute("accept");
        var allowedExts = extensionsFromAccept(accept);
        for (var i = 0; i < input.files.length; i++) {
            var f = input.files[i];
            if (f.size > MAX_BYTES) {
                // eslint-disable-next-line no-alert
                alert(
                    'ไฟล์ "' + f.name + '" มีขนาดเกิน 25 MB กรุณาเลือกไฟล์ขนาดเล็กกว่า'
                );
                input.value = "";
                return false;
            }
            if (!matchesAccept(f, accept)) {
                var hint = allowedExts
                    ? " (อนุญาตเฉพาะ " + allowedExts.join(", ") + ")"
                    : "";
                // eslint-disable-next-line no-alert
                alert('ไฟล์ "' + f.name + '" มีนามสกุลที่ไม่รองรับ' + hint);
                input.value = "";
                return false;
            }
        }
        return true;
    }

    function init() {
        document.addEventListener(
            "change",
            function (ev) {
                var t = ev.target;
                if (t && t.tagName === "INPUT" && t.type === "file") {
                    validate(t);
                }
            },
            true
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
});
