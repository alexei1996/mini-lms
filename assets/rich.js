(function () {
  var richTag = /<(?:p|div|br|strong|em|b|i|a)\b/i;
  var align = /text-align\s*:\s*(left|center|right|justify)/i;
  var safeUrl = /^(https?:|mailto:)/i;

  function looksRich(text) {
    return richTag.test(text || "");
  }

  function append(parent, html) {
    var parsed = new DOMParser().parseFromString("<div>" + (html || "") + "</div>", "text/html");
    copy(parsed.body.firstChild, parent);
  }

  function copy(node, target) {
    Array.prototype.forEach.call(node.childNodes, function (child) {
      if (child.nodeType === 3) {
        target.append(document.createTextNode(child.textContent));
        return;
      }
      if (child.nodeType !== 1) return;
      var tag = child.tagName.toLowerCase();
      if (tag === "b") tag = "strong";
      if (tag === "i") tag = "em";
      if (["p", "div", "br", "strong", "em", "a"].indexOf(tag) < 0) {
        copy(child, target);
        return;
      }
      if (tag === "a") {
        var href = child.getAttribute("href") || "";
        if (!safeUrl.test(href)) {
          copy(child, target);
          return;
        }
        var link = document.createElement("a");
        link.href = href;
        link.rel = "noopener";
        link.target = "_blank";
        copy(child, link);
        target.append(link);
        return;
      }
      var next = document.createElement(tag);
      if (tag === "p" || tag === "div") {
        var found = align.exec(child.getAttribute("style") || "");
        if (found) next.style.textAlign = found[1].toLowerCase();
      }
      if (tag !== "br") copy(child, next);
      target.append(next);
    });
  }

  window.LMS_RICH = { looksRich: looksRich, append: append };
})();
