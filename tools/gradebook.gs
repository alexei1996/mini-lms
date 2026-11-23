// Ведомость. Вставить в Расширения → Apps Script у таблицы учителя.
// Пароль Google сюда не входит. Адрес развёрнутого сценария потом попадает в код сайта.

var MAP_SHEET = "_редакции";

function doGet() {
  return json({ ok: true });
}

function doPost(e) {
  try {
    var body = JSON.parse(e.postData && e.postData.contents ? e.postData.contents : "{}");
    return json(recordGrade(body));
  } catch (error) {
    return json({ ok: false, error: "bad" });
  }
}

function recordGrade(body) {
  var name = cleanName(body.name);
  if (!name) return { ok: false, error: "identity" };
  var score = Number(body.score);
  var total = Number(body.total);
  if (!isFinite(score) || !isFinite(total) || total < 1 || Math.floor(total) !== total) {
    return { ok: false, error: "score" };
  }
  var edition = String(body.edition || "").trim();
  if (!edition) return { ok: false, error: "edition" };

  var book = SpreadsheetApp.getActive();
  var sheet = sheetForEdition(book, body, edition, total);
  if (body.allowRetake === false && hasName(sheet, name)) {
    return { ok: false, error: "retake" };
  }
  var rowNumber = sheet.getLastRow();
  var when = Utilities.formatDate(new Date(), "Europe/Moscow", "dd.MM.yyyy HH:mm");
  sheet.appendRow([rowNumber, name, Math.trunc(score), when]);
  return { ok: true };
}

function sheetForEdition(book, body, edition, total) {
  var map = mapSheet(book);
  var found = findEdition(map, edition);
  if (found) {
    var existing = book.getSheetByName(found);
    if (existing) return existing;
  }
  var title = sheetTitle(body);
  var created = book.insertSheet(title);
  created.appendRow(["№", "ФИО", "Результат (" + total + ")", "Дата"]);
  created.setFrozenRows(1);
  map.appendRow([edition, title]);
  return created;
}

function sheetTitle(body) {
  var course = cleanName(body.courseTitle) || "Курс";
  var test = cleanName(body.testTitle) || "Тест";
  var base = fitSheetName(course + " — " + test);
  var book = SpreadsheetApp.getActive();
  if (!book.getSheetByName(base)) return base;
  var published = String(body.publishedOn || "").trim();
  if (!published) {
    published = Utilities.formatDate(new Date(), "Europe/Moscow", "yyyy-MM-dd");
  }
  var withDate = fitSheetName(base + " " + published);
  if (!book.getSheetByName(withDate)) return withDate;
  var counter = 2;
  while (book.getSheetByName(fitSheetName(withDate + " " + counter))) counter++;
  return fitSheetName(withDate + " " + counter);
}

function fitSheetName(name) {
  var cleaned = String(name).replace(/[:\\\/\?\*\[\]]/g, " ").replace(/\s+/g, " ").trim();
  if (!cleaned) cleaned = "Тест";
  return cleaned.slice(0, 99);
}

function mapSheet(book) {
  var sheet = book.getSheetByName(MAP_SHEET);
  if (!sheet) {
    sheet = book.insertSheet(MAP_SHEET);
    sheet.appendRow(["edition", "sheet"]);
    sheet.hideSheet();
  }
  return sheet;
}

function findEdition(map, edition) {
  var values = map.getDataRange().getValues();
  var index;
  for (index = 1; index < values.length; index++) {
    if (String(values[index][0]) === edition) return String(values[index][1]);
  }
  return "";
}

function hasName(sheet, name) {
  var values = sheet.getDataRange().getValues();
  var index;
  for (index = 1; index < values.length; index++) {
    if (cleanName(values[index][1]) === name) return true;
  }
  return false;
}

function cleanName(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function json(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
