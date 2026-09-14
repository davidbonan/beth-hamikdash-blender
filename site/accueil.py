#!/usr/bin/env python3
"""Écrit index.html, en/index.html et he/index.html depuis un gabarit et les textes ci-dessous.

    python3 site/accueil.py

L'accueil est la visite elle-même en mode cinéma : la scène marche seule le long des
degrés de sainteté (Kelim 1:6-9) et la page nomme le degré où elle en est. Les haltes
et leurs temps viennent de visite/cinema.json ; à chaque halte, l'image du film prise
de ce même point (site/images/<degré>_*.webp) se fond sur la scène, puis la marche
reprend. L'affiche est l'image du départ.
"""
import json
from pathlib import Path

SITE = Path(__file__).resolve().parent
DOMAINE = "https://bethhamikdach.com"
PARCOURS = json.loads((SITE.parent / "visite" / "cinema.json").read_text(encoding="utf-8"))

TEXTES = {
    "fr": {
        "chemin": "",
        "sens": "ltr",
        "nom_langue": "Français",
        "titre": "Beit HaMikdach, le Temple de Jérusalem en trois dimensions",
        "description": "Le Temple de Jérusalem reconstruit aux cotes de la Mishna. Une visite libre, du Har HaBayit au Kodesh HaKodashim, où chaque pierre cite sa source.",
        "nav_langue": "Langue",
        "hebreu": "בית המקדש",
        "latin": "Beit HaMikdach",
        "accroche": "Le Temple de Jérusalem, reconstruit en trois dimensions aux cotes de la Mishna. On y entre à pied, on y marche librement, et chaque pierre dit d'où elle vient.",
        "entrer": "Entrer dans la visite",
        "entrer_note": "Gratuit, sans installation. Dix minutes ou une heure.",
        "degres_titre": "Les degrés de sainteté",
        "mishna": "Mishna Kelim",
        "degres": {
            "har_habayit": ("Har HaBayit", "הר הבית", "1:8", "Plus saint que Jérusalem : les zavim, les zavot, les niddot et les accouchées n'y entrent pas."),
            "heil": ("Heil", "חיל", "1:8", "Plus saint que le Har HaBayit : les non-Juifs et ceux qu'un mort a rendus impurs n'y entrent pas."),
            "ezrat_nashim": ("Ezrat Nashim", "עזרת נשים", "1:8", "Plus sainte que le Heil : celui qui s'est immergé le jour même n'y entre pas avant le coucher du soleil."),
            "azara": ("Ezrat Israël", "עזרת ישראל", "1:8", "Plus sainte que l'Ezrat Nashim : celui à qui il manque encore une offrande d'expiation n'y entre pas."),
            "mizbeach": ("Ezrat Cohanim", "עזרת כהנים", "1:8", "Plus sainte que l'Ezrat Israël : les Israélites n'y entrent que pour ce qui les requiert, la semikha, la she'hita et la tenoufa."),
            "oulam": ("Entre l'Oulam et l'autel", "בין האולם ולמזבח", "1:9", "Plus saint que l'Ezrat Cohanim : les cohanim atteints d'un défaut ou aux cheveux défaits n'y entrent pas."),
            "heikhal": ("Heikhal", "היכל", "1:9", "Plus saint encore : nul n'y entre sans s'être lavé les mains et les pieds."),
            "kodesh_hakodashim": ("Kodesh HaKodashim", "קודש הקודשים", "1:9", "Plus saint que tout : nul n'y entre, sinon le Cohen Gadol, le jour de Kippour, à l'heure du service."),
        },
    },
    "en": {
        "chemin": "en/",
        "sens": "ltr",
        "nom_langue": "English",
        "titre": "Beit HaMikdach, the Temple of Jerusalem in three dimensions",
        "description": "The Temple of Jerusalem rebuilt to the measurements of the Mishnah. A free walk from the Har HaBayit to the Kodesh HaKodashim, where every stone cites its source.",
        "nav_langue": "Language",
        "hebreu": "בית המקדש",
        "latin": "Beit HaMikdach",
        "accroche": "The Temple of Jerusalem, rebuilt in three dimensions to the measurements of the Mishnah. You enter on foot, walk where you like, and every stone tells you where it comes from.",
        "entrer": "Enter the tour",
        "entrer_note": "Free, nothing to install. Ten minutes or an hour.",
        "degres_titre": "The degrees of holiness",
        "mishna": "Mishnah Kelim",
        "degres": {
            "har_habayit": ("Har HaBayit", "הר הבית", "1:8", "Holier than Jerusalem: zavim, zavot, menstruants and women after childbirth may not enter."),
            "heil": ("Chel", "חיל", "1:8", "Holier than the Har HaBayit: non-Jews and those made impure by a corpse may not enter."),
            "ezrat_nashim": ("Ezrat Nashim", "עזרת נשים", "1:8", "Holier than the Chel: one who immersed that same day may not enter before sunset."),
            "azara": ("Ezrat Israel", "עזרת ישראל", "1:8", "Holier than the Ezrat Nashim: one who still owes an offering of atonement may not enter."),
            "mizbeach": ("Ezrat Kohanim", "עזרת כהנים", "1:8", "Holier than the Ezrat Israel: Israelites enter only for what requires them, the semikhah, the shechitah and the tenufah."),
            "oulam": ("Between the Ulam and the altar", "בין האולם ולמזבח", "1:9", "Holier than the Ezrat Kohanim: priests with a blemish or unkempt hair may not enter."),
            "heikhal": ("Heikhal", "היכל", "1:9", "Holier still: no one enters without having washed hands and feet."),
            "kodesh_hakodashim": ("Kodesh HaKodashim", "קודש הקודשים", "1:9", "Holiest of all: no one enters but the Kohen Gadol, on Yom Kippur, at the hour of the service."),
        },
    },
    "he": {
        "chemin": "he/",
        "sens": "rtl",
        "nom_langue": "עברית",
        "titre": "בית המקדש, סיור תלת־ממדי",
        "description": "בית המקדש משוחזר לפי מידות המשנה. סיור חופשי מהר הבית ועד קודש הקודשים, שבו כל אבן מציינת את מקורה.",
        "nav_langue": "שפה",
        "hebreu": "בית המקדש",
        "latin": "Beit HaMikdach",
        "accroche": "בית המקדש, משוחזר בתלת־ממד לפי מידות המשנה. נכנסים ברגל, מהלכים בחופשיות, וכל אבן אומרת מניין היא באה.",
        "entrer": "כניסה לסיור",
        "entrer_note": "חינם, ללא התקנה. עשר דקות או שעה.",
        "degres_titre": "מעלות הקדושה",
        "mishna": "משנה כלים",
        "degres": {
            "har_habayit": ("הר הבית", "", "א, ח", "מְקֻדָּשׁ מִירוּשָׁלַיִם, שֶׁאֵין זָבִים וְזָבוֹת, נִדּוֹת וְיוֹלְדוֹת נִכְנָסִים לְשָׁם."),
            "heil": ("חיל", "", "א, ח", "מְקֻדָּשׁ מִמֶּנּוּ, שֶׁאֵין גּוֹיִם וּטְמֵא מֵת נִכְנָסִים לְשָׁם."),
            "ezrat_nashim": ("עזרת נשים", "", "א, ח", "מְקֻדֶּשֶׁת מִמֶּנּוּ, שֶׁאֵין טְבוּל יוֹם נִכְנָס לְשָׁם."),
            "azara": ("עזרת ישראל", "", "א, ח", "מְקֻדֶּשֶׁת מִמֶּנָּה, שֶׁאֵין מְחֻסַּר כִּפּוּרִים נִכְנָס לְשָׁם."),
            "mizbeach": ("עזרת כהנים", "", "א, ח", "מְקֻדֶּשֶׁת מִמֶּנָּה, שֶׁאֵין יִשְׂרָאֵל נִכְנָסִים לְשָׁם אֶלָּא בִשְׁעַת צָרְכֵיהֶם, לִסְמִיכָה לִשְׁחִיטָה וְלִתְנוּפָה."),
            "oulam": ("בין האולם ולמזבח", "", "א, ט", "מְקֻדָּשׁ מִמֶּנָּה, שֶׁאֵין בַּעֲלֵי מוּמִין וּפְרוּעֵי רֹאשׁ נִכְנָסִים לְשָׁם."),
            "heikhal": ("היכל", "", "א, ט", "מְקֻדָּשׁ מִמֶּנּוּ, שֶׁאֵין נִכְנָס לְשָׁם שֶׁלֹּא רְחוּץ יָדַיִם וְרַגְלָיִם."),
            "kodesh_hakodashim": ("קודש הקודשים", "", "א, ט", "מְקֻדָּשׁ מֵהֶם, שֶׁאֵין נִכְנָס לְשָׁם אֶלָּא כֹהֵן גָּדוֹל בְּיוֹם הַכִּפּוּרִים בִּשְׁעַת הָעֲבוֹדָה."),
        },
    },
}

