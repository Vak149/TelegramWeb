#!/usr/bin/env python3
"""Генератор статического сайта врача. Без зависимостей: python3 build.py [--strict]

Результат — папка dist/ с готовым HTML (контент отдаётся без выполнения JS).
"""
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from config import (CONTACTS, CONTRAINDICATIONS, DISCLAIMER, DOCTOR, FORM_ACTION, LEGAL,
                    SERVICE, SITE_URL, YANDEX_METRIKA_ID)
from content_articles import MORE_ARTICLES
from content_extra import (ANALYSES, MATERIALS, NOT_MY_FIELD, PREP_DIARY, PREP_FORMAT, PREP_LABS, PREP_MEDS,
                           PREP_TIMING, QUESTIONS_TO_DOCTOR, VIDEOS)
from content import (ARTICLES, CONSULT_INCLUDES, CONSULT_PREPARE, DIRECTIONS, FAQ,
                     NOT_ONLINE_COMMON, PLANNED_ARTICLES, PUBLISHED, REVIEWS, UPDATED)

ROOT = Path(__file__).parent
ARTICLES = ARTICLES + MORE_ARTICLES
DIST = ROOT / "dist"
TODAY = date.today().isoformat()
FORBIDDEN = [r"гарант", r"100\s*%", r"вылеч", r"избави", r"лучший врач", r"самый опытный"]
PAGES = []  # (path, html) для проверок и sitemap


def e(s):
    """Экранирует текст; значения-заглушки «[УТОЧНИТЬ…]» подсвечивает."""
    s = html.escape(str(s))
    return re.sub(r"(\[УТОЧНИТЬ[^\]]*\])", r'<mark class="todo">\1</mark>', s)


def plain(s):
    return re.sub(r"\[УТОЧНИТЬ[^\]]*\]", "", str(s)).strip()


def url(path):
    return SITE_URL.rstrip("/") + path


def price():
    return f"{SERVICE['price']:,}".replace(",", " ") + " ₽"


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def physician_ref():
    return {"@type": "Physician", "@id": url("/about#doctor"), "name": DOCTOR["name"], "url": url("/about")}


def org_ld():
    return {"@context": "https://schema.org", "@type": "Organization", "@id": url("/#org"),
            "name": f"{LEGAL['form']} {DOCTOR['name']}", "taxID": LEGAL["inn"], "url": url("/"),
            "address": {"@type": "PostalAddress", "streetAddress": LEGAL["address"], "addressCountry": "RU"}}


