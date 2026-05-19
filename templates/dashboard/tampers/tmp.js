 

      $(document).ready(function () {
          $("#dashboard").removeClass("active menu-open");
          $("#dashboard").find("ul li").removeClass("active");
          $("#tampers").addClass("menu-open");
          $("#tampers").find("ul").find("li#tamper_list").addClass("active");
          $("#tampers").find("ul").css("display","block");

          var $list = $("#tamperList");
          var $detailTitle = $("#tamperDetailTitle");
          var detailCodeEl = document.getElementById("tamperDetailCode");

          function setActive($btn) {
              $list.find(".km-tamper-item").removeClass("is-active");
              $btn.addClass("is-active");
          }

          function showDetail($btn) {
              var id = String($btn.attr("data-id") || "").trim();
              var name = $("#tamperName" + id).val() || "";
              var filterText = $("#tamperFilter" + id).val() || "";
              var inputText = $("#tamperInput" + id).val() || "";
              $detailTitle.text(name + (id ? ("  #" + id) : ""));
              detailCodeEl.textContent = 'tamper_name = "' + name + '"\n' + 'filter_function = ' + filterText + '\n' + 'input_control = ' + inputText;
              if (window.Prism) {
                  Prism.highlightElement(detailCodeEl);
              }
          }

          function pickFirstVisible() {
              var $first = $list.find(".km-tamper-item:visible").first();
              if ($first.length) {
                  setActive($first);
                  showDetail($first);
              } else {
                  $list.find(".km-tamper-item").removeClass("is-active");
                  $detailTitle.text("没有匹配的拓展插件");
                  detailCodeEl.textContent = "";
              }
          }

          $list.on("click", ".km-tamper-item", function () {
              var $btn = $(this);
              setActive($btn);
              showDetail($btn);
          });

          $("#tamperFilterInput").on("input", function () {
              var q = ($(this).val() || "").toLowerCase().trim();
              $list.find(".km-tamper-item").each(function () {
                  var $btn = $(this);
                  var name = ($btn.attr("data-name") || "");
                  var id = String($btn.attr("data-id") || "");
                  var ok = !q || name.indexOf(q) > -1 || id.indexOf(q) > -1;
                  $btn.toggle(ok);
              });
              pickFirstVisible();
          });

          $("#tamperCopyBtn").on("click", function () {
              var text = detailCodeEl.textContent || "";
              if (!text) return;
              if (navigator.clipboard && navigator.clipboard.writeText) {
                  navigator.clipboard.writeText(text);
              } else {
                  var $tmp = $("<textarea>");
                  $("body").append($tmp);
                  $tmp.val(text).select();
                  document.execCommand("copy");
                  $tmp.remove();
              }
          });

          pickFirstVisible();
      });

  

      $(document).ready(function () {
          $("#dashboard").removeClass("active menu-open");
          $("#dashboard").find("ul li").removeClass("active");
          $("#tampers").addClass("menu-open");
          $("#tampers").find("ul").find("li#tamper_list").addClass("active");
          $("#tampers").find("ul").css("display","block");

          var $list = $("#tamperList");
          var $detailTitle = $("#tamperDetailTitle");
          var detailCodeEl = document.getElementById("tamperDetailCode");

          function setActive($btn) {
              $list.find(".km-tamper-item").removeClass("is-active");
              $btn.addClass("is-active");
          }

          function showDetail($btn) {
              var id = String($btn.attr("data-id") || "").trim();
              var name = $("#tamperName" + id).val() || "";
              var filterText = $("#tamperFilter" + id).val() || "";
              var inputText = $("#tamperInput" + id).val() || "";
              $detailTitle.text(name + (id ? ("  #" + id) : ""));
              detailCodeEl.textContent = 'tamper_name = "' + name + '"\n' + 'filter_function = ' + filterText + '\n' + 'input_control = ' + inputText;
              if (window.Prism) {
                  Prism.highlightElement(detailCodeEl);
              }
          }

          function pickFirstVisible() {
              var $first = $list.find(".km-tamper-item:visible").first();
              if ($first.length) {
                  setActive($first);
                  showDetail($first);
              } else {
                  $list.find(".km-tamper-item").removeClass("is-active");
                  $detailTitle.text("没有匹配的拓展插件");
                  detailCodeEl.textContent = "";
              }
          }

          $list.on("click", ".km-tamper-item", function () {
              var $btn = $(this);
              setActive($btn);
              showDetail($btn);
          });

          $("#tamperFilterInput").on("input", function () {
              var q = ($(this).val() || "").toLowerCase().trim();
              $list.find(".km-tamper-item").each(function () {
                  var $btn = $(this);
                  var name = ($btn.attr("data-name") || "");
                  var id = String($btn.attr("data-id") || "");
                  var ok = !q || name.indexOf(q) > -1 || id.indexOf(q) > -1;
                  $btn.toggle(ok);
              });
              pickFirstVisible();
          });

          $("#tamperCopyBtn").on("click", function () {
              var text = detailCodeEl.textContent || "";
              if (!text) return;
              if (navigator.clipboard && navigator.clipboard.writeText) {
                  navigator.clipboard.writeText(text);
              } else {
                  var $tmp = $("<textarea>");
                  $("body").append($tmp);
                  $tmp.val(text).select();
                  document.execCommand("copy");
                  $tmp.remove();
              }
          });

          pickFirstVisible();
      });

  

      $(document).ready(function () {
          $("#dashboard").removeClass("active menu-open");
          $("#dashboard").find("ul li").removeClass("active");
          $("#tampers").addClass("menu-open");
          $("#tampers").find("ul").find("li#tamper_list").addClass("active");
          $("#tampers").find("ul").css("display","block");

          var $list = $("#tamperList");
          var $detailTitle = $("#tamperDetailTitle");
          var detailCodeEl = document.getElementById("tamperDetailCode");

          function setActive($btn) {
              $list.find(".km-tamper-item").removeClass("is-active");
              $btn.addClass("is-active");
          }

          function showDetail($btn) {
              var id = String($btn.attr("data-id") || "").trim();
              var name = $("#tamperName" + id).val() || "";
              var filterText = $("#tamperFilter" + id).val() || "";
              var inputText = $("#tamperInput" + id).val() || "";
              $detailTitle.text(name + (id ? ("  #" + id) : ""));
              detailCodeEl.textContent = 'tamper_name = "' + name + '"\n' + 'filter_function = ' + filterText + '\n' + 'input_control = ' + inputText;
              if (window.Prism) {
                  Prism.highlightElement(detailCodeEl);
              }
          }

          function pickFirstVisible() {
              var $first = $list.find(".km-tamper-item:visible").first();
              if ($first.length) {
                  setActive($first);
                  showDetail($first);
              } else {
                  $list.find(".km-tamper-item").removeClass("is-active");
                  $detailTitle.text("没有匹配的拓展插件");
                  detailCodeEl.textContent = "";
              }
          }

          $list.on("click", ".km-tamper-item", function () {
              var $btn = $(this);
              setActive($btn);
              showDetail($btn);
          });

          $("#tamperFilterInput").on("input", function () {
              var q = ($(this).val() || "").toLowerCase().trim();
              $list.find(".km-tamper-item").each(function () {
                  var $btn = $(this);
                  var name = ($btn.attr("data-name") || "");
                  var id = String($btn.attr("data-id") || "");
                  var ok = !q || name.indexOf(q) > -1 || id.indexOf(q) > -1;
                  $btn.toggle(ok);
              });
              pickFirstVisible();
          });

          $("#tamperCopyBtn").on("click", function () {
              var text = detailCodeEl.textContent || "";
              if (!text) return;
              if (navigator.clipboard && navigator.clipboard.writeText) {
                  navigator.clipboard.writeText(text);
              } else {
                  var $tmp = $("<textarea>");
                  $("body").append($tmp);
                  $tmp.val(text).select();
                  document.execCommand("copy");
                  $tmp.remove();
              }
          });

          pickFirstVisible();
      });

 