 

$(document).ready(function () {
  $("#dashboard").removeClass("active menu-open");
  $("#dashboard").find("ul li").removeClass("active");
  $("#tasks").addClass("menu-open");
  $("#tasks").find("ul").find("li#task_new").addClass("active");
  $("#tasks").find("ul").css("display","block");

  var btn = document.getElementById('toggleAdvanced');
  var panel = document.getElementById('advancedPanel');
  var arrow = document.getElementById('advancedArrow');
  var sub = document.getElementById('advancedSub');
  if (btn && panel) {
    function toggleAdvanced() {
      var open = panel.style.display !== 'none';
      panel.style.display = open ? 'none' : 'block';
      btn.setAttribute('aria-expanded', open ? 'false' : 'true');
      if (sub) {
        sub.textContent = open ? '点击展开' : '点击收起';
      }
      if (arrow) {
        arrow.className = open ? 'km-advanced-arrow' : 'km-advanced-arrow is-open';
      }
    }
    btn.addEventListener('click', toggleAdvanced);
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleAdvanced();
      }
    });
  }
});

  

function delVul(vulid){
  $.get("{% url 'dashboard:vul_del' 654321 %}".replace('654321', vulid), function(data){
      if(data.code == 200){
          location.reload();
      }else{
          alert(data.message)
      }
  })
}

$(document).ready(function(){
  $("#dashboard").removeClass("active menu-open");
  $("#dashboard").find("ul li").removeClass("active");
  $("#tasks").addClass("menu-open");
  $("#tasks").find("ul").find("li#task_list").addClass("active");
  $("#tasks").find("ul").css("display","block");

  $("button#result").click(function () {
      location.href = "{% url 'backend:tasklog' task.id %}?token={{ visit_token }}";
    });

});

  

$(document).ready(function () {
  $("#dashboard").removeClass("active menu-open");
  $("#dashboard").find("ul li").removeClass("active");
  $("#tasks").addClass("menu-open");
  $("#tasks").find("ul").find("li#task_new").addClass("active");
  $("#tasks").find("ul").css("display","block");

  var dz = document.getElementById('dropzone');
  var input = document.getElementById('archiveInput');
  var nameBox = document.getElementById('fileName');
  var statusBox = document.getElementById('uploadStatus');
  var form = document.getElementById('uploadForm');
  var submitting = false;

  function submitNow() {
    if (submitting) return;
    submitting = true;
    statusBox.textContent = '正在上传并准备项目，请稍候...';
    dz.style.pointerEvents = 'none';
    dz.style.opacity = '0.72';
    form.submit();
  }

  function setFile(f) {
    if (!f) return;
    nameBox.textContent = '已选择：' + f.name;
    setTimeout(function () {
      submitNow();
    }, 150);
  }

  dz.addEventListener('click', function () {
    input.click();
  });

  input.addEventListener('change', function () {
    if (input.files && input.files[0]) setFile(input.files[0]);
  });

  dz.addEventListener('dragover', function (e) {
    e.preventDefault();
    dz.style.background = '#f0f7ff';
  });

  dz.addEventListener('dragleave', function (e) {
    e.preventDefault();
    dz.style.background = '#fafafa';
  });

  dz.addEventListener('drop', function (e) {
    e.preventDefault();
    dz.style.background = '#fafafa';
    if (!e.dataTransfer || !e.dataTransfer.files || !e.dataTransfer.files[0]) return;
    input.files = e.dataTransfer.files;
    setFile(e.dataTransfer.files[0]);
  });

  form.addEventListener('submit', function () {
    if (submitting) return;
    submitNow();
  });
});

  

      $(document).ready(function () {
          $("#dashboard").removeClass("active menu-open");
          $("#dashboard").find("ul li").removeClass("active");
          $("#tasks").addClass("menu-open");
          $("#tasks").find("ul").find("li#task_list").addClass("active");
          $("#tasks").find("ul").css("display","block");

          $("#allTaskFilterInput").on("input", function () {
              var text = $(this).val().toLowerCase();
              $("#allTaskTable tbody tr").each(function () {
                  var rowText = $(this).text().toLowerCase();
                  $(this).toggle(rowText.indexOf(text) > -1);
              });
          });
      });

  

