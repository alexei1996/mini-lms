fetch("published/catalog.json?v=" + Date.now(), { cache: "no-store" })
  .then(function (response) {
    if (!response.ok) throw new Error("missing");
    return response.json();
  })
  .then(function (courses) {
    var catalog = document.getElementById("catalog");
    courses.forEach(function (course) {
      var link = document.createElement("a");
      link.href = "course.html?course=" + encodeURIComponent(course.id);
      link.textContent = course.title;
      catalog.append(link);
    });
  })
  .catch(function () {});
