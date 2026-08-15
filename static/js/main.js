(function () {
  "use strict";

  // Destructive form confirmation
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("submit", function (e) {
      var msg = el.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(msg)) {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
    });
  });

  // Floating navbar scroll state
  var header = document.getElementById("site-header");
  var navShell = document.querySelector(".nav-shell-premium");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("scrolled", window.scrollY > 12);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // Premium navbar — cursor glow + magnetic hover
  if (navShell) {
    navShell.addEventListener("mousemove", function (e) {
      var rect = navShell.getBoundingClientRect();
      var x = ((e.clientX - rect.left) / rect.width) * 100;
      var y = ((e.clientY - rect.top) / rect.height) * 100;
      navShell.style.setProperty("--nav-glow-x", x + "%");
      navShell.style.setProperty("--nav-glow-y", y + "%");
      navShell.classList.add("nav-glow-active");
    });

    navShell.addEventListener("mouseleave", function () {
      navShell.classList.remove("nav-glow-active");
    });

    // Subtle magnetic pull on nav items
    var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduceMotion) {
      var magneticEls = navShell.querySelectorAll(
        ".brand-premium, .nav-link, .btn-nav-cta, .btn-nav-ghost, .btn-nav-outline, .btn-nav-profile"
      );
      magneticEls.forEach(function (el) {
        el.addEventListener("mousemove", function (e) {
          var r = el.getBoundingClientRect();
          var dx = e.clientX - (r.left + r.width / 2);
          var dy = e.clientY - (r.top + r.height / 2);
          var strength = el.classList.contains("brand-premium") ? 0.14 : 0.22;
          el.style.setProperty("--mag-x", (dx * strength) + "px");
          el.style.setProperty("--mag-y", (dy * strength) + "px");
        });
        el.addEventListener("mouseleave", function () {
          el.style.setProperty("--mag-x", "0px");
          el.style.setProperty("--mag-y", "0px");
        });
      });
    }
  }

  // Active nav link highlight
  var path = window.location.pathname.replace(/\/$/, "") || "/index.html";
  document.querySelectorAll(".nav-link[href]").forEach(function (link) {
    var href = link.getAttribute("href").replace(/\/$/, "");
    if (href === path || (path.endsWith(href) && href !== "/index.html")) {
      link.classList.add("is-active");
    }
    if (href === "/index.html" && (path === "/index.html" || path === "" || path === "/")) {
      link.classList.add("is-active");
    }
  });

  // Mobile menu + dashboard sidebar drawer
  var toggle = document.getElementById("mobile-menu-toggle");
  var menu = document.getElementById("mobile-menu");
  var dashSidebar = document.getElementById("dash-sidebar");
  var dashOverlay = document.getElementById("dash-overlay");

  function setToggleIcon(open) {
    if (!toggle) return;
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    var icon = toggle.querySelector("i");
    if (icon) {
      icon.classList.toggle("fa-bars", !open);
      icon.classList.toggle("fa-xmark", open);
    }
  }

  function closeDashDrawer() {
    if (dashSidebar) dashSidebar.classList.remove("is-open");
    if (dashOverlay) {
      dashOverlay.classList.remove("is-open");
      dashOverlay.hidden = true;
    }
    document.body.classList.remove("dash-nav-open");
    setToggleIcon(false);
  }

  if (toggle && dashSidebar) {
    toggle.addEventListener("click", function () {
      var open = !dashSidebar.classList.contains("is-open");
      dashSidebar.classList.toggle("is-open", open);
      document.body.classList.toggle("dash-nav-open", open);
      if (dashOverlay) {
        dashOverlay.classList.toggle("is-open", open);
        dashOverlay.hidden = !open;
      }
      if (menu) menu.classList.toggle("open", open);
      setToggleIcon(open);
    });
    if (dashOverlay) {
      dashOverlay.addEventListener("click", closeDashDrawer);
    }
  } else if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("open");
      setToggleIcon(open);
    });
    document.addEventListener("click", function (e) {
      if (!header || !header.contains(e.target)) {
        menu.classList.remove("open");
        setToggleIcon(false);
      }
    });
  }

  // Scroll reveal
  var reveals = document.querySelectorAll(".reveal");
  if (reveals.length && "IntersectionObserver" in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach(function (el) { observer.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("visible"); });
  }

  // Study planner result is rendered by Django after POST


  // Notes quiz demo check
  var quizForm = document.getElementById("quiz-form");
  if (quizForm) {
    quizForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var result = document.getElementById("quiz-result");
      if (result) {
        result.classList.remove("hidden");
        result.classList.add("reveal", "visible");
        result.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  }

  // Blog filter pills (visual toggle only)
  document.querySelectorAll(".filter-pills .filter-pill").forEach(function (pill) {
    pill.addEventListener("click", function () {
      pill.parentElement.querySelectorAll(".filter-pill").forEach(function (p) {
        p.classList.remove("active");
      });
      pill.classList.add("active");
    });
  });

  // Hero 3D scene — subtle mouse parallax
  var heroScene = document.getElementById("hero-scene");
  var heroStage = document.getElementById("hero-scene-stage");
  if (heroScene && heroStage && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    var heroTicking = false;
    var heroTargetX = 8;
    var heroTargetY = -12;
    var heroCurrentX = 8;
    var heroCurrentY = -12;

    function applyHeroTilt() {
      heroCurrentX += (heroTargetX - heroCurrentX) * 0.08;
      heroCurrentY += (heroTargetY - heroCurrentY) * 0.08;
      heroStage.style.setProperty("--hero-rx", heroCurrentX + "deg");
      heroStage.style.setProperty("--hero-ry", heroCurrentY + "deg");
      if (Math.abs(heroTargetX - heroCurrentX) > 0.05 || Math.abs(heroTargetY - heroCurrentY) > 0.05) {
        requestAnimationFrame(applyHeroTilt);
      } else {
        heroTicking = false;
      }
    }

    function onHeroMove(e) {
      var rect = heroScene.getBoundingClientRect();
      var x = (e.clientX - rect.left) / rect.width - 0.5;
      var y = (e.clientY - rect.top) / rect.height - 0.5;
      heroTargetX = 8 + (-y * 10);
      heroTargetY = -12 + (x * 16);
      if (!heroTicking) {
        heroTicking = true;
        requestAnimationFrame(applyHeroTilt);
      }
    }

    function onHeroLeave() {
      heroTargetX = 8;
      heroTargetY = -12;
      if (!heroTicking) {
        heroTicking = true;
        requestAnimationFrame(applyHeroTilt);
      }
    }

    heroScene.addEventListener("mousemove", onHeroMove);
    heroScene.addEventListener("mouseleave", onHeroLeave);

    // Touch: very subtle tilt on move
    heroScene.addEventListener("touchmove", function (e) {
      if (!e.touches.length) return;
      var touch = e.touches[0];
      onHeroMove({ clientX: touch.clientX, clientY: touch.clientY });
    }, { passive: true });
  }

  // Resource page — search + filter pills
  var resourceGrid = document.getElementById("resources-grid");
  var resourceSearch = document.getElementById("resource-search");
  var resourceEmpty = document.getElementById("resources-empty");
  var resourceReset = document.getElementById("resources-reset");
  var resourceFilterBtns = document.querySelectorAll(".resources-filters .filter-pill[data-filter]");

  if (resourceGrid) {
    var activeFilter = "all";

    function applyResourceFilters() {
      var query = resourceSearch ? resourceSearch.value.trim().toLowerCase() : "";
      var cards = resourceGrid.querySelectorAll(".resource-card-premium");
      var visible = 0;

      cards.forEach(function (card) {
        var type = card.getAttribute("data-type") || "";
        var searchText = (card.getAttribute("data-search") || card.textContent).toLowerCase();
        var typeMatch = activeFilter === "all" || type === activeFilter;
        var searchMatch = !query || searchText.indexOf(query) !== -1;
        var show = typeMatch && searchMatch;
        card.classList.toggle("hidden", !show);
        if (show) visible++;
      });

      if (resourceEmpty) resourceEmpty.classList.toggle("hidden", visible > 0);
      resourceGrid.classList.toggle("hidden", visible === 0);
    }

    if (resourceSearch) {
      resourceSearch.addEventListener("input", applyResourceFilters);
    }

    resourceFilterBtns.forEach(function (pill) {
      pill.addEventListener("click", function () {
        resourceFilterBtns.forEach(function (p) { p.classList.remove("active"); });
        pill.classList.add("active");
        activeFilter = pill.getAttribute("data-filter") || "all";
        applyResourceFilters();
      });
    });

    if (resourceReset) {
      resourceReset.addEventListener("click", function () {
        activeFilter = "all";
        if (resourceSearch) resourceSearch.value = "";
        resourceFilterBtns.forEach(function (p) {
          p.classList.toggle("active", p.getAttribute("data-filter") === "all");
        });
        applyResourceFilters();
      });
    }
  }

  // Note detail — copy code button
  document.querySelectorAll(".note-code-copy").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var code = btn.closest(".note-code-block");
      if (!code) return;
      var pre = code.querySelector("pre");
      if (!pre) return;
      var text = pre.textContent;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
          var icon = btn.querySelector("i");
          if (icon) {
            icon.classList.remove("fa-copy");
            icon.classList.add("fa-check");
            setTimeout(function () {
              icon.classList.remove("fa-check");
              icon.classList.add("fa-copy");
            }, 1500);
          }
        });
      }
    });
  });

  // Note detail — TOC active link on scroll
  var tocLinks = document.querySelectorAll(".note-toc-link");
  if (tocLinks.length && "IntersectionObserver" in window) {
    var tocSections = [];
    tocLinks.forEach(function (link) {
      var id = link.getAttribute("href");
      if (id && id.charAt(0) === "#") {
        var el = document.querySelector(id);
        if (el) tocSections.push({ link: link, el: el });
      }
    });
    if (tocSections.length) {
      var tocObserver = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              tocSections.forEach(function (s) {
                s.link.classList.toggle("is-active", s.el === entry.target);
              });
            }
          });
        },
        { rootMargin: "-20% 0px -60% 0px", threshold: 0 }
      );
      tocSections.forEach(function (s) { tocObserver.observe(s.el); });
    }
  }

  // PDF upload dropzone (demo — file stays local; form still redirects)
  var dropzone = document.getElementById("pdf-dropzone");
  var fileInput = document.getElementById("pdf-file");
  var dropIdle = document.getElementById("pdf-drop-idle");
  var dropFile = document.getElementById("pdf-drop-file");
  var fileNameEl = document.getElementById("pdf-file-name");
  var fileSizeEl = document.getElementById("pdf-file-size");
  var fileRemove = document.getElementById("pdf-file-remove");

  function formatBytes(bytes) {
    if (!bytes) return "0 KB";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function showSelectedFile(file) {
    if (!file || !dropIdle || !dropFile) return;
    dropIdle.classList.add("hidden");
    dropFile.classList.remove("hidden");
    if (dropzone) dropzone.classList.add("has-file");
    if (fileNameEl) fileNameEl.textContent = file.name;
    if (fileSizeEl) fileSizeEl.textContent = formatBytes(file.size);
  }

  function clearSelectedFile() {
    if (fileInput) fileInput.value = "";
    if (dropIdle) dropIdle.classList.remove("hidden");
    if (dropFile) dropFile.classList.add("hidden");
    if (dropzone) dropzone.classList.remove("has-file");
  }

  if (dropzone && fileInput) {
    fileInput.addEventListener("change", function () {
      if (fileInput.files && fileInput.files[0]) showSelectedFile(fileInput.files[0]);
    });

    ["dragenter", "dragover"].forEach(function (evt) {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        dropzone.classList.add("is-dragover");
      });
    });

    ["dragleave", "drop"].forEach(function (evt) {
      dropzone.addEventListener(evt, function () {
        dropzone.classList.remove("is-dragover");
      });
    });

    dropzone.addEventListener("drop", function (e) {
      e.preventDefault();
      var files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) return;
      var file = files[0];
      if (file.type && file.type !== "application/pdf") return;
      try {
        var dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
      } catch (err) {
        /* browsers without DataTransfer still show UI */
      }
      showSelectedFile(file);
    });

    if (fileRemove) {
      fileRemove.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        clearSelectedFile();
      });
    }
  }

  // Forum feed — search + type filters
  var forumList = document.getElementById("forum-thread-list");
  var forumSearch = document.getElementById("forum-search");
  var forumEmpty = document.getElementById("forum-empty");
  var forumFilterBtns = document.querySelectorAll(".forum-filters .filter-pill[data-filter]");

  if (forumList) {
    var forumFilter = "all";

    function applyForumFilters() {
      var query = forumSearch ? forumSearch.value.trim().toLowerCase() : "";
      var cards = forumList.querySelectorAll(".forum-thread-card");
      var visible = 0;
      cards.forEach(function (card) {
        var type = card.getAttribute("data-type") || "";
        var searchText = (card.getAttribute("data-search") || card.textContent).toLowerCase();
        var show = (forumFilter === "all" || type === forumFilter) && (!query || searchText.indexOf(query) !== -1);
        card.classList.toggle("hidden", !show);
        if (show) visible++;
      });
      if (forumEmpty) forumEmpty.classList.toggle("hidden", visible > 0);
      forumList.classList.toggle("hidden", visible === 0);
    }

    if (forumSearch) forumSearch.addEventListener("input", applyForumFilters);
    forumFilterBtns.forEach(function (pill) {
      pill.addEventListener("click", function () {
        forumFilterBtns.forEach(function (p) { p.classList.remove("active"); });
        pill.classList.add("active");
        forumFilter = pill.getAttribute("data-filter") || "all";
        applyForumFilters();
      });
    });
  }

  // Forum vote buttons (visual only)
  document.querySelectorAll(".forum-vote-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var group = btn.parentElement;
      if (!group) return;
      group.querySelectorAll(".forum-vote-btn").forEach(function (b) { b.classList.remove("is-active"); });
      btn.classList.add("is-active");
    });
  });

  // Password visibility toggle
  document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var id = btn.getAttribute("data-toggle-password");
      var input = id ? document.getElementById(id) : null;
      if (!input) return;
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
      var icon = btn.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-eye", !show);
        icon.classList.toggle("fa-eye-slash", show);
      }
    });
  });

  // Blog search + category filters
  var blogGrid = document.getElementById("blog-grid");
  var blogSearch = document.getElementById("blog-search");
  var blogEmpty = document.getElementById("blog-empty");
  var blogPills = document.querySelectorAll(".blog-filters .filter-pill[data-filter]");
  var blogFeatured = document.querySelector(".blog-featured");

  if (blogGrid) {
    var blogFilter = "all";

    function applyBlogFilters() {
      var query = blogSearch ? blogSearch.value.trim().toLowerCase() : "";
      var items = [];
      if (blogFeatured) items.push(blogFeatured);
      blogGrid.querySelectorAll(".blog-card").forEach(function (c) { items.push(c); });
      var visible = 0;
      items.forEach(function (card) {
        var type = card.getAttribute("data-type") || "";
        var searchText = (card.getAttribute("data-search") || card.textContent).toLowerCase();
        var show = (blogFilter === "all" || type === blogFilter) && (!query || searchText.indexOf(query) !== -1);
        card.classList.toggle("hidden", !show);
        if (show) visible++;
      });
      if (blogEmpty) blogEmpty.classList.toggle("hidden", visible > 0);
      var gridVisible = 0;
      blogGrid.querySelectorAll(".blog-card").forEach(function (c) {
        if (!c.classList.contains("hidden")) gridVisible++;
      });
      blogGrid.classList.toggle("hidden", gridVisible === 0);
    }

    if (blogSearch) blogSearch.addEventListener("input", applyBlogFilters);
    blogPills.forEach(function (pill) {
      pill.addEventListener("click", function () {
        blogFilter = pill.getAttribute("data-filter") || "all";
        applyBlogFilters();
      });
    });
  }

  // Exam routine list filter
  var routineForm = document.getElementById("routine-filter-form");
  if (routineForm) {
    function applyRoutineFilter() {
      var course = (document.getElementById("routine-course") || {}).value || "";
      var sec = (document.getElementById("routine-sec") || {}).value || "";
      var q = (course + " " + sec).trim().toLowerCase();
      var visible = 0;
      document.querySelectorAll("#routine-table .routine-row").forEach(function (row) {
        var hay = (row.getAttribute("data-search") || "").toLowerCase();
        var show = !q || hay.indexOf(course.trim().toLowerCase()) !== -1;
        if (sec.trim()) show = show && hay.indexOf(sec.trim().toLowerCase()) !== -1;
        row.classList.toggle("hidden", !show);
        if (show) visible++;
      });
      document.querySelectorAll("#routine-cards .routine-row").forEach(function (row) {
        var hay = (row.getAttribute("data-search") || "").toLowerCase();
        var show = !q || hay.indexOf(course.trim().toLowerCase()) !== -1;
        if (sec.trim()) show = show && hay.indexOf(sec.trim().toLowerCase()) !== -1;
        row.classList.toggle("hidden", !show);
      });
      var countEl = document.getElementById("routine-count");
      if (countEl) countEl.textContent = String(visible);
      var empty = document.getElementById("routine-empty");
      if (empty) empty.classList.toggle("hidden", visible > 0);
    }

    routineForm.addEventListener("submit", function (e) {
      e.preventDefault();
      applyRoutineFilter();
    });
  }
})();