AUTEUR = {"fr": "David Bonan", "en": "David Bonan", "he": "דוד בונן"}


def arrivees():
    """Le temps d'arrivée à chaque halte et la pause qu'on y fait, comme cinema.js les compte."""
    temps, resultat = 0.0, []
    for i, halte in enumerate(PARCOURS["haltes"]):
        temps += 0 if i == 0 else halte["duree_s"]
        pause = halte.get("pause_s", 3)
        resultat.append((halte, temps, pause))
        temps += pause
    return resultat


def vision(halte):
    d = halte["degre"]
    return (f'<img class="vision" data-degre="{d}" src="/images/{d}_2000.webp" '
            f'srcset="/images/{d}_1000.webp 1000w, /images/{d}_2000.webp 2000w" sizes="100vw" alt="" decoding="async">')


def nav_langues(code):
    liens = []
    for autre, t in TEXTES.items():
        courant = ' aria-current="page"' if autre == code else ""
        sens = ' dir="rtl"' if t["sens"] == "rtl" else ' dir="ltr"'
        liens.append(f'<a href="/{t["chemin"]}" lang="{autre}"{sens}{courant}>{t["nom_langue"]}</a>')
    return "\n    ".join(liens)


def hreflangs():
    lignes = [f'<link rel="alternate" hreflang="{c}" href="{DOMAINE}/{t["chemin"]}">' for c, t in TEXTES.items()]
    lignes.append(f'<link rel="alternate" hreflang="x-default" href="{DOMAINE}/">')
    return "\n".join(lignes)


