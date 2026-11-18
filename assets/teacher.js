(function () {
  var root = document.getElementById("app");

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function clear() {
    root.replaceChildren();
  }

  function api(path, body) {
    var options = { headers: { "Content-Type": "application/json" } };
    if (body !== undefined) {
      options.method = "POST";
      options.body = JSON.stringify(body);
    }
    return fetch(path, options).then(function (response) {
      return response.json().then(function (payload) {
        return { ok: response.ok, status: response.status, payload: payload };
      });
    });
  }

  function showLogin(message) {
    clear();
    root.append(el("h1", null, "Вход учителя"));
    if (message) root.append(el("p", "message", message));
    var form = el("form", "stack");
    var email = field("Почта", "email");
    var password = field("Пароль", "password");
    var submit = el("button", "button", "Войти");
    submit.type = "submit";
    form.append(email.label, password.label, submit);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      api("/api/login", {
        email: email.input.value,
        password: password.input.value,
      }).then(function (result) {
        if (!result.ok) {
          showLogin("Неверная почта или пароль.");
          return;
        }
        showCourses();
      });
    });
    root.append(form);
    root.append(homeLink());
  }

  function field(labelText, type) {
    var label = el("label", null, labelText);
    var input = document.createElement("input");
    input.type = type;
    input.required = true;
    input.autocomplete = type === "password" ? "current-password" : "username";
    label.append(input);
    return { label: label, input: input };
  }

  function homeLink() {
    var link = el("a", "text-link back", "Ко всем курсам");
    link.href = "index.html";
    return link;
  }

  var notice = "";

  function showCourses() {
    api("/api/courses").then(function (result) {
      if (!result.ok) {
        showLogin();
        return;
      }
      clear();
      root.append(el("h1", null, "Курсы учителя"));
      var logout = el("button", "button button-quiet", "Выйти");
      logout.type = "button";
      logout.addEventListener("click", function () {
        api("/api/logout", {}).then(function () { showLogin(); });
      });
      root.append(logout);
      if (notice) {
        root.append(el("p", "message", notice));
        notice = "";
      }

      var form = el("form", "stack");
      var title = document.createElement("input");
      title.required = true;
      title.placeholder = "Название курса";
      var create = el("button", "button", "Создать курс");
      create.type = "submit";
      form.append(title, create);
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        api("/api/courses", { title: title.value }).then(function (created) {
          if (created.ok) showCourses();
        });
      });
      root.append(form);

      result.payload.forEach(function (course) {
        root.append(courseCard(course));
      });
      root.append(homeLink());
    });
  }

  function courseCard(course) {
    var card = el("section", "card");
    card.append(el("h2", null, course.title));
    var link = el("a", "text-link", "Ссылка для ученика");
    link.href = "course.html?course=" + encodeURIComponent(course.id);
    card.append(link);

    card.append(uploadControl(course));
    if (course.presentations.length === 0) {
      var add = el("button", "button", "Добавить подготовленную презентацию");
      add.type = "button";
      add.addEventListener("click", function () {
        api("/api/presentations", { courseId: course.id }).then(showCourses);
      });
      card.append(add);
    }

    course.presentations.forEach(function (presentation) {
      var row = el("div", "row");
      var state = presentation.published ? "Опубликована" : "Черновик";
      row.append(el("p", null, presentation.title + " — " + state));
      var toggle = el("button", "button", presentation.published ? "Снять с публикации" : "Опубликовать");
      toggle.type = "button";
      toggle.addEventListener("click", function () {
        api("/api/publish", {
          courseId: course.id,
          presentationId: presentation.id,
          published: !presentation.published,
        }).then(showCourses);
      });
      row.append(toggle);
      if (presentation.slides && presentation.slides.length) {
        var thumbs = el("div", "thumbs");
        presentation.slides.forEach(function (src, index) {
          var image = document.createElement("img");
          image.src = src;
          image.alt = "Слайд " + (index + 1);
          thumbs.append(image);
        });
        row.append(thumbs);
      }
      card.append(row);
    });
    return card;
  }

  function uploadControl(course) {
    var label = el("label", "button file-button", "Открыть");
    var input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,.pptx,application/pdf";
    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function () {
        var encoded = String(reader.result).split(",")[1];
        api("/api/upload", {
          courseId: course.id,
          filename: file.name,
          contentBase64: encoded,
        }).then(function (result) {
          notice = result.ok ? "" : "Можно загрузить только PDF или PowerPoint.";
          showCourses();
        });
      };
      reader.readAsDataURL(file);
    });
    label.append(input);
    return label;
  }

  api("/api/me").then(function (result) {
    if (result.ok && result.payload.signedIn) showCourses();
    else showLogin();
  }).catch(function () {
    showLogin("Сервер входа не запущен.");
  });
})();
