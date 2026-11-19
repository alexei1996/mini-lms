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
    Promise.all([api("/api/courses"), api("/api/attempts")]).then(function (results) {
      var result = results[0];
      var attempts = results[1].ok ? results[1].payload : [];
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
        root.append(courseCard(course, attempts));
      });
      root.append(homeLink());
    });
  }

  function courseCard(course, attempts) {
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

    card.append(testsBlock(course, attempts));
    return card;
  }

  function testsBlock(course, attempts) {
    var block = el("section");
    block.append(el("h3", null, "Тесты"));
    var createRow = el("div", "row");
    var title = document.createElement("input");
    title.placeholder = "Название теста";
    var create = el("button", "button", "Создать тест");
    create.type = "button";
    create.addEventListener("click", function () {
      api("/api/tests", { courseId: course.id, title: title.value }).then(showCourses);
    });
    createRow.append(title, create);
    block.append(createRow);
    if (!course.tests || course.tests.length === 0) {
      block.append(el("p", "empty", "Тестов пока нет."));
      return block;
    }
    course.tests.forEach(function (test) {
      block.append(testEditor(course, test, attempts));
    });
    return block;
  }

  function testEditor(course, test, attempts) {
    var card = el("div", "question");
    var head = el("div", "row");
    var title = document.createElement("input");
    title.value = test.title || "";
    head.append(title);
    head.append(removeButton("Удалить тест «" + (test.title || "Тест") + "»?", {
      courseId: course.id,
      testId: test.id,
    }));
    card.append(head);
    var retake = document.createElement("input");
    retake.type = "checkbox";
    retake.checked = test.allowRetake !== false;
    var retakeLabel = el("label", "choice", "Можно сдать ещё раз");
    retakeLabel.prepend(retake);
    card.append(retakeLabel);
    var state = test.published ? "Опубликован" : "Черновик";
    card.append(el("p", null, state));
    var questions = el("div");
    (test.questions || []).forEach(function (question, index) {
      questions.append(questionEditor(question, index));
    });
    card.append(questions);
    var add = el("button", "button button-quiet", "Добавить вопрос");
    add.type = "button";
    add.addEventListener("click", function () {
      questions.append(questionEditor({
        id: "q" + Date.now(),
        prompt: [{ type: "text", text: "" }],
        options: [
          { id: "o1", text: "", image: "", correct: false },
          { id: "o2", text: "", image: "", correct: false },
        ],
      }, questions.children.length));
    });
    var save = el("button", "button", "Сохранить");
    save.type = "button";
    var publish = el("button", "button", test.published ? "Снять с публикации" : "Опубликовать");
    publish.type = "button";
    function send(published) {
      api("/api/tests/save", {
        courseId: course.id,
        testId: test.id,
        title: title.value,
        allowRetake: retake.checked,
        questions: readQuestions(questions),
        published: published,
      }).then(function (result) {
        notice = result.ok
          ? "Тест сохранён."
          : "В каждом вопросе нужно хотя бы два варианта и один верный.";
        showCourses();
      });
    }
    save.addEventListener("click", function () { send(test.published); });
    publish.addEventListener("click", function () { send(!test.published); });
    var actions = el("div", "row");
    actions.append(add, save, publish);
    card.append(actions);
    var mine = (attempts || []).filter(function (attempt) {
      return attempt.courseId === course.id && attempt.testId === test.id;
    });
    if (mine.length) {
      card.append(el("h3", null, "Сдачи"));
      mine.forEach(function (attempt) {
        var line = el("p", null, attempt.submittedAt + " — " + attempt.name + ", " + attempt.email +
          " — " + attempt.score + " из " + attempt.total + ", попытка " + attempt.attemptNumber);
        card.append(line);
        (attempt.snapshot || []).forEach(function (question, index) {
          var chosen = attempt.answers && attempt.answers[question.id] ? attempt.answers[question.id] : [];
          var correct = (question.options || []).filter(function (option) { return option.correct; }).map(function (option) {
            return option.text || option.id;
          }).join(", ");
          var picked = (question.options || []).filter(function (option) {
            return chosen.indexOf(option.id) !== -1;
          }).map(function (option) { return option.text || option.id; }).join(", ");
          card.append(el("p", "empty", "Вопрос " + (index + 1) + ". Выбрано: " + (picked || "ничего") + ". Верно: " + correct));
        });
      });
    }
    return card;
  }

  function questionEditor(question, index) {
    var block = el("fieldset", "question");
    block.dataset.question = question.id;
    block.append(el("legend", null, "Вопрос " + (index + 1)));
    var fragments = el("div");
    (question.prompt || [{ type: "text", text: "" }]).forEach(function (fragment) {
      fragments.append(fragmentEditor(fragment));
    });
    var addFragment = el("button", "button button-quiet", "Добавить фрагмент");
    addFragment.type = "button";
    addFragment.addEventListener("click", function () {
      fragments.append(fragmentEditor({ type: "text", text: "" }));
    });
    block.append(fragments, addFragment);
    var options = el("div");
    (question.options || []).forEach(function (option) {
      options.append(optionEditor(option));
    });
    var count = document.createElement("input");
    count.type = "number";
    count.min = "2";
    count.value = String(Math.max(2, (question.options || []).length));
    var applyCount = el("button", "button button-quiet", "Задать число вариантов");
    applyCount.type = "button";
    applyCount.addEventListener("click", function () {
      var wanted = Math.max(2, Number(count.value) || 2);
      while (options.children.length < wanted) {
        options.append(optionEditor({ id: "o" + Date.now() + options.children.length, text: "", image: "", correct: false }));
      }
      while (options.children.length > wanted) options.removeChild(options.lastElementChild);
    });
    var countRow = el("div", "row");
    countRow.append(count, applyCount);
    block.append(options, countRow);
    return block;
  }

  function fragmentEditor(fragment) {
    var row = el("div", "row");
    row.dataset.fragment = "1";
    var kind = document.createElement("select");
    [["text", "Текст"], ["bold", "Жирный"], ["italic", "Курсив"], ["list", "Список"], ["formula", "Формула"]].forEach(function (item) {
      var option = document.createElement("option");
      option.value = item[0];
      option.textContent = item[1];
      if (item[0] === fragment.type) option.selected = true;
      kind.append(option);
    });
    var text = document.createElement("textarea");
    text.value = fragment.text || "";
    row.append(kind, text);
    return row;
  }

  function optionEditor(option) {
    var row = el("div", "row");
    row.dataset.option = option.id;
    if (option.image) row.dataset.image = option.image;
    var text = document.createElement("input");
    text.type = "text";
    text.value = option.text || "";
    text.placeholder = "Текст варианта";
    var correct = document.createElement("input");
    correct.type = "checkbox";
    correct.checked = !!option.correct;
    var correctLabel = el("label", "choice", "Верный");
    correctLabel.prepend(correct);
    var file = document.createElement("input");
    file.type = "file";
    file.accept = "image/png,image/jpeg";
    file.addEventListener("change", function () {
      var image = file.files && file.files[0];
      if (!image) return;
      var reader = new FileReader();
      reader.onload = function () {
        api("/api/test-image", { contentBase64: String(reader.result).split(",")[1] }).then(function (result) {
          if (result.ok) row.dataset.image = result.payload.id;
        });
      };
      reader.readAsDataURL(image);
    });
    row.append(text, correctLabel, file);
    return row;
  }

  function readQuestions(container) {
    var questions = [];
    container.querySelectorAll("[data-question]").forEach(function (block) {
      var prompt = [];
      block.querySelectorAll("[data-fragment]").forEach(function (row) {
        prompt.push({
          type: row.querySelector("select").value,
          text: row.querySelector("textarea").value,
        });
      });
      var options = [];
      block.querySelectorAll("[data-option]").forEach(function (row) {
        options.push({
          id: row.dataset.option,
          text: row.querySelector("input[type=text]").value,
          image: row.dataset.image || "",
          correct: row.querySelector("input[type=checkbox]").checked,
        });
      });
      questions.push({ id: block.dataset.question, prompt: prompt, options: options });
    });
    return questions;
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
