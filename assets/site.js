(function () {
  if (!window.LMS_OPEN) return;
  var params = new URLSearchParams(window.location.search);

  function courseById(id) {
    return window.LMS_COURSES.find(function (course) {
      return course.id === id;
    });
  }

  function presentationById(course, id) {
    return course.presentations.find(function (presentation) {
      return presentation.id === id;
    });
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function showMissing(root, message) {
    root.append(
      el("p", "message", message),
      linkTo("index.html", "Ко всем курсам")
    );
  }

  function linkTo(href, text, className) {
    var link = el("a", className || "text-link", text);
    link.href = href;
    return link;
  }

  function loadCourse(id, onCourse) {
    var course = courseById(id);
    if (course) {
      onCourse(course);
      return;
    }
    fetch("published/catalog.json?v=" + Date.now(), { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("missing");
        return response.json();
      })
      .then(function (catalog) {
        var course = catalog.find(function (item) { return item.id === id; });
        if (!course) throw new Error("missing");
        onCourse(course);
      })
      .catch(function () {
        showMissing(root, "Такого курса нет.");
      });
  }

  function renderCourse(root) {
    loadCourse(params.get("course"), function (course) {
      paintCourse(root, course);
    });
  }

  function paintCourse(root, course) {

    document.title = course.title;
    root.append(el("h1", null, course.title));

    var sections = course.sections || [];
    var byId = {};
    sections.forEach(function (section) { byId[section.id] = section; });
    var hasText = sections.some(function (section) { return section.text; });
    var empty = course.presentations.length === 0 && !hasText && course.tests.length === 0;
    if (empty) {
      root.append(
        el("p", "message", "В этом курсе пока ничего не опубликовано.")
      );
    }

    paintNamedSection(root, "Объявления", byId.announce, "Объявлений пока нет.");

    root.append(el("h2", null, "Презентации"));
    root.append(itemList(course.presentations, function (presentation) {
      return linkTo(
        "slides.html?course=" + encodeURIComponent(course.id) +
          "&presentation=" + encodeURIComponent(presentation.id),
        presentation.title
      );
    }, "Презентаций пока нет."));

    paintNamedSection(root, "Методические материалы", byId.method, "Материалов пока нет.");

    root.append(el("h2", null, "Тесты"));
    root.append(itemList(course.tests, function (test) {
      return linkTo(
        "test.html?course=" + encodeURIComponent(course.id) +
          "&test=" + encodeURIComponent(test.id),
        test.title
      );
    }, "Тестов пока нет."));

    root.append(linkTo("index.html", "Ко всем курсам", "text-link back"));
  }

  function paintNamedSection(root, title, section, emptyText) {
    if (!section) return;
    root.append(el("h2", null, title));
    if (!section.text) root.append(el("p", "empty", emptyText));
    else root.append(reading(section.text));
  }

  function itemList(items, renderItem, emptyText) {
    if (items.length === 0) return el("p", "empty", emptyText);
    var list = el("ul", "items");
    items.forEach(function (item) {
      var li = el("li");
      li.append(renderItem(item));
      list.append(li);
    });
    return list;
  }

  function renderSlides(root) {
    loadCourse(params.get("course"), function (course) {
      paintSlides(root, course);
    });
  }

  function paintSlides(root, course) {
    var presentation = presentationById(course, params.get("presentation"));
    if (!presentation) {
      showMissing(root, "Такой презентации нет.");
      return;
    }

    var index = Number(params.get("slide") || "1");
    if (!Number.isInteger(index)) index = 1;
    index = Math.min(Math.max(index, 1), presentation.slides.length);

    document.title = presentation.title;

    var courseHref = "course.html?course=" + encodeURIComponent(course.id);
    root.append(linkTo(courseHref, course.title, "text-link"));
    root.append(el("h1", null, presentation.title));

    var figure = el("figure", "slide");
    var image = document.createElement("img");
    image.src = presentation.slides[index - 1];
    image.alt = "Слайд " + index + " из " + presentation.slides.length;
    figure.append(image);
    root.append(figure);

    var controls = el("div", "controls");
    controls.append(
      slideButton("Назад", index - 1, index === 1, course, presentation),
      el("p", "counter", "Слайд " + index + " из " + presentation.slides.length),
      slideButton("Дальше", index + 1, index === presentation.slides.length, course, presentation)
    );
    root.append(controls);
  }

  function slideButton(label, slideNumber, disabled, course, presentation) {
    var href = "slides.html?course=" + encodeURIComponent(course.id) +
      "&presentation=" + encodeURIComponent(presentation.id) +
      "&slide=" + slideNumber;
    if (disabled) {
      var span = el("span", "button is-disabled", label);
      span.setAttribute("aria-disabled", "true");
      return span;
    }
    return linkTo(href, label, "button");
  }

  function renderPrompt(parent, fragments) {
    (fragments || []).forEach(function (fragment) {
      if (fragment.type === "formula") {
        var formula = el("span", "formula");
        if (window.katex) {
          window.katex.render(fragment.text || "", formula, { throwOnError: false });
        } else {
          formula.textContent = fragment.text || "";
        }
        parent.append(formula);
        return;
      }
      if (fragment.type === "list") {
        var list = el("ul");
        String(fragment.text || "").split("\n").forEach(function (line) {
          if (!line.trim()) return;
          list.append(el("li", null, line));
        });
        parent.append(list);
        return;
      }
      var tag = fragment.type === "bold" ? "strong" : fragment.type === "italic" ? "em" : "p";
      parent.append(el(tag, null, fragment.text || ""));
    });
  }

  function renderTest(root) {
    loadCourse(params.get("course"), function (course) {
      var test = (course.tests || []).find(function (item) {
        return item.id === params.get("test");
      });
      if (!test) {
        showMissing(root, "Такого теста нет.");
        return;
      }
      paintTest(root, course, test);
    });
  }

  function paintTest(root, course, test) {
    document.title = test.title;
    root.append(linkTo("course.html?course=" + encodeURIComponent(course.id), course.title, "text-link"));
    root.append(el("h1", null, test.title));
    if (test.allowRetake === false) {
      root.append(el("p", "message", "Этот тест можно сдать один раз."));
    }
    var form = el("form", "stack test-form");
    var name = document.createElement("input");
    name.required = true;
    name.placeholder = "Имя";
    form.append(fieldLabel("Имя", name));
    (test.questions || []).forEach(function (question, index) {
      var block = el("fieldset", "question");
      block.dataset.question = question.id;
      var legend = el("legend", null, "Вопрос " + (index + 1));
      block.append(legend);
      renderPrompt(block, question.prompt);
      if (question.image) {
        var figure = document.createElement("img");
        figure.className = "question-figure";
        figure.src = question.image;
        figure.alt = "";
        block.append(figure);
      }
      (question.options || []).forEach(function (option) {
        var choice = el("label", "choice");
        var box = document.createElement("input");
        box.type = "checkbox";
        box.name = question.id;
        box.value = option.id;
        choice.append(box);
        var text = el("span", null, option.text || "");
        choice.append(text);
        if (option.image) {
          var image = document.createElement("img");
          image.src = option.image;
          image.alt = "";
          choice.append(image);
        }
        block.append(choice);
      });
      form.append(block);
    });
    var submit = el("button", "button", "Проверить");
    submit.type = "submit";
    form.append(submit);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var answers = {};
      (test.questions || []).forEach(function (question) {
        answers[question.id] = [];
      });
      form.querySelectorAll("input[type=checkbox]:checked").forEach(function (box) {
        if (!answers[box.name]) answers[box.name] = [];
        answers[box.name].push(box.value);
      });
      var local = grade(test, answers);
      fetch("/api/attempt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          courseId: course.id,
          testId: test.id,
          name: name.value,
          answers: answers,
        }),
      }).then(function (response) {
        return response.json().then(function (payload) {
          return { ok: response.ok, payload: payload };
        });
      }).then(function (result) {
        if (!result.ok && result.payload.error === "identity") {
          root.insertBefore(el("p", "message", "Впишите имя."), form);
          return;
        }
        if (!result.ok && result.payload.error === "retake") {
          root.insertBefore(el("p", "message", "Повторная сдача этого теста закрыта."), form);
          return;
        }
        if (!result.ok) {
          showScore(root, local);
          markQuestions(form, local);
          return;
        }
        showScore(root, result.payload);
        markQuestions(form, local);
      }).catch(function () {
        showScore(root, local);
        markQuestions(form, local);
      });
    });
    root.append(form);
  }

  function grade(test, answers) {
    var score = 0;
    var questions = [];
    (test.questions || []).forEach(function (question) {
      var correct = [];
      (question.options || []).forEach(function (option) {
        if (option.correct) correct.push(option.id);
      });
      var chosen = answers[question.id] || [];
      var same = chosen.length === correct.length;
      chosen.forEach(function (id) {
        if (correct.indexOf(id) < 0) same = false;
      });
      if (same) score += 1;
      questions.push({ id: question.id, ok: same });
    });
    return { score: score, total: (test.questions || []).length, questions: questions };
  }

  function markQuestions(form, result) {
    (result.questions || []).forEach(function (item) {
      var block = null;
      form.querySelectorAll("[data-question]").forEach(function (node) {
        if (node.dataset.question === item.id) block = node;
      });
      if (!block) return;
      var note = block.querySelector(".question-result");
      if (!note) {
        note = el("p", "question-result", "");
        block.append(note);
      }
      note.textContent = item.ok ? "Верно" : "Неверно";
      note.className = item.ok ? "question-result is-right" : "question-result is-wrong";
    });
  }

  function showScore(root, result) {
    root.querySelectorAll(".score-line").forEach(function (node) { node.remove(); });
    var sent = el("p", "message score-line", "Отправлено");
    var score = el("p", "score score-line", "Правильных ответов: " + result.score + " из " + result.total);
    root.insertBefore(score, root.querySelector(".test-form"));
    root.insertBefore(sent, score);
  }

  function reading(text) {
    var box = el("div", "reading");
    if (!window.LMS_RICH || !window.LMS_RICH.looksRich(text)) {
      box.classList.add("reading-plain");
      box.textContent = text || "";
      return box;
    }
    window.LMS_RICH.append(box, text);
    return box;
  }

  function fieldLabel(text, input) {
    var label = el("label", null, text);
    label.append(input);
    return label;
  }

  var root = document.getElementById("app");
  var page = document.body.dataset.page;
  if (page === "course") renderCourse(root);
  if (page === "slides") renderSlides(root);
  if (page === "test") renderTest(root);
})();
