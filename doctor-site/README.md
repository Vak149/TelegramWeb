# Сайт врача-эндокринолога, диетолога

Статический сайт по ТЗ. Генератор на Python 3 без зависимостей — HTML отдаётся поисковику без выполнения JS.

```
python3 build.py           # сборка в dist/ + проверки
python3 build.py --strict  # то же, но падает, пока есть незаполненные [УТОЧНИТЬ]
python3 -m http.server -d dist 8000   # локальный просмотр
```

- `config.py` — данные врача, реквизиты, услуга, контакты, ID Метрики, домен.
- `content.py` — тексты направлений, FAQ, отзывы, статьи.
- `static/` — стили и изображения (положить `img/doctor.webp`, `img/og-doctor.jpg`).

## Что реализовано
Дополнительно: `/preparation` (подготовка), `/materials` (чек-лист анализов, шаблон дневника питания, вопросы врачу — в обмен на контакт), `/calculators` (ИМТ, базовый обмен, HOMA-IR), `/analizy` (8 разборов: ТТГ, свободный Т4, АТ-ТПО, глюкоза, HbA1c, инсулин, HOMA-IR, витамин D), блок видео (`VIDEOS` в `content_extra.py`), блок «Чем я не занимаюсь».

Страницы: `/`, `/about`, `/consultation`, `/faq`, `/reviews`, `/documents`, `/blog` (+11 статей), `/contacts`, `/privacy`, `/offer`, 6 направлений (`/thyroid`, `/diabetes`, `/insulin-resistance`, `/weight`, `/hormones`, `/nutrition`), `/thanks` (noindex).

Schema.org: Physician, MedicalWebPage (с `reviewedBy`), Service+Offer, FAQPage, Article, BreadcrumbList, Organization; Review+AggregateRating — только когда в `content.py` появятся реальные отзывы.

Canonical, OG, sitemap.xml, robots.txt, viewport без блокировки зума, дисклеймер и предупреждение о противопоказаниях на всех страницах, авторская подпись с датами, форма с обязательным согласием на обработку ПД, закреплённая кнопка записи на мобильном.

Проверки при сборке: один H1, уникальные title/description и их длина, запрещённые формулировки, alt у изображений, валидный JSON-LD, зум не заблокирован.

## Цели Яндекс.Метрики
Задать в `YANDEX_METRIKA_ID`. Клики по элементам с `data-goal` отправляются как цели: `phone_click`, `messenger_telegram`, `messenger_whatsapp`, `cta_*`. Отправка формы — цель «посещение /thanks» (настроить в интерфейсе Метрики). Скачивание памятки — цель `memo_download`, заявка на материалы — `lead_materials` (посещение `/materials/thanks`), расчёт в калькуляторе — `calc_bmi`, `calc_bmr`, `calc_homa`.

## До запуска (нужно от клиента / юриста)
Всё, что на сайте подсвечено жёлтым `[УТОЧНИТЬ]` — список из раздела 12 ТЗ. Тексты оферты и политики ПД — шаблоны, их проверяет юрист. Обработчик формы (`FORM_ACTION`) — сервер в РФ или виджет YClients/Dikidi. Хостинг — в РФ.
