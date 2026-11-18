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
    var titleRow = el("div", "row");
    titleRow.append(el("h2", null, course.title));
    titleRow.append(removeButton("Удалить курс «" + course.title + "»?", {
      courseId: course.id,
    }));
    card.append(titleRow);
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
      row.append(removeButton("Удалить презентацию «" + presentation.title + "»?", {
        courseId: course.id,
        presentationId: presentation.id,
      }));
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

    card.append(materialsEditor(course));

    card.append(el("h3", null, "Тесты"));
    if (!course.tests || course.tests.length === 0) {
      card.append(el("p", "empty", "Тестов пока нет."));
    } else {
      course.tests.forEach(function (test) {
        var testRow = el("div", "row");
        testRow.append(el("p", null, test.title));
        testRow.append(removeButton("Удалить тест «" + test.title + "»?", {
          courseId: course.id,
          testId: test.id,
        }));
        card.append(testRow);
      });
    }
    return card;
  }

  function materialsEditor(course) {
    var section = (course.sections || []).filter(function (item) {
      return item.id === "method";
    })[0] || { id: "method", text: "", published: false };
    var block = el("section", null);
    block.append(el("h3", null, "Методические материалы"));
    var state = section.published ? "Опубликованы" : "Черновик";
    block.append(el("p", null, state));
    var area = document.createElement("textarea");
    area.value = section.text || "";
    var row = el("div", "row");
    var save = el("button", "button", "Сохранить");
    save.type = "button";
    save.addEventListener("click", function () {
      sendSection(course.id, section.id, area.value, section.published);
    });
    var toggle = el("button", "button", section.published ? "Снять с публикации" : "Опубликовать");
    toggle.type = "button";
    toggle.addEventListener("click", function () {
      sendSection(course.id, section.id, area.value, !section.published);
    });
    row.append(save, toggle);
    block.append(area, row);
    return block;
  }

  function sendSection(courseId, sectionId, text, published) {
    api("/api/section", {
      courseId: courseId,
      sectionId: sectionId,
      text: text,
      published: published,
    }).then(function (result) {
      notice = result.ok ? "Текст раздела сохранён." : "Не удалось сохранить раздел.";
      showCourses();
    });
  }

  function removeButton(question, body) {
    var button = el("button", "button button-quiet", "Удалить");
    button.type = "button";
    button.addEventListener("click", function () {
      if (!window.confirm(question)) return;
      api("/api/delete", body).then(showCourses);
    });
    return button;
  }

  function uploadControl(course) {
    var label = el("label", "button file-button", "Открыть");
    var input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,.pptx,application/pdf";
    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!file) return;
      var wait = el("p", "message", "Готовим картинки слайдов. Это может занять минуту.");
      label.after(wait);
      var reader = new FileReader();
      reader.onload = function () {
        var encoded = String(reader.result).split(",")[1];
        api("/api/upload", {
          courseId: course.id,
          filename: file.name,
          contentBase64: encoded,
        }).then(function (result) {
          if (result.ok) notice = "";
          else if (result.payload && result.payload.error === "render") {
            notice = "Не удалось нарисовать слайды. Закройте PowerPoint и загрузите файл ещё раз.";
          } else notice = "Можно загрузить только PDF или PowerPoint.";
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