$(document).ready(function () {
  $("#dashboard").removeClass("active menu-open");
  $("#dashboard").find("ul li").removeClass("active");
  $("#tasks").addClass("menu-open");
  $("#tasks").find("ul").find("li#task_new").addClass("active");
  $("#tasks").find("ul").css("display","block");

  var btn = document.getElementById('toggleAdvanced');
  var panel = document.getElementById('advancedPanel');
  var arrow = document.getElementById('advancedArrow');
  var sub = document.getElementById('advancedSub');
  if (btn && panel) {
    function toggleAdvanced() {
      var open = panel.style.display !== 'none';
      panel.style.display = open ? 'none' : 'block';
      btn.setAttribute('aria-expanded', open ? 'false' : 'true');
      if (sub) {
        sub.textContent = open ? '点击展开' : '点击收起';
      }
      if (arrow) {
        arrow.className = open ? 'km-advanced-arrow' : 'km-advanced-arrow is-open';
      }
    }
    btn.addEventListener('click', toggleAdvanced);
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleAdvanced();
      }
    });
  }
});

  

function delVul(vulid){
  $.get("{% url 'dashboard:vul_del' 654321 %}".replace('654321', vulid), function(data){
      if(data.code == 200){
          location.reload();
      }else{
          alert(data.message)
      }
  })
}

$(document).ready(function(){
  $("#dashboard").removeClass("active menu-open");
  $("#dashboard").find("ul li").removeClass("active");
  $("#tasks").addClass("menu-open");
  $("#tasks").find("ul").find("li#task_list").addClass("active");
  $("#tasks").find("ul").css("display","block");

  $("button#result").click(function () {
      location.href = "{% url 'backend:tasklog' task.id %}?token={{ visit_token }}";
    });

});

  

$(document).ready(function () {
  $("#dashboard").removeClass("active menu-open");
  $("#dashboard").find("ul li").removeClass("active");
  $("#tasks").addClass("menu-open");
  $("#tasks").find("ul").find("li#task_new").addClass("active");
  $("#tasks").find("ul").css("display","block");

  var dz = document.getElementById('dropzone');
  var input = document.getElementById('archiveInput');
  var nameBox = document.getElementById('fileName');
  var statusBox = document.getElementById('uploadStatus');
  var form = document.getElementById('uploadForm');
  var submitting = false;

  function submitNow() {
    if (submitting) return;
    submitting = true;
    statusBox.textContent = '正在上传并准备项目，请稍候...';
    dz.style.pointerEvents = 'none';
    dz.style.opacity = '0.72';
    form.submit();
  }

  function setFile(f) {
    if (!f) return;
    nameBox.textContent = '已选择：' + f.name;
    setTimeout(function () {
      submitNow();
    }, 150);
  }

  dz.addEventListener('click', function () {
    input.click();
  });

  input.addEventListener('change', function () {
    if (input.files && input.files[0]) setFile(input.files[0]);
  });

  dz.addEventListener('dragover', function (e) {
    e.preventDefault();
    dz.style.background = '#f0f7ff';
  });

  dz.addEventListener('dragleave', function (e) {
    e.preventDefault();
    dz.style.background = '#fafafa';
  });

  dz.addEventListener('drop', function (e) {
    e.preventDefault();
    dz.style.background = '#fafafa';
    if (!e.dataTransfer || !e.dataTransfer.files || !e.dataTransfer.files[0]) return;
    input.files = e.dataTransfer.files;
    setFile(e.dataTransfer.files[0]);
  });

  form.addEventListener('submit', function () {
    if (submitting) return;
    submitNow();
  });
});

  

      $(document).ready(function () {
          $("#dashboard").removeClass("active menu-open");
          $("#dashboard").find("ul li").removeClass("active");
          $("#tasks").addClass("menu-open");
          $("#tasks").find("ul").find("li#task_list").addClass("active");
          $("#tasks").find("ul").css("display","block");

          $("#allTaskFilterInput").on("input", function () {
              var text = $(this).val().toLowerCase();
              $("#allTaskTable tbody tr").each(function () {
                  var rowText = $(this).text().toLowerCase();
                  $(this).toggle(rowText.indexOf(text) > -1);
              });
          });
      });

  

