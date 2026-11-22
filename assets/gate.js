(function () {
  var word = "hep2026";
  var open = false;
  try {
    open = localStorage.getItem("lms-entry") === "1";
  } catch (error) {
    open = false;
  }
  window.LMS_OPEN = open;
  if (open) return;
  var main = document.querySelector("main");
  if (!main) return;
  main.replaceChildren();
  var title = document.createElement("h1");
  title.textContent = "Вход на сайт";
  var message = document.createElement("p");
  message.className = "message";
  message.hidden = true;
  var form = document.createElement("form");
  form.className = "stack";
  var input = document.createElement("input");
  input.type = "password";
  input.required = true;
  input.autocomplete = "off";
  input.placeholder = "Кодовое слово";
  var button = document.createElement("button");
  button.className = "button";
  button.type = "submit";
  button.textContent = "Войти";
  form.append(input, button);
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (input.value.trim() !== word) {
      message.hidden = false;
      message.textContent = "Неверное кодовое слово.";
      return;
    }
    try {
      localStorage.setItem("lms-entry", "1");
    } catch (error) {}
    window.location.reload();
  });
  main.append(title, message, form);
})();