def breadcrumbs(trail):
    items = [("Главная", "/")] + trail
    crumbs = " › ".join(f'<a href="{p}">{e(n)}</a>' if i < len(items) - 1 else e(n) for i, (n, p) in enumerate(items))
    data = {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": url(p)} for i, (n, p) in enumerate(items)]}
    return f'<nav class="crumbs" aria-label="Хлебные крошки">{crumbs}</nav>' + ld(data)


def messengers():
    links = []
    if CONTACTS["telegram"]:
        links.append(f'<a href="https://t.me/{CONTACTS["telegram"]}" data-goal="messenger_telegram" rel="noopener">Telegram</a>')
    if CONTACTS["whatsapp"]:
        links.append(f'<a href="https://wa.me/{CONTACTS["whatsapp"]}" data-goal="messenger_whatsapp" rel="noopener">WhatsApp</a>')
    if CONTACTS["phone"]:
        links.append(f'<a href="tel:{CONTACTS["phone"]}" data-goal="phone_click">{CONTACTS["phone"]}</a>')
    return " · ".join(links) or '<mark class="todo">[УТОЧНИТЬ: Telegram, WhatsApp, телефон]</mark>'


def metrika():
    if not YANDEX_METRIKA_ID:
        return ""
    i = YANDEX_METRIKA_ID
    return f"""<script>(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");
window.YM_ID={i};ym({i},"init",{{clickmap:true,trackLinks:true,accurateTrackBounce:true,webvisor:true}});
document.addEventListener("click",function(ev){{var a=ev.target.closest("[data-goal]");if(a)ym({i},"reachGoal",a.dataset.goal)}});</script>
<noscript><div><img src="https://mc.yandex.ru/watch/{i}" style="position:absolute;left:-9999px" alt=""></div></noscript>"""


NAV = [("/consultation", "Консультация"), ("/about", "О враче"), ("/preparation", "Подготовка"), ("/analizy", "Анализы"),
       ("/calculators", "Калькуляторы"), ("/blog", "Статьи"), ("/reviews", "Отзывы"), ("/contacts", "Контакты")]


SEO_Q = {
    "/": "Эндокринолог и диетолог онлайн", "/about": "Врач, образование и опыт",
    "/consultation": "Онлайн-консультация, цена", "/thyroid": "Щитовидная железа онлайн",
    "/diabetes": "Диабет и преддиабет онлайн", "/insulin-resistance": "Инсулинорезистентность онлайн",
    "/weight": "Лишний вес: консультация онлайн", "/hormones": "Гормональные нарушения онлайн",
    "/nutrition": "Диетолог онлайн: питание", "/faq": "Вопросы о консультации",
    "/reviews": "Отзывы о консультациях", "/documents": "Дипломы и сертификаты врача",
    "/blog": "Статьи об анализах и гормонах", "/contacts": "Контакты и реквизиты врача",
    "/privacy": "Политика обработки ПД сайта", "/offer": "Публичная оферта на консультации",
    "/blog/kogda-onlajn-format-ne-podhodit": "Когда онлайн-формат не подходит",
    "/blog/kakie-analizy-sdat-pered-konsultaciej-endokrinologa": "Анализы перед консультацией",
    "/blog/kak-prohodit-onlajn-konsultaciya-endokrinologa": "Как проходит онлайн-консультация",
}


def page(path, title, description, body, h1, schema=(), trail=None, og_type="website"):
    title = SEO_Q.get(path, title)
    full_title = f"{title} — {DOCTOR['specialty'].split(',')[0].replace('врач-', '')} {plain(DOCTOR['short_name'])}".strip()
    crumbs = breadcrumbs(trail) if trail else ""
    nav = "".join(f'<a href="{p}">{n}</a>' for p, n in NAV)
    dirs = "".join(f'<li><a href="/{d["slug"]}">{e(d["nav"])}</a></li>' for d in DIRECTIONS)
    doc = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(full_title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{url(path)}">{'<meta name="robots" content="noindex">' if path.endswith("thanks") else ""}
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{url(path)}">
<meta property="og:image" content="{url('/img/og-doctor.jpg')}">
<link rel="stylesheet" href="/style.css">
{"".join(ld(s) for s in schema)}
</head>
<body>
<header class="site"><div class="wrap">
<a class="brand" href="/">{e(DOCTOR['short_name'])}<small>{e(DOCTOR['specialty'])}</small></a>
<nav class="main" aria-label="Основное меню">{nav}</nav>
<a class="btn small" href="/consultation#booking" data-goal="cta_header">Записаться</a>
</div></header>
<main><div class="wrap">
{crumbs}
<h1>{e(h1)}</h1>
{body}
</div></main>
<footer class="site"><div class="wrap">
<p><strong>Направления:</strong></p><ul>{dirs}</ul>
<p>{e(LEGAL['form'])} {e(DOCTOR['name'])}, ИНН {e(LEGAL['inn'])}, ОГРНИП {e(LEGAL['ogrnip'])}. {e(LEGAL['address'])}. E-mail: {e(LEGAL['email'])}</p>
<p>{e(DISCLAIMER)} {e(CONTRAINDICATIONS)}</p>
<p><a href="/privacy">Политика обработки персональных данных</a> · <a href="/offer">Публичная оферта</a> · <a href="/contacts">Контакты</a></p>
</div></footer>
<div class="sticky-cta"><a class="btn" href="/consultation#booking" data-goal="cta_sticky">Записаться на консультацию · {price()}</a></div>
{ld(org_ld())}
{metrika()}
</body>
</html>
"""
    PAGES.append((path, doc, full_title, description))
    out = DIST / ("index.html" if path == "/" else path.strip("/") + "/index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")


# ---------- блоки ----------

def ul(items):
    return "<ul>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>"


def disclaimer_block():
    return f'<p class="note">{e(DISCLAIMER)}<br>{e(CONTRAINDICATIONS)}</p>'


def price_block():
    return f"""<div class="card"><p class="price">{price()}</p>
<p>{e(SERVICE['name'])}. Длительность: {e(SERVICE['duration'])}. Платформа: {e(SERVICE['platform'])}.</p>
<a class="btn" href="/consultation#booking" data-goal="cta_price">Записаться на консультацию</a>
{disclaimer_block()}</div>"""


def doctor_block():
    badges = "".join(f'<li><a href="{m["url"]}" rel="noopener">{e(m["name"])}</a></li>' for m in DOCTOR["memberships"])
    return f"""<div class="card doctor"><h2>Врач</h2>
<img src="{DOCTOR['photo']}" width="120" height="168" loading="lazy" alt="{html.escape(plain(DOCTOR['name']))}, {DOCTOR['specialty']}">
<p><a href="/about"><strong>{e(DOCTOR['name'])}</strong></a>, {e(DOCTOR['specialty'])}. Практика с {e(DOCTOR['practice_since'])} года.</p>
<p>Член профессиональных ассоциаций:</p><ul class="badges">{badges}</ul>
<p><a href="/documents">Дипломы, сертификаты и подтверждения членства →</a></p></div>"""


def byline(published=PUBLISHED, updated=UPDATED):
    return (f'<p class="byline">Автор: <a href="/about" rel="author">{e(DOCTOR["name"])}</a>, {e(DOCTOR["specialty"])}<br>'
            f'Опубликовано: <time datetime="{published}">{published}</time> · '
            f'Обновлено: <time datetime="{updated}">{updated}</time></p>')


def faq_block(items, heading="Частые вопросы"):
    body = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in items)
    return f"<h2>{heading}</h2>{body}"


def faq_ld(items):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}


def booking_form():
    action = FORM_ACTION or "/thanks"
    return f"""<form id="booking" class="card" method="post" action="{action}" data-goal="form_submit">
<h2>Запись на консультацию</h2>
<label for="f-name">Имя</label><input id="f-name" name="name" required autocomplete="given-name">
<label for="f-contact">Телефон или ник в Telegram</label><input id="f-contact" name="contact" required autocomplete="tel">
<label for="f-time">Удобное время</label><input id="f-time" name="time" placeholder="например, будни после 18:00">
<label for="f-msg">Кратко о вопросе</label><textarea id="f-msg" name="message" rows="4"></textarea>
<label class="consent"><input type="checkbox" name="consent" required>
<span>Я даю <a href="/privacy#consent">согласие на обработку персональных данных</a> и ознакомлен(а) с <a href="/offer">публичной офертой</a>.</span></label>
<p><button class="btn" type="submit">Отправить заявку</button></p>
<p class="note">Что дальше: в течение рабочего дня с вами свяжутся, подтвердят время и пришлют ссылку на видеосвязь.</p>
</form>"""


# ---------- страницы ----------

def build_home():
    dirs = "".join(f'<div class="card"><h3><a href="/{d["slug"]}">{e(d["nav"])}</a></h3><p>{e(d["how"])}</p></div>' for d in DIRECTIONS)
    badges = "".join(f'<li><a href="{m["url"]}" rel="noopener">{e(m["name"])}</a></li>' for m in DOCTOR["memberships"])
    body = f"""<div class="hero"><div>
<p>{e(DOCTOR['name'])} — {e(DOCTOR['specialty'])}. Разбираю жалобы, анализы и питание онлайн и объясняю, что делать дальше.</p>
<ul class="badges">{badges}</ul>
<p class="price">{price()} <small>за консультацию</small></p>
<p><a class="btn" href="/consultation#booking" data-goal="cta_hero">Записаться на консультацию</a> <a class="btn ghost" href="/about">О враче</a></p>
</div>
<img class="photo" src="{DOCTOR['photo']}" width="300" height="420" alt="{html.escape(plain(DOCTOR['name']) or 'Врач')}, {DOCTOR['specialty']}" fetchpriority="high">
</div>
<h2>С какими вопросами обращаются</h2><div class="grid three">{dirs}</div>
<h2>Что входит в консультацию</h2>{ul(CONSULT_INCLUDES)}
<h2>Когда онлайн-формат не подходит</h2>{ul(NOT_ONLINE_COMMON)}
<p><a href="/blog/kogda-onlajn-format-ne-podhodit">Подробнее о границах онлайн-формата →</a></p>
{not_my_field_block()}
{videos_block()}
{materials_teaser()}
{price_block()}"""
    page("/", "Эндокринолог и диетолог онлайн: консультация",
         "Онлайн-консультация врача-эндокринолога и диетолога: разбор жалоб, анализов и питания. Член ESE, EASD, Endocrine Society. Цена 5 000 ₽. Запишитесь.",
         body, "Эндокринолог и диетолог онлайн — консультация врача")


def build_about():
    d = DOCTOR
    edu = "".join(f"<li>{e(x['year'])} — {e(x['where'])}, {e(x['what'])}</li>" for x in d["education"])
    certs = "".join(f'<li>{e(c["what"])}, {e(c["year"])}, действует до {e(c["valid_until"])} — <a href="{c["doc"]}">документ</a></li>' for c in d["certificates"])
    mem = "".join(f'<li><a href="{m["url"]}" rel="noopener">{e(m["name"])}</a>, членский № {e(m["number"])} — <a href="{m["doc"]}">подтверждение</a></li>' for m in d["memberships"])
    prof = "".join(f'<li><a href="{p["url"]}" rel="noopener me">{e(p["name"])}</a></li>' for p in d["profiles"]) or "<li><mark class=\"todo\">[УТОЧНИТЬ: ПроДокторов, НаПоправку, СберЗдоровье и др.]</mark></li>"
    pubs = ul(d["publications"]) if d["publications"] else "<p>—</p>"
    body = f"""<div class="hero"><div>
<p><strong>{e(d['specialty'])}</strong>. Практика с {e(d['practice_since'])} года.</p>
<blockquote>{e(d['credo'])}</blockquote></div>
<img class="photo" src="{d['photo']}" width="300" height="420" alt="{html.escape(plain(d['name']) or 'Врач')}, {d['specialty']}"></div>
<h2>Образование</h2><ul>{edu}</ul>
<h2>Сертификаты и аккредитация</h2><ul>{certs}</ul>
<h2>Места работы</h2>{ul(d['workplaces'])}
<h2>Членство в профессиональных ассоциациях</h2><ul>{mem}</ul>
<h2>Повышение квалификации</h2>{ul(d['trainings'])}
<h2>Публикации и выступления</h2>{pubs}
<h2>Профили на внешних площадках</h2><ul>{prof}</ul>
{not_my_field_block()}
{price_block()}"""
    schema = {"@context": "https://schema.org", "@type": "Physician", "@id": url("/about#doctor"),
              "name": d["name"], "url": url("/about"), "image": url(d["photo"]),
              "medicalSpecialty": ["Endocrine", "DietNutrition"], "description": d["specialty"],
              "alumniOf": [{"@type": "EducationalOrganization", "name": x["where"]} for x in d["education"]],
              "memberOf": [{"@type": "Organization", "name": m["name"], "url": m["url"]} for m in d["memberships"]],
              "sameAs": [p["url"] for p in d["profiles"]], "priceRange": price()}
    page("/about", f"О враче: {plain(d['name']) or 'эндокринолог, диетолог'}, образование и опыт",
         "Образование, сертификаты, стаж и членство в ESE, EASD и Endocrine Society врача-эндокринолога и диетолога. Документы и ссылки для проверки квалификации.",
         body, f"{d['name']} — врач-эндокринолог, диетолог", [schema], [("О враче", "/about")], "profile")


def build_consultation():
    body = f"""{price_block()}
<h2>Что входит</h2>{ul(CONSULT_INCLUDES)}
<h2>Как проходит</h2>
<ol><li>Вы оставляете заявку или пишете в мессенджер.</li><li>Вам подтверждают время и присылают ссылку ({e(SERVICE['platform'])}).</li>
<li>Консультация по видеосвязи, {e(SERVICE['duration'])}.</li><li>После — письменные рекомендации [УТОЧНИТЬ: формат].</li></ol>
<h2>Что подготовить</h2>{ul(CONSULT_PREPARE)}
<p><a href="/preparation">Подробно: как подготовиться к консультации →</a> · <a href="/pamyatka-k-konsultacii.txt" download data-goal="memo_download">скачать памятку</a></p>
<h2>Что не входит и не решается онлайн</h2>{ul(NOT_ONLINE_COMMON)}
<h2>Перенос и отмена</h2><p>{e(SERVICE['cancel_policy'])}</p>
<h2>Повторная консультация</h2><p>{e(SERVICE['repeat'])}</p>
{not_my_field_block()}
{videos_block()}
{booking_form()}
<p>Или напишите: {messengers()}</p>
{doctor_block()}"""
    schema = {"@context": "https://schema.org", "@type": "Service", "name": SERVICE["name"], "serviceType": "Онлайн-консультация",
              "provider": physician_ref(), "areaServed": "RU", "url": url("/consultation"),
              "offers": {"@type": "Offer", "price": SERVICE["price"], "priceCurrency": "RUB", "url": url("/consultation"),
                         "availability": "https://schema.org/InStock"}}
    page("/consultation", "Онлайн-консультация эндокринолога: цена и порядок",
         "Что входит в онлайн-консультацию эндокринолога и диетолога, как подготовиться и как проходит разговор. Цена 5 000 ₽. Оставьте заявку на удобное время.",
         body, "Онлайн-консультация эндокринолога и диетолога", [schema], [("Консультация", "/consultation")])


def build_direction(d):
    tools_map = {"insulin-resistance": ("/calculators/homa-ir", "Калькулятор HOMA-IR"), "weight": ("/calculators/bmi", "Калькулятор ИМТ"),
                 "nutrition": ("/calculators/bmr", "Калькулятор базового обмена"), "thyroid": ("/analizy/ttg", "Разбор анализа на ТТГ"),
                 "diabetes": ("/analizy/glikirovannyj-gemoglobin", "Разбор анализа HbA1c")}
    t = tools_map.get(d["slug"])
    tools = f'<div class="card"><p>Полезно перед консультацией: <a href="{t[0]}">{t[1]}</a> · <a href="/preparation">как подготовиться</a></p></div>' if t else ""
    body = f"""{byline()}
<h2>Если вас беспокоит</h2>{ul(d['symptoms'])}
<p class="note">Перечисленное — не признаки конкретного заболевания и не повод ставить себе диагноз. Это ситуации, с которыми обращаются к врачу.</p>
<h2>Какие обследования могут понадобиться</h2>{ul(d['exams'])}
<p>Это ориентир, а не назначение: нужный перечень врач обсудит с вами на консультации.</p>
<h2>Как проходит консультация</h2><p>{e(d['how'])}</p>{tools}
<h2>Что не решается онлайн</h2>{ul(d['not_online'] + NOT_ONLINE_COMMON)}
{price_block()}
{doctor_block()}
{faq_block(d['faq'])}"""
    path = "/" + d["slug"]
    schema = [{"@context": "https://schema.org", "@type": "MedicalWebPage", "url": url(path), "name": d["h1"],
               "about": {"@type": "MedicalCondition", "name": d["about"]}, "specialty": "Endocrine",
               "lastReviewed": UPDATED, "datePublished": PUBLISHED, "dateModified": UPDATED,
               "reviewedBy": physician_ref(), "author": physician_ref()}, faq_ld(d["faq"])]
    page(path, d["title"], d["description"], body, d["h1"], schema, [(d["nav"], path)])


def build_faq():
    page("/faq", "Частые вопросы об онлайн-консультации эндокринолога",
         "Ответы на частые вопросы: цена, длительность, подготовка, перенос, чем онлайн-консультация эндокринолога отличается от очного приёма. Читайте и записывайтесь.",
         faq_block(FAQ, "Вопросы и ответы") + price_block(), "Частые вопросы об онлайн-консультации", [faq_ld(FAQ)], [("Вопросы", "/faq")])


def build_reviews():
    schema = []
    if REVIEWS:
        items = "".join(f'<div class="card"><p><strong>{e(r["name"])}</strong>, {e(r["city"])} · вопрос: {e(r["topic"])}</p><p>{e(r["text"])}</p></div>' for r in REVIEWS)
        schema = [{"@context": "https://schema.org", "@type": "Physician", "@id": url("/about#doctor"), "name": DOCTOR["name"],
                   "aggregateRating": {"@type": "AggregateRating", "ratingValue": round(sum(r["rating"] for r in REVIEWS) / len(REVIEWS), 1), "reviewCount": len(REVIEWS)},
                   "review": [{"@type": "Review", "author": {"@type": "Person", "name": r["name"]}, "datePublished": r["date"],
                               "reviewBody": r["text"], "reviewRating": {"@type": "Rating", "ratingValue": r["rating"], "bestRating": 5}} for r in REVIEWS]}]
    else:
        items = '<p class="card"><mark class="todo">[УТОЧНИТЬ: отзывы пациентов с согласием на публикацию]</mark></p>'
    body = f"""<p>Отзывы публикуются с согласия авторов. По требованиям к рекламе медицинских услуг мы не публикуем упоминания диагнозов и результатов лечения.</p>
{items}
<p>Были на консультации? <a href="/contacts">Оставьте отзыв</a> — после консультации мы также присылаем ссылку на форму отзыва.</p>
{price_block()}"""
    page("/reviews", "Отзывы о консультациях эндокринолога и диетолога",
         "Отзывы пациентов об онлайн-консультациях врача-эндокринолога и диетолога: с какими вопросами обращались и как прошла консультация. Читайте и записывайтесь.",
         body, "Отзывы об онлайн-консультациях", schema, [("Отзывы", "/reviews")])


def build_documents():
    blocks = [("accreditation-endo", "Аккредитация: эндокринология"), ("accreditation-diet", "Аккредитация / сертификат: диетология"),
              ("diploma", "Диплом о высшем образовании"), ("residency", "Диплом / удостоверение об ординатуре")]
    blocks += [(m["doc"].split("#")[1], f'Членство: {m["name"]}') for m in DOCTOR["memberships"]]
    cards = "".join(f'<div class="card" id="{i}"><h2>{e(n)}</h2><p><mark class="todo">[УТОЧНИТЬ: скан в WebP, номер, дата, ссылка на реестр]</mark></p></div>' for i, n in blocks)
    body = f"""<p>Здесь собраны документы, подтверждающие образование и квалификацию. Персональные данные на сканах (паспортные данные, адреса) скрыты.</p>
<div class="grid">{cards}</div>
<div class="card" id="license"><h2>Лицензия на медицинскую деятельность</h2><p>Консультации проводятся как информационная услуга. <mark class="todo">[УТОЧНИТЬ: есть ли лицензия; если есть — номер и ссылка на реестр Росздравнадзора]</mark></p></div>"""
    page("/documents", "Дипломы, сертификаты и членство в ассоциациях врача",
         "Дипломы, сертификаты, аккредитация и подтверждение членства в ESE, EASD и Endocrine Society врача-эндокринолога и диетолога. Проверьте квалификацию врача.",
         body, "Документы и подтверждение квалификации", [], [("Документы", "/documents")])


def build_blog():
    lst = "".join(f'<div class="card"><h2><a href="/blog/{a["slug"]}">{e(a["title"])}</a></h2><p>{e(a["description"])}</p></div>' for a in ARTICLES)
    page("/blog", "Статьи эндокринолога и диетолога: анализы, гормоны, питание",
         "Понятные разборы от врача-эндокринолога и диетолога: какие анализы сдать, как проходит онлайн-консультация, когда нужен очный приём. Читайте статьи.",
         lst, "Статьи врача-эндокринолога и диетолога", [], [("Статьи", "/blog")])
    for a in ARTICLES:
        path = f"/blog/{a['slug']}"
        src = ("<h2>Источники</h2><ol>" + "".join(f'<li><a href="{u}" rel="noopener">{e(t)}</a></li>' for t, u in a["sources"]) + "</ol>") if a["sources"] else ""
        body = f"""{byline()}<article>{a['body']}</article>{src}
{disclaimer_block()}
<p><a class="btn" href="/consultation#booking" data-goal="cta_article">Записаться на консультацию · {price()}</a></p>"""
        schema = {"@context": "https://schema.org", "@type": "Article", "headline": a["title"], "description": a["description"],
                  "datePublished": PUBLISHED, "dateModified": UPDATED, "author": physician_ref(), "reviewedBy": physician_ref(),
                  "mainEntityOfPage": url(path), "image": url("/img/og-doctor.jpg"), "inLanguage": "ru"}
        page(path, a.get("seo", a["title"]), a["description"], body, a["title"], [schema], [("Статьи", "/blog"), (a["title"], path)], "article")


def build_contacts():
    body = f"""<div class="card"><p>Мессенджеры и телефон: {messengers()}</p><p>E-mail: {e(LEGAL['email'])}</p>
<p>Консультации проводятся онлайн. Очный приём: [УТОЧНИТЬ: есть ли, где, по какой цене].</p></div>
<h2>Реквизиты</h2><p>{e(LEGAL['form'])} {e(DOCTOR['name'])}<br>ИНН {e(LEGAL['inn'])}<br>ОГРНИП {e(LEGAL['ogrnip'])}<br>{e(LEGAL['address'])}</p>
{booking_form()}"""
    page("/contacts", "Контакты и реквизиты эндокринолога-диетолога",
         "Контакты врача-эндокринолога и диетолога: Telegram, WhatsApp, e-mail, реквизиты. Напишите в мессенджер или оставьте заявку на онлайн-консультацию.",
         body, "Контакты и реквизиты", [], [("Контакты", "/contacts")])


def build_legal():
    privacy = f"""<p class="note">Шаблон. Текст должен быть проверен юристом до публикации (разд. 5 ТЗ).</p>
<h2>1. Оператор</h2><p>{e(LEGAL['form'])} {e(DOCTOR['name'])}, ИНН {e(LEGAL['inn'])}, {e(LEGAL['address'])}, {e(LEGAL['email'])}.</p>
<h2>2. Какие данные собираются</h2><ul><li>имя;</li><li>телефон или имя пользователя в мессенджере;</li><li>удобное время связи;</li>
<li>сведения, которые вы сами указываете в поле «Кратко о вопросе», — могут относиться к сведениям о состоянии здоровья (специальная категория ПД, ст. 10 152-ФЗ);</li>
<li>технические данные посещения через Яндекс.Метрику (cookie, IP-адрес, сведения о браузере).</li></ul>
<h2>3. Цели</h2><p>Запись на консультацию, связь с вами, проведение консультации, анализ посещаемости сайта.</p>
<h2>4. Где хранятся данные</h2><p>На серверах в Российской Федерации ({e(LEGAL['hosting'])}), в соответствии с ч. 5 ст. 18 152-ФЗ.</p>
<h2>5. Сроки и отзыв согласия</h2><p>Данные хранятся до достижения целей обработки или до отзыва согласия. Отозвать согласие можно письмом на {e(LEGAL['email'])}.</p>
<h2 id="consent">6. Согласие на обработку персональных данных</h2><p>Отправляя форму, вы даёте согласие оператору на обработку указанных выше данных, включая сведения о состоянии здоровья, в целях из раздела 3. [УТОЧНИТЬ у юриста: полный текст согласия]</p>"""
    page("/privacy", "Политика обработки персональных данных сайта врача",
         "Политика обработки персональных данных по 152-ФЗ: какие данные собирает сайт врача-эндокринолога, зачем, где хранятся и как отозвать согласие.",
         privacy, "Политика обработки персональных данных", [], [("Политика ПД", "/privacy")])
    offer = f"""<p class="note">Шаблон. Текст должен быть проверен юристом до публикации.</p>
<h2>1. Стороны и предмет</h2><p>{e(LEGAL['form'])} {e(DOCTOR['name'])} (Исполнитель) оказывает информационно-консультационные услуги в онлайн-формате: {e(SERVICE['name'].lower())}.</p>
<h2>2. Характер услуги</h2><p>{e(DISCLAIMER)} Исполнитель не ставит диагнозов, не назначает лекарственные препараты и не выдаёт медицинских документов в рамках онлайн-консультации.</p>
<h2>3. Стоимость</h2><p>{price()} за одну консультацию длительностью {e(SERVICE['duration'])}.</p>
<h2>4. Перенос, отмена, возврат</h2><p>{e(SERVICE['cancel_policy'])}</p>
<h2>5. Акцепт</h2><p>Акцептом оферты является оплата услуги. [УТОЧНИТЬ у юриста]</p>
<h2>6. Реквизиты</h2><p>ИНН {e(LEGAL['inn'])}, ОГРНИП {e(LEGAL['ogrnip'])}, {e(LEGAL['address'])}.</p>"""
    page("/offer", "Публичная оферта на информационно-консультационные услуги",
         "Публичная оферта на оказание информационно-консультационных услуг врачом-эндокринологом и диетологом онлайн: предмет, стоимость, порядок отмены.",
         offer, "Публичная оферта", [], [("Оферта", "/offer")])


def build_thanks():
    page("/thanks", "Заявка отправлена",
         "Заявка на онлайн-консультацию эндокринолога отправлена. В течение рабочего дня с вами свяжутся, чтобы подтвердить время и прислать ссылку на видеосвязь.",
         f"<p>Спасибо! В течение рабочего дня с вами свяжутся и подтвердят время. Если вопрос срочный — напишите: {messengers()}</p>",
         "Спасибо, заявка отправлена", [], [("Заявка отправлена", "/thanks")])


def build_service_files(indexable):
    sm = "".join(f"<url><loc>{url(p)}</loc><lastmod>{UPDATED}</lastmod></url>" for p in indexable)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n', encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nDisallow: /thanks\nAllow: /\n\nSitemap: {url('/sitemap.xml')}\n", encoding="utf-8")


# ---------- дополнительные разделы ----------

def not_my_field_block():
    rows = "".join(f"<li>{e(a)} → <strong>{e(b)}</strong></li>" for a, b in NOT_MY_FIELD)
    return f"""<h2 id="not-my-field">Чем я не занимаюсь</h2>
<p>Есть вопросы, которые лучше решит другой специалист. В таких случаях я честно скажу об этом и подскажу, к кому обратиться.</p><ul>{rows}</ul>"""


def videos_block():
    cards = []
    schema = []
    for v in VIDEOS:
        if v["src"]:
            if v["src"].endswith(".mp4"):
                media = f'<video controls preload="none" poster="{v["poster"]}" width="640" height="360" style="width:100%;height:auto"><source src="{v["src"]}" type="video/mp4"></video>'
            else:
                media = f'<p><a href="{v["src"]}" rel="noopener">Смотреть видео →</a></p>'
            schema.append({"@context": "https://schema.org", "@type": "VideoObject", "name": v["title"], "contentUrl": url(v["src"]) if v["src"].startswith("/") else v["src"],
                           "thumbnailUrl": url(v["poster"]) if v["poster"] else url("/img/og-doctor.jpg"), "uploadDate": UPDATED, "duration": v["duration"] or None})
        else:
            media = '<p><mark class="todo">[УТОЧНИТЬ: видео 1–2 минуты]</mark></p>'
        cards.append(f'<div class="card"><h3>{e(v["title"])}</h3>{media}</div>')
    return f'<h2>Видео: познакомьтесь с врачом</h2><div class="grid three">{"".join(cards)}</div>' + "".join(ld(s) for s in schema)


def lead_form():
    action = FORM_ACTION or "/materials/thanks"
    return f"""<form id="materials-form" class="card" method="post" action="{action}" data-goal="lead_materials">
<h2>Получить материалы</h2>
<p>Оставьте контакт — пришлём ссылки на все материалы. Без рассылок и спама: только материалы и, если захотите, напоминание о записи.</p>
<label for="m-name">Имя</label><input id="m-name" name="name" required autocomplete="given-name">
<label for="m-contact">Telegram, WhatsApp или e-mail</label><input id="m-contact" name="contact" required>
<label class="consent"><input type="checkbox" name="consent" required>
<span>Я даю <a href="/privacy#consent">согласие на обработку персональных данных</a>.</span></label>
<input type="hidden" name="source" value="materials">
<p><button class="btn" type="submit">Получить материалы</button></p>
</form>"""


def materials_teaser():
    return """<div class="card"><h2>Бесплатные материалы</h2><p>Чек-лист анализов, шаблон дневника питания и список вопросов врачу.</p>
<a class="btn ghost" href="/materials">Получить материалы</a></div>"""


def build_preparation():
    labs = "".join(f"<tr><td>{e(n)}</td><td>{e(w)}</td></tr>" for n, w in PREP_LABS)
    body = f"""{byline()}
<p>Хорошая подготовка делает консультацию в разы полезнее: врач тратит время на разбор, а не на сбор информации.</p>
<h2>Какие анализы иметь на руках</h2>
<p>Это ориентир, а не назначение. Если анализов нет — консультация всё равно возможна: врач подскажет, с чего начать.</p>
<div class="table"><table><thead><tr><th>Анализ</th><th>Когда полезен</th></tr></thead><tbody>{labs}</tbody></table></div>
<p>Подробнее о каждом показателе — в разделе <a href="/analizy">«Разбор анализов»</a>.</p>
<h2>Когда и как сдавать</h2>{ul(PREP_TIMING)}
<h2>В каком виде присылать</h2>{ul(PREP_FORMAT)}
<h2>Список препаратов</h2><p>{e(PREP_MEDS)}</p>
<h2>Дневник питания</h2><p>{e(PREP_DIARY)}</p>
<h2>Вопросы</h2><p>Запишите вопросы заранее — во время разговора их легко забыть. Готовый список — в <a href="/materials">материалах</a>.</p>
{materials_teaser()}
{price_block()}"""
    faq = [("Какие анализы нужны эндокринологу?", "Чаще всего полезны ТТГ, свободный Т4, глюкоза натощак и гликированный гемоглобин. Точный перечень зависит от жалоб."),
           ("За сколько дней сдавать анализы?", "Не раньше чем за 1–2 месяца до консультации, чтобы результаты были актуальны."),
           ("Можно ли прислать фото вместо PDF?", "Да, если на фото виден весь бланк с датой и референсными значениями.")]
    page("/preparation", "Подготовка к консультации",
         "Какие анализы нужны эндокринологу, за сколько дней сдавать, в каком виде присылать, как составить список препаратов и дневник питания. Подготовьтесь.",
         body + faq_block(faq), "Как подготовиться к консультации эндокринолога", [faq_ld(faq)], [("Подготовка", "/preparation")])


def build_materials():
    items = "".join(f'<div class="card"><h3>{e(m["title"])}</h3><p>{e(m["about"])}</p></div>' for m in MATERIALS)
    page("/materials", "Чек-листы и памятки от эндокринолога",
         "Бесплатно: чек-лист анализов перед визитом к эндокринологу, шаблон дневника питания и список вопросов врачу. Оставьте контакт и получите материалы.",
         f'<div class="grid three">{items}</div>{lead_form()}{disclaimer_block()}', "Бесплатные материалы для подготовки к консультации", [], [("Материалы", "/materials")])
    links = "".join(f'<li><a href="/files/{m["file"]}" download data-goal="memo_download">{e(m["title"])}</a></li>' for m in MATERIALS)
    page("/materials/thanks", "Материалы", "Ссылки на материалы.",
         f"<p>Спасибо! Скачайте материалы:</p><ul>{links}</ul>{price_block()}", "Ваши материалы", [], [("Материалы", "/materials"), ("Скачать", "/materials/thanks")])
    files = DIST / "files"
    files.mkdir(exist_ok=True)
    head = f"{DOCTOR['name']}, {DOCTOR['specialty']}\n{url('/')}\n\n"
    tail = f"\n{DISCLAIMER}\n{CONTRAINDICATIONS}\n"
    (files / "chek-list-analizov.txt").write_text(
        "Чек-лист анализов перед первым визитом к эндокринологу\n" + head + "".join(f"[ ] {n} — {w}\n" for n, w in PREP_LABS)
        + "\nКак сдавать:\n" + "".join(f"- {t}\n" for t in PREP_TIMING) + "\nЭто ориентир, а не назначение. Перечень зависит от жалоб.\n" + tail, encoding="utf-8")
    rows = "День;Время;Что съели/выпили;Количество;Самочувствие (голод, сонливость, тяга к сладкому)\n" + "".join(f"{d};;;;\n" for d in range(1, 8) for _ in range(5))
    (files / "dnevnik-pitaniya-shablon.csv").write_text("﻿" + rows, encoding="utf-8")
    (files / "voprosy-vrachu.txt").write_text("Список вопросов врачу\n" + head + "".join(f"[ ] {q}\n" for q in QUESTIONS_TO_DOCTOR) + "\nМои вопросы:\n1.\n2.\n3.\n" + tail, encoding="utf-8")


CALCS = [
    {"slug": "bmi", "name": "Калькулятор индекса массы тела (ИМТ)", "seo": "Калькулятор ИМТ онлайн", "nav": "Индекс массы тела",
     "description": "Рассчитайте индекс массы тела (ИМТ) по росту и весу и узнайте, как его трактует ВОЗ и почему ИМТ — лишь один из показателей. Калькулятор врача.",
     "fields": [("weight", "Вес, кг"), ("height", "Рост, см")],
     "about": "<p>ИМТ = вес (кг) / рост² (м). Классификация ВОЗ: менее 18,5 — ниже нормы, 18,5–24,9 — норма, 25–29,9 — избыточная масса тела, 30 и более — ожирение.</p><p>ИМТ не учитывает соотношение мышц и жира, распределение жира и возраст. У спортсменов он может быть завышен, у пожилых — занижен. Это ориентир, а не диагноз.</p>",
     "related": "/weight"},
    {"slug": "bmr", "name": "Калькулятор базового обмена веществ", "seo": "Калькулятор базового обмена", "nav": "Базовый обмен",
     "description": "Рассчитайте базовый обмен веществ по формуле Миффлина — Сан Жеора: сколько калорий организм тратит в покое. Онлайн-калькулятор от врача-диетолога.",
     "fields": [("weight", "Вес, кг"), ("height", "Рост, см"), ("age", "Возраст, лет")], "sex": True,
     "about": "<p>Базовый обмен — энергия, которую организм тратит в покое на дыхание, кровообращение, работу органов. Формула Миффлина — Сан Жеора: 10 × вес + 6,25 × рост − 5 × возраст + 5 (мужчины) или −161 (женщины).</p><p>Это оценка: реальный расход зависит от состава тела, активности, гормонального фона. Не используйте результат для жёстких диет.</p>",
     "related": "/nutrition"},
    {"slug": "homa-ir", "name": "Калькулятор индекса HOMA-IR", "seo": "Калькулятор HOMA-IR онлайн", "nav": "HOMA-IR",
     "description": "Рассчитайте индекс инсулинорезистентности HOMA-IR по глюкозе и инсулину натощак. Объясняем, как понимать результат и почему нет единой нормы.",
     "fields": [("glucose", "Глюкоза натощак, ммоль/л"), ("insulin", "Инсулин натощак, мкЕд/мл")],
     "about": "<p>HOMA-IR = глюкоза (ммоль/л) × инсулин (мкЕд/мл) / 22,5. Оба анализа сдаются одновременно, строго натощак.</p><p>Единого порога для HOMA-IR нет: в исследованиях используют разные значения. Индекс — дополнительный ориентир, его оценивают вместе с жалобами, весом, другими анализами. <a href=\"/analizy/homa-ir\">Подробнее об индексе</a>.</p>",
     "related": "/insulin-resistance"},
]
CALC_KEY = {"bmi": "bmi", "bmr": "bmr", "homa-ir": "homa"}


def build_calculators():
    cards = "".join(f'<div class="card"><h2><a href="/calculators/{c["slug"]}">{e(c["nav"])}</a></h2><p>{e(c["description"])}</p></div>' for c in CALCS)
    page("/calculators", "Калькуляторы ИМТ и HOMA-IR",
         "Онлайн-калькуляторы от врача-эндокринолога: индекс массы тела, базовый обмен веществ и индекс инсулинорезистентности HOMA-IR. С пояснениями.",
         f'<div class="grid three">{cards}</div>{disclaimer_block()}', "Медицинские калькуляторы", [], [("Калькуляторы", "/calculators")])
    for c in CALCS:
        fields = "".join(f'<label for="c-{n}">{l}</label><input id="c-{n}" name="{n}" inputmode="decimal" required>' for n, l in c["fields"])
        if c.get("sex"):
            fields += '<label for="c-sex">Пол</label><select id="c-sex" name="sex"><option value="f">Женский</option><option value="m">Мужской</option></select>'
        rel = next(d for d in DIRECTIONS if "/" + d["slug"] == c["related"])
        body = f"""{byline()}
<form class="card calc" data-calc="{CALC_KEY[c['slug']]}">{fields}
<p><button class="btn" type="submit">Рассчитать</button></p><output aria-live="polite"></output></form>
<h2>Как считается и как понимать результат</h2>{c['about']}
<p class="note">Калькулятор не ставит диагноз. Результат — повод для разговора с врачом, а не для самостоятельных выводов.</p>
<p>Связанное направление: <a href="{c['related']}">{e(rel['nav'])}</a>.</p>
{price_block()}<script src="/calc.js" defer></script>"""
        schema = {"@context": "https://schema.org", "@type": "MedicalWebPage", "url": url(f"/calculators/{c['slug']}"), "name": c["name"],
                  "lastReviewed": UPDATED, "reviewedBy": physician_ref(), "author": physician_ref()}
        page(f"/calculators/{c['slug']}", c["seo"], c["description"], body, c["name"], [schema],
             [("Калькуляторы", "/calculators"), (c["nav"], f"/calculators/{c['slug']}")])


def build_analyses():
    by = {a["slug"]: a for a in ANALYSES}
    cards = "".join(f'<div class="card"><h2><a href="/analizy/{a["slug"]}">{e(a["name"])}</a></h2><p>{e(a["what"])}</p></div>' for a in ANALYSES)
    page("/analizy", "Разбор анализов: ТТГ, глюкоза",
         "Что показывают ТТГ, свободный Т4, антитела к ТПО, глюкоза, HbA1c, инсулин, HOMA-IR и витамин D. Понятные разборы анализов от врача-эндокринолога.",
         f'<p>Что показывает каждый анализ, когда его сдают и что делать с результатом. Без диагнозов и назначений: результаты всегда оценивает врач.</p><div class="grid">{cards}</div>',
         "Разбор анализов: что показывают и что делать дальше", [], [("Анализы", "/analizy")])
    for a in ANALYSES:
        path = f"/analizy/{a['slug']}"
        rel = "".join(f'<li><a href="/analizy/{s}">{e(by[s]["name"])}</a></li>' for s in a["related"])
        calc = f'<p><a class="btn ghost" href="{a["calc"]}">Рассчитать в калькуляторе</a></p>' if a.get("calc") else ""
        body = f"""{byline()}
<h2>Что показывает</h2><p>{e(a['what'])}</p>{calc}
<h2>Когда сдают</h2>{ul(a['when'])}
<h2>Почему «норма» — не всегда ответ</h2><p>{e(a['norm'])}</p>
<h2>Что делать дальше</h2><p>{e(a['next'])}</p>
<p>Как подготовиться к сдаче — на странице <a href="/preparation">«Подготовка к консультации»</a>.</p>
<h2>Связанные анализы</h2><ul>{rel}</ul>
{disclaimer_block()}
{price_block()}"""
        schema = {"@context": "https://schema.org", "@type": "MedicalWebPage", "url": url(path), "name": a["name"],
                  "about": {"@type": "MedicalTest", "name": a["name"]}, "specialty": "Endocrine",
                  "lastReviewed": UPDATED, "datePublished": PUBLISHED, "dateModified": UPDATED,
                  "reviewedBy": physician_ref(), "author": physician_ref()}
        page(path, a["seo"], a["description"], body, f"{a['name']}: что показывает анализ", [schema],
             [("Анализы", "/analizy"), (a["name"], path)])



def check(strict):
    problems, warnings = [], []
    titles, descs = {}, {}
    for path, doc, title, desc in PAGES:
        if doc.count("<h1") != 1:
            problems.append(f"{path}: H1 должен быть ровно один")
        if "maximum-scale" in doc or "user-scalable" in doc:
            problems.append(f"{path}: заблокирован зум")
        if title in titles:
            problems.append(f"{path}: title совпадает с {titles[title]}")
        if desc in descs:
            problems.append(f"{path}: description совпадает с {descs[desc]}")
        titles[title], descs[desc] = path, path
        if not 140 <= len(desc) <= 160 and not path.endswith("thanks"):
            warnings.append(f"{path}: description {len(desc)} знаков (нужно 140–160)")
        if not 50 <= len(title) <= 65 and not path.endswith("thanks"):
            warnings.append(f"{path}: title {len(title)} знаков (нужно 50–65)")
        text = re.sub(r"<[^>]+>", " ", doc).lower()
        for pat in FORBIDDEN:
            if re.search(pat, text):
                problems.append(f"{path}: запрещённая формулировка /{pat}/")
        for img in re.findall(r"<img[^>]*>", doc):
            if "alt=" not in img:
                problems.append(f"{path}: <img> без alt")
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
            json.loads(block)
        if "УТОЧНИТЬ" in doc:
            warnings.append(f"{path}: есть незаполненные данные [УТОЧНИТЬ]")
    for w in warnings:
        print("warn:", w)
    for p in problems:
        print("ERROR:", p)
    if problems or (strict and any("УТОЧНИТЬ" in w for w in warnings)):
        sys.exit(1)
    print(f"OK: {len(PAGES)} страниц в {DIST}")


def main():
    strict = "--strict" in sys.argv
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ROOT / "static", DIST, dirs_exist_ok=True)
    build_home(); build_about(); build_consultation()
    for d in DIRECTIONS:
        build_direction(d)
    build_faq(); build_reviews(); build_documents(); build_blog(); build_contacts(); build_legal(); build_thanks()
    build_preparation(); build_materials(); build_calculators(); build_analyses()
    memo = "Как подготовиться к онлайн-консультации\n" + DOCTOR["name"] + ", " + DOCTOR["specialty"] + "\n\nПодготовьте:\n" + "".join(f"- {x}\n" for x in CONSULT_PREPARE) + "\n" + DISCLAIMER + "\n" + CONTRAINDICATIONS + "\n" + url("/consultation") + "\n"
    (DIST / "pamyatka-k-konsultacii.txt").write_text(memo, encoding="utf-8")
    build_service_files([p for p, *_ in PAGES if not p.endswith("thanks")])
    check(strict)


if __name__ == "__main__":
    main()
