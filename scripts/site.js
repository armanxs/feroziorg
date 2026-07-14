(function () {
  "use strict";

  // Collapse nav on link click (mobile)
  document.querySelectorAll("#mainNav .nav-link, #mainNav .dropdown-item").forEach(function (link) {
    link.addEventListener("click", function () {
      var nav = document.getElementById("mainNav");
      var w = window.innerWidth || document.documentElement.clientWidth;
      if (nav && w < 992 && nav.classList.contains("show") && window.bootstrap) {
        var col = bootstrap.Collapse.getInstance(nav);
        if (col) col.hide();
      }
    });
  });

  // Responsive iframe fallback for legacy inline iframes not wrapped at build time
  document.querySelectorAll(".legacy-content iframe:not(.embed-iframe)").forEach(function (iframe) {
    iframe.classList.add("embed-iframe");
    if (!iframe.parentElement.classList.contains("embed-wrap")) {
      var wrap = document.createElement("div");
      wrap.className = "ratio ratio-16x9 embed-wrap mb-4";
      iframe.parentNode.insertBefore(wrap, iframe);
      wrap.appendChild(iframe);
    }
    iframe.removeAttribute("width");
    iframe.removeAttribute("height");
    iframe.setAttribute("loading", "lazy");
  });

  // Fix absolute image paths
  document.querySelectorAll('img[src^="/"]').forEach(function (img) {
    img.src = img.src.replace(/^\/+/, "");
  });
})();
