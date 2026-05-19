 

  $(document).ready(function () {
    $("#dashboard").removeClass("active menu-open");
    $("#dashboard").find("ul li").removeClass("active");
    $("#docs").addClass("active");

    var apiListUrl = "{% url 'dashboard:docs_api_list' %}";
    var apiFileUrl = "{% url 'dashboard:docs_api_file' %}";
    var defaultPath = "{{ default_doc_path|escapejs }}";

    var $list = $("#docsList");
    var $filter = $("#docsFilterInput");
    var $title = $("#docsTitle");
    var $rendered = $("#docsRendered");
    var $sourcePre = $("#docsSourcePre");
    var sourceCodeEl = document.getElementById("docsSourceCode");
    var renderedEl = document.getElementById("docsRendered");

    var state = {
      files: [],
      mode: "render",
      currentPath: null,
      currentMd: ""
    };

    function setMode(mode) {
      state.mode = mode;
      $("#docsModeRender").toggleClass("is-active", mode === "render");
      $("#docsModeSource").toggleClass("is-active", mode === "source");
      $rendered.toggle(mode === "render");
      $sourcePre.toggle(mode === "source");
    }

    function setActive(path) {
      $list.find(".km-docs-item").removeClass("is-active");
      $list.find('.km-docs-item[data-path="' + path.replace(/"/g, '\\"') + '"]').addClass("is-active");
    }

    function urlWithPath(base, path) {
      return base + (base.indexOf("?") === -1 ? "?" : "&") + "path=" + encodeURIComponent(path);
    }

    function pickFromQueryOrDefault(files) {
      var u = new URL(window.location.href);
      var p = (u.searchParams.get("path") || "").trim();
      if (p) return p;
      if (defaultPath) return defaultPath;
      return (files[0] && files[0].path) || null;
    }

    function updateQuery(path) {
      var u = new URL(window.location.href);
      u.searchParams.set("path", path);
      history.replaceState(null, "", u.toString());
    }

    function renderList(files) {
      var q = ($filter.val() || "").toLowerCase().trim();
      var html = files
        .filter(function (f) {
          if (!q) return true;
          return (f.path || "").toLowerCase().indexOf(q) > -1 || (f.name || "").toLowerCase().indexOf(q) > -1;
        })
        .map(function (f) {
          return '<button type="button" class="km-docs-item" data-path="' + f.path + '"><span class="km-docs-item-name">' + f.path + '</span></button>';
        })
        .join("");
      $list.html(html || '<div class="km-docs-empty">没有匹配的文档</div>');
    }

    function setContent(path, md) {
      state.currentPath = path;
      state.currentMd = md || "";
      $title.text(path);
      sourceCodeEl.textContent = state.currentMd;
      if (window.Prism) {
        Prism.highlightElement(sourceCodeEl);
      }
      var html = window.kmMarkdownLite ? window.kmMarkdownLite.render(state.currentMd) : "";
      renderedEl.innerHTML = html;
      if (window.Prism && window.Prism.highlightAllUnder) {
        Prism.highlightAllUnder(renderedEl);
      }
      setActive(path);
      updateQuery(path);
    }

    function loadDoc(path) {
      if (!path) return;
      $.getJSON(urlWithPath(apiFileUrl, path))
        .done(function (res) {
          if (!res || res.status !== "ok") {
            setContent(path, "加载失败");
            return;
          }
          setContent(res.path || path, res.content || "");
        })
        .fail(function () {
          setContent(path, "加载失败");
        });
    }

    $list.on("click", ".km-docs-item", function () {
      var path = $(this).attr("data-path");
      loadDoc(path);
    });

    $rendered.on("click", "a.km-md-link", function (e) {
      var href = $(this).attr("href") || "";
      if (!href) return;
      if (href.indexOf("#") === 0) return;
      if (/\.md($|[?#])/i.test(href) && !/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(href)) {
        e.preventDefault();
        loadDoc(href.replace(/^\//, ""));
      }
    });

    $filter.on("input", function () {
      renderList(state.files);
    });

    $("#docsModeRender").on("click", function () {
      setMode("render");
    });
    $("#docsModeSource").on("click", function () {
      setMode("source");
    });

    setMode("render");
    $.getJSON(apiListUrl).done(function (res) {
      state.files = (res && res.files) || [];
      renderList(state.files);
      var p = pickFromQueryOrDefault(state.files);
      if (p) loadDoc(p);
      else {
        $title.text("docs/ 目录下没有可用的 .md");
        setMode("render");
      }
    });
  });

  

      $(document).ready(function () {
          $("#dashboard").removeClass("active menu-open");
          $("#dashboard").find("ul li").removeClass("active");
          $("#user").addClass("active");
      });

  

  $(document).ready(function () {
    $("#dashboard").removeClass("active menu-open");
    $("#dashboard").find("ul li").removeClass("active");
    $("#docs").addClass("active");

    var apiListUrl = "{% url 'dashboard:docs_api_list' %}";
    var apiFileUrl = "{% url 'dashboard:docs_api_file' %}";
    var defaultPath = "{{ default_doc_path|escapejs }}";

    var $list = $("#docsList");
    var $filter = $("#docsFilterInput");
    var $title = $("#docsTitle");
    var $rendered = $("#docsRendered");
    var $sourcePre = $("#docsSourcePre");
    var sourceCodeEl = document.getElementById("docsSourceCode");
    var renderedEl = document.getElementById("docsRendered");

    var state = {
      files: [],
      mode: "render",
      currentPath: null,
      currentMd: ""
    };

    function setMode(mode) {
      state.mode = mode;
      $("#docsModeRender").toggleClass("is-active", mode === "render");
      $("#docsModeSource").toggleClass("is-active", mode === "source");
      $rendered.toggle(mode === "render");
      $sourcePre.toggle(mode === "source");
    }

    function setActive(path) {
      $list.find(".km-docs-item").removeClass("is-active");
      $list.find('.km-docs-item[data-path="' + path.replace(/"/g, '\\"') + '"]').addClass("is-active");
    }

    function urlWithPath(base, path) {
      return base + (base.indexOf("?") === -1 ? "?" : "&") + "path=" + encodeURIComponent(path);
    }

    function pickFromQueryOrDefault(files) {
      var u = new URL(window.location.href);
      var p = (u.searchParams.get("path") || "").trim();
      if (p) return p;
      if (defaultPath) return defaultPath;
      return (files[0] && files[0].path) || null;
    }

    function updateQuery(path) {
      var u = new URL(window.location.href);
      u.searchParams.set("path", path);
      history.replaceState(null, "", u.toString());
    }

    function renderList(files) {
      var q = ($filter.val() || "").toLowerCase().trim();
      var html = files
        .filter(function (f) {
          if (!q) return true;
          return (f.path || "").toLowerCase().indexOf(q) > -1 || (f.name || "").toLowerCase().indexOf(q) > -1;
        })
        .map(function (f) {
          return '<button type="button" class="km-docs-item" data-path="' + f.path + '"><span class="km-docs-item-name">' + f.path + '</span></button>';
        })
        .join("");
      $list.html(html || '<div class="km-docs-empty">没有匹配的文档</div>');
    }

    function setContent(path, md) {
      state.currentPath = path;
      state.currentMd = md || "";
      $title.text(path);
      sourceCodeEl.textContent = state.currentMd;
      if (window.Prism) {
        Prism.highlightElement(sourceCodeEl);
      }
      var html = window.kmMarkdownLite ? window.kmMarkdownLite.render(state.currentMd) : "";
      renderedEl.innerHTML = html;
      if (window.Prism && window.Prism.highlightAllUnder) {
        Prism.highlightAllUnder(renderedEl);
      }
      setActive(path);
      updateQuery(path);
    }

    function loadDoc(path) {
      if (!path) return;
      $.getJSON(urlWithPath(apiFileUrl, path))
        .done(function (res) {
          if (!res || res.status !== "ok") {
            setContent(path, "加载失败");
            return;
          }
          setContent(res.path || path, res.content || "");
        })
        .fail(function () {
          setContent(path, "加载失败");
        });
    }

    $list.on("click", ".km-docs-item", function () {
      var path = $(this).attr("data-path");
      loadDoc(path);
    });

    $rendered.on("click", "a.km-md-link", function (e) {
      var href = $(this).attr("href") || "";
      if (!href) return;
      if (href.indexOf("#") === 0) return;
      if (/\.md($|[?#])/i.test(href) && !/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(href)) {
        e.preventDefault();
        loadDoc(href.replace(/^\//, ""));
      }
    });

    $filter.on("input", function () {
      renderList(state.files);
    });

    $("#docsModeRender").on("click", function () {
      setMode("render");
    });
    $("#docsModeSource").on("click", function () {
      setMode("source");
    });

    setMode("render");
    $.getJSON(apiListUrl).done(function (res) {
      state.files = (res && res.files) || [];
      renderList(state.files);
      var p = pickFromQueryOrDefault(state.files);
      if (p) loadDoc(p);
      else {
        $title.text("docs/ 目录下没有可用的 .md");
        setMode("render");
      }
    });
  });

  

      $(document).ready(function () {
          $("#dashboard").removeClass("active menu-open");
          $("#dashboard").find("ul li").removeClass("active");
          $("#user").addClass("active");
      });

  

  $(document).ready(function () {
    $("#dashboard").removeClass("active menu-open");
    $("#dashboard").find("ul li").removeClass("active");
    $("#docs").addClass("active");

    var apiListUrl = "{% url 'dashboard:docs_api_list' %}";
    var apiFileUrl = "{% url 'dashboard:docs_api_file' %}";
    var defaultPath = "{{ default_doc_path|escapejs }}";

    var $list = $("#docsList");
    var $filter = $("#docsFilterInput");
    var $title = $("#docsTitle");
    var $rendered = $("#docsRendered");
    var $sourcePre = $("#docsSourcePre");
    var sourceCodeEl = document.getElementById("docsSourceCode");
    var renderedEl = document.getElementById("docsRendered");

    var state = {
      files: [],
      mode: "render",
      currentPath: null,
      currentMd: ""
    };

    function setMode(mode) {
      state.mode = mode;
      $("#docsModeRender").toggleClass("is-active", mode === "render");
      $("#docsModeSource").toggleClass("is-active", mode === "source");
      $rendered.toggle(mode === "render");
      $sourcePre.toggle(mode === "source");
    }

    function setActive(path) {
      $list.find(".km-docs-item").removeClass("is-active");
      $list.find('.km-docs-item[data-path="' + path.replace(/"/g, '\\"') + '"]').addClass("is-active");
    }

    function urlWithPath(base, path) {
      return base + (base.indexOf("?") === -1 ? "?" : "&") + "path=" + encodeURIComponent(path);
    }

    function pickFromQueryOrDefault(files) {
      var u = new URL(window.location.href);
      var p = (u.searchParams.get("path") || "").trim();
      if (p) return p;
      if (defaultPath) return defaultPath;
      return (files[0] && files[0].path) || null;
    }

    function updateQuery(path) {
      var u = new URL(window.location.href);
      u.searchParams.set("path", path);
      history.replaceState(null, "", u.toString());
    }

    function renderList(files) {
      var q = ($filter.val() || "").toLowerCase().trim();
      var html = files
        .filter(function (f) {
          if (!q) return true;
          return (f.path || "").toLowerCase().indexOf(q) > -1 || (f.name || "").toLowerCase().indexOf(q) > -1;
        })
        .map(function (f) {
          return '<button type="button" class="km-docs-item" data-path="' + f.path + '"><span class="km-docs-item-name">' + f.path + '</span></button>';
        })
        .join("");
      $list.html(html || '<div class="km-docs-empty">没有匹配的文档</div>');
    }

    function setContent(path, md) {
      state.currentPath = path;
      state.currentMd = md || "";
      $title.text(path);
      sourceCodeEl.textContent = state.currentMd;
      if (window.Prism) {
        Prism.highlightElement(sourceCodeEl);
      }
      var html = window.kmMarkdownLite ? window.kmMarkdownLite.render(state.currentMd) : "";
      renderedEl.innerHTML = html;
      if (window.Prism && window.Prism.highlightAllUnder) {
        Prism.highlightAllUnder(renderedEl);
      }
      setActive(path);
      updateQuery(path);
    }

    function loadDoc(path) {
      if (!path) return;
      $.getJSON(urlWithPath(apiFileUrl, path))
        .done(function (res) {
          if (!res || res.status !== "ok") {
            setContent(path, "加载失败");
            return;
          }
          setContent(res.path || path, res.content || "");
        })
        .fail(function () {
          setContent(path, "加载失败");
        });
    }

    $list.on("click", ".km-docs-item", function () {
      var path = $(this).attr("data-path");
      loadDoc(path);
    });

    $rendered.on("click", "a.km-md-link", function (e) {
      var href = $(this).attr("href") || "";
      if (!href) return;
      if (href.indexOf("#") === 0) return;
      if (/\.md($|[?#])/i.test(href) && !/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(href)) {
        e.preventDefault();
        loadDoc(href.replace(/^\//, ""));
      }
    });

    $filter.on("input", function () {
      renderList(state.files);
    });

    $("#docsModeRender").on("click", function () {
      setMode("render");
    });
    $("#docsModeSource").on("click", function () {
      setMode("source");
    });

    setMode("render");
    $.getJSON(apiListUrl).done(function (res) {
      state.files = (res && res.files) || [];
      renderList(state.files);
      var p = pickFromQueryOrDefault(state.files);
      if (p) loadDoc(p);
      else {
        $title.text("docs/ 目录下没有可用的 .md");
        setMode("render");
      }
    });
  });

  

      $(document).ready(function () {
          $("#dashboard").removeClass("active menu-open");
          $("#dashboard").find("ul li").removeClass("active");
          $("#user").addClass("active");
      });

 