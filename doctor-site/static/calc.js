(function () {
  function num(form, name) { return parseFloat(String(form.elements[name].value).replace(",", ".")); }
  function fmt(x, d) { return x.toLocaleString("ru-RU", { maximumFractionDigits: d, minimumFractionDigits: d }); }
  var calcs = {
    bmi: function (f) {
      var w = num(f, "weight"), h = num(f, "height") / 100;
      if (!(w > 0 && h > 0)) return null;
      var v = w / (h * h), cat =
        v < 18.5 ? "ниже нормы" : v < 25 ? "в пределах нормы" : v < 30 ? "избыточная масса тела" : "ожирение";
      return "ИМТ: <strong>" + fmt(v, 1) + "</strong> — по классификации ВОЗ: " + cat + ".";
    },
    bmr: function (f) {
      var w = num(f, "weight"), h = num(f, "height"), a = num(f, "age");
      if (!(w > 0 && h > 0 && a > 0)) return null;
      var v = 10 * w + 6.25 * h - 5 * a + (f.elements.sex.value === "m" ? 5 : -161);
      return "Базовый обмен: <strong>" + fmt(Math.round(v), 0) + " ккал/сутки</strong> (формула Миффлина — Сан Жеора).";
    },
    homa: function (f) {
      var g = num(f, "glucose"), i = num(f, "insulin");
      if (!(g > 0 && i > 0)) return null;
      return "HOMA-IR: <strong>" + fmt(g * i / 22.5, 2) + "</strong>. Единого порога нет — обсудите результат с врачом вместе с другими анализами.";
    }
  };
  document.querySelectorAll("form[data-calc]").forEach(function (f) {
    f.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var out = f.querySelector("output"), r = calcs[f.dataset.calc](f);
      out.innerHTML = r || "Проверьте введённые значения.";
      if (r && window.ym && window.YM_ID) ym(window.YM_ID, "reachGoal", "calc_" + f.dataset.calc);
    });
  });
})();
