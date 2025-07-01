<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Телеграм Бой</title>
  <style>
    body {
      font-family: sans-serif;
      background: #1e1e2f;
      color: #fff;
      margin: 0;
      padding: 20px;
    }
    .title {
      font-size: 24px;
      margin-bottom: 16px;
    }
    .state-table {
      border-collapse: collapse;
      width: 100%;
      margin-bottom: 20px;
    }
    .state-table td, .state-table th {
      border: 1px solid #555;
      padding: 8px;
      text-align: center;
    }
    .state-table td:first-child {
      text-align: left;
    }
    .btn-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }
    button {
      padding: 10px;
      font-size: 16px;
      border: none;
      border-radius: 8px;
      background: #444;
      color: white;
      cursor: pointer;
    }
    button:hover {
      background: #666;
    }
  </style>
</head>
<body>
  <div class="title">🧍‍♂️ Состояние игрока</div>
  <table class="state-table">
    <tr><td>Голова</td><td>✅ В порядке</td></tr>
    <tr><td>Торс</td><td>❌ Перелом</td></tr>
    <tr><td>Левая рука</td><td>🩸 Рана</td></tr>
    <tr><td>Правая рука</td><td>🗡️ Отсечена</td></tr>
    <tr><td>Левая нога</td><td>✅ В порядке</td></tr>
    <tr><td>Правая нога</td><td>✅ В порядке</td></tr>
  </table>

  <div>🎯 Эффекты: Кровотечение</div>
  <div>❤️ HP: <span id="hp">65</span>/100</div>

  <div class="title" style="margin-top: 30px;">🎯 Выберите часть для атаки:</div>
  <div class="btn-grid">
    <button onclick="attack('Голова')">👊 Голова</button>
    <button onclick="attack('Торс')">🛡️ Торс</button>
    <button onclick="attack('Левая рука')">🖐 Левая рука</button>
    <button onclick="attack('Правая рука')">✊ Правая рука</button>
    <button onclick="attack('Левая нога')">🦵 Левая нога</button>
    <button onclick="attack('Правая нога')">🦿 Правая нога</button>
  </div>

  <script>
    function attack(part) {
      alert(`Вы атакуете в: ${part}`);
      // Тут можно будет подключить Telegram WebApp API
      // и отправить выбранную часть на сервер или в Bot API
    }
  </script>
</body>
</html>