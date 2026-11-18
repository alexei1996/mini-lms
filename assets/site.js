(function () {
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
    fetch("published/catalog.json")
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

    var empty = course.presentations.length === 0 && course.tests.length === 0;
    if (empty) {
      root.append(
        el("p", "message", "В этом курсе пока ничего не опубликовано.")
      );
    }

    root.append(el("h2", null, "Презентации"));
    root.append(itemList(course.presentations, function (presentation) {
      return linkTo(
        "slides.html?course=" + encodeURIComponent(course.id) +
          "&presentation=" + encodeURIComponent(presentation.id),
        presentation.title
      );
    }, "Презентаций пока нет."));

    root.append(el("h2", null, "Тесты"));
    root.append(itemList(course.tests, function (test) {
      return el("span", null, test.title);
    }, "Тестов пока нет."));

    root.append(linkTo("index.html", "Ко всем курсам", "text-link back"));
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

  var root = document.getElementById("app");
  var page = document.body.dataset.page;
  if (page === "course") renderCourse(root);
  if (page === "slides") renderSlides(root);
})();