def echelon(t, halte, premier):
    nom = t["degres"][halte["degre"]][0]
    courant = ' aria-current="true"' if premier else ""
    return f'<li><button type="button" data-degre="{halte["degre"]}" title="{nom}" aria-label="{nom}"{courant}></button></li>'


def degre(t, halte, temps, pause, premier):
    nom, hebreu, ref, phrase = t["degres"][halte["degre"]]
    courant = ' aria-current="true"' if premier else ""
    titre = f'<span class="nom">{nom}</span>'
    if hebreu:
        titre += f' <span class="nom-he" lang="he" dir="rtl">{hebreu}</span>'
    return f'''
      <li data-degre="{halte["degre"]}" data-vue="{halte["vue"]}" data-temps="{temps:g}" data-pause="{pause:g}"{courant}>
        <h2>{titre}</h2>
        <p class="mishna">{phrase}</p>
        <p class="source">{t["mishna"]} {ref}</p>
      </li>'''


def page(code):
    t = TEXTES[code]
    url = f'{DOMAINE}/{t["chemin"]}'
    haltes = arrivees()
    degres = "".join(degre(t, halte, temps, pause, i == 0) for i, (halte, temps, pause) in enumerate(haltes))
    echelle = "".join(echelon(t, halte, i == 0) for i, (halte, _, _) in enumerate(haltes))
    visions = "".join(vision(halte) for halte, _, _ in haltes)
    return f'''<!doctype html>
<html lang="{code}" dir="{t["sens"]}">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#100e0b">
<title>{t["titre"]}</title>
<meta name="description" content="{t["description"]}">
<link rel="canonical" href="{url}">
{hreflangs()}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Beit HaMikdach">
<meta property="og:title" content="{t["titre"]}">
<meta property="og:description" content="{t["description"]}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{DOMAINE}/images/partage.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Serif+4:ital,opsz,wght@0,8..60,300..600;1,8..60,300..600&family=Frank+Ruhl+Libre:wght@300;400;500&display=swap">
<link rel="stylesheet" href="/style.css">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" as="image" href="/images/affiche_2000.webp" imagesrcset="/images/affiche_1000.webp 1000w, /images/affiche_2000.webp 2000w" imagesizes="100vw" media="(min-aspect-ratio: 4/5)">
<link rel="preload" as="image" href="/images/affiche_portrait_720.webp" media="(max-aspect-ratio: 4/5)">

<main class="scene">
  <div class="fond">
    <picture class="affiche">
      <source media="(max-aspect-ratio: 4/5)" srcset="/images/affiche_portrait_720.webp">
      <img src="/images/affiche_2000.webp" srcset="/images/affiche_1000.webp 1000w, /images/affiche_2000.webp 2000w" sizes="100vw" alt="" fetchpriority="high">
    </picture>
    <iframe class="vivante" title="" tabindex="-1" aria-hidden="true" hidden></iframe>
    <video class="vivante" muted playsinline loop preload="none" aria-hidden="true" data-src="/images/parcours_portrait.mp4" hidden></video>
    <div class="visions" aria-hidden="true">{visions}</div>
  </div>

  <nav aria-label="{t["nav_langue"]}">
    {nav_langues(code)}
  </nav>

  <div class="titre">
    <h1><span class="he" lang="he" dir="rtl">{t["hebreu"]}</span><span class="latin" lang="fr">{t["latin"]}</span></h1>
    <p class="accroche">{t["accroche"]}</p>
    <p class="action"><a class="entrer" href="/visite/" data-langue="{code}">{t["entrer"]}</a><span class="note">{t["entrer_note"]}</span></p>
  </div>

  <section class="degres" aria-label="{t["degres_titre"]}">
    <ol class="echelle" aria-label="{t["degres_titre"]}">{echelle}</ol>
    <ul aria-live="polite">{degres}
    </ul>
  </section>

  <footer>
    <span>© 2026 {AUTEUR[code]}</span>
  </footer>
</main>

<script src="/accueil.js" defer></script>
</html>
'''


for code, t in TEXTES.items():
    cible = SITE / t["chemin"] / "index.html"
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(page(code), encoding="utf-8")
    print(cible.relative_to(SITE.parent))