$(document).ready(function () {
  $("#dashboard").removeClass("active menu-open");
  $("#dashboard").find("ul li").removeClass("active");
  $("#tasks").addClass("menu-open");
  $("#tasks").find("ul").find("li#task_new").addClass("active");
  $("#tasks").find("ul").css("display","block");

  var btn = document.getElementById('toggleAdvanced');
  var panel = document.getElementById('advancedPanel');
  var arrow = document.getElementById('advancedArrow');
  var sub = document.getElementById('advancedSub');
  if (btn && panel) {
    function toggleAdvanced() {
      var open = panel.style.display !== 'none';
      panel.style.display = open ? 'none' : 'block';
      btn.setAttribute('aria-expanded', open ? 'false' : 'true');
      if (sub) {
        sub.textContent = open ? '点击展开' : '点击收起';
      }
      if (arrow) {
        arrow.className = open ? 'km-advanced-arrow' : 'km-advanced-arrow is-open';
      }
    }
    btn.addEventListener('click', toggleAdvanced);
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleAdvanced();
      }
    });
  }
});

  

function delVul(vulid){
  $.get("{% url 'dashboard:vul_del' 654321 %}".replace('654321', vulid), function(data){
      if(data.code == 200){
          location.reload();
      }else{
          alert(data.message)
      }
  })
}

$(document).ready(function(){
  $("#dashboard").removeClass("active menu-open");
  $("#dashboard").find("ul li").removeClass("active");
  $("#tasks").addClass("menu-open");
  $("#tasks").find("ul").find("li#task_list").addClass("active");
  $("#tasks").find("ul").css("display","block");

  $("button#result").click(function () {
      location.href = "{% url 'backend:tasklog' task.id %}?token={{ visit_token }}";
    });

});

  

$(document).ready(function () {
  $("#dashboard").removeClass("active menu-open");
  $("#dashboard").find("ul li").removeClass("active");
  $("#tasks").addClass("menu-open");
  $("#tasks").find("ul").find("li#task_new").addClass("active");
  $("#tasks").find("ul").css("display","block");

  var dz = document.getElementById('dropzone');
  var input = document.getElementById('archiveInput');
  var nameBox = document.getElementById('fileName');
  var statusBox = document.getElementById('uploadStatus');
  var form = document.getElementById('uploadForm');
  var submitting = false;

  function submitNow() {
    if (submitting) return;
    submitting = true;
    statusBox.textContent = '正在上传并准备项目，请稍候...';
    dz.style.pointerEvents = 'none';
    dz.style.opacity = '0.72';
    form.submit();
  }

  function setFile(f) {
    if (!f) return;
    nameBox.textContent = '已选择：' + f.name;
    setTimeout(function () {
      submitNow();
    }, 150);
  }

  dz.addEventListener('click', function () {
    input.click();
  });

  input.addEventListener('change', function () {
    if (input.files && input.files[0]) setFile(input.files[0]);
  });

  dz.addEventListener('dragover', function (e) {
    e.preventDefault();
    dz.style.background = '#f0f7ff';
  });

  dz.addEventListener('dragleave', function (e) {
    e.preventDefault();
    dz.style.background = '#fafafa';
  });

  dz.addEventListener('drop', function (e) {
    e.preventDefault();
    dz.style.background = '#fafafa';
    if (!e.dataTransfer || !e.dataTransfer.files || !e.dataTransfer.files[0]) return;
    input.files = e.dataTransfer.files;
    setFile(e.dataTransfer.files[0]);
  });

  form.addEventListener('submit', function () {
    if (submitting) return;
    submitNow();
  });
});

  

      $(document).ready(function () {
          $("#dashboard").removeClass("active menu-open");
          $("#dashboard").find("ul li").removeClass("active");
          $("#tasks").addClass("menu-open");
          $("#tasks").find("ul").find("li#task_list").addClass("active");
          $("#tasks").find("ul").css("display","block");

          $("#allTaskFilterInput").on("input", function () {
              var text = $(this).val().toLowerCase();
              $("#allTaskTable tbody tr").each(function () {
                  var rowText = $(this).text().toLowerCase();
                  $(this).toggle(rowText.indexOf(text) > -1);
              });
          });
      });

 