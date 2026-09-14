#!/usr/bin/env python3
"""Écrit index.html, en/index.html et he/index.html depuis un gabarit et les textes ci-dessous.

    python3 site/accueil.py
"""
from pathlib import Path

SITE = Path(__file__).resolve().parent
DOMAINE = "https://bethhamikdach.com"

DEGRES = [("har_habayit", "har_habayit"), ("heil", "face_porte_est"), ("ezrat_nashim", "ezrat_nashim"), ("azara", "azara"),
          ("mizbeach", "mizbeach"), ("oulam", "oulam"), ("heikhal", "heikhal"), ("kodesh_hakodashim", "kodesh_hakodashim")]

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
        "intro": [
            "La visite est une scène en trois dimensions que l'on parcourt au clavier, à la souris ou au doigt. Les cours, les portes, les chambres, l'autel et le Sanctuaire sont bâtis en volumes aux mesures du traité <i>Middot</i>, la seule description mesurée d'un Temple debout.",
            "Un clic sur une porte, un ustensile ou un vêtement dit ce que c'est, sa mesure, et cite le texte : <i>Middot</i>, <i>Tamid</i>, <i>Yoma</i>, le Rambam, avec le lien vers Sefaria. Là où les sources divergent ou se taisent, la visite indique l'avis retenu, l'avis écarté, et ce qui n'est qu'un choix du projet.",
        ],
        "montee_titre": "La montée",
        "montee_intro": "La Mishna compte dix degrés de sainteté, du pays d'Israël au Kodesh HaKodashim, et définit chacun par ceux qui n'y entrent plus (<i>Kelim</i> 1:6-9). La visite parcourt les huit derniers. Cette page aussi : plus on avance, plus la lumière se resserre.",
        "aller": "Y aller",
        "degres": {
            "har_habayit": ("Har HaBayit", "הר הבית", "Plus saint que Jérusalem : les zavim, les zavot, les niddot et les accouchées n'y entrent pas."),
            "heil": ("Heil", "חיל", "Plus saint que le Har HaBayit : les non-Juifs et ceux qu'un mort a rendus impurs n'y entrent pas."),
            "ezrat_nashim": ("Ezrat Nashim", "עזרת נשים", "Plus sainte que le Heil : celui qui s'est immergé le jour même n'y entre pas avant le coucher du soleil."),
            "azara": ("Ezrat Israël", "עזרת ישראל", "Plus sainte que l'Ezrat Nashim : celui à qui il manque encore une offrande d'expiation n'y entre pas."),
            "mizbeach": ("Ezrat Cohanim", "עזרת כהנים", "Plus sainte que l'Ezrat Israël : les Israélites n'y entrent que pour ce qui les requiert, la semikha, la she'hita et la tenoufa."),
            "oulam": ("Entre l'Oulam et l'autel", "בין האולם ולמזבח", "Plus saint que l'Ezrat Cohanim : les cohanim atteints d'un défaut ou aux cheveux défaits n'y entrent pas."),
            "heikhal": ("Heikhal", "היכל", "Plus saint encore : nul n'y entre sans s'être lavé les mains et les pieds."),
            "kodesh_hakodashim": ("Kodesh HaKodashim", "קודש הקודשים", "Plus saint que tout : nul n'y entre, sinon le Cohen Gadol, le jour de Kippour, à l'heure du service."),
        },
        "methode_titre": "Comment c'est fait",
        "methode": [
            "La scène est générée par un script dans Blender, cote par cote, depuis la fiche technique du projet. Le plan et les mesures viennent de <i>Middot</i> ; ce que le Premier Temple avait sans que <i>Middot</i> le répète y revient quand le Tanakh le décrit et que rien ne l'abroge. C'est donc le Temple à venir, qui n'est ni le Premier ni le Second : l'Arche est de retour sur l'Even HaShetiya, Yakhin et Boaz sont debout dans l'Oulam.",
            "Les cohanim et les Léviim qui peuplent la visite sont vêtus d'après le Rambam, <i>Klei HaMikdash</i>. Les images de cette page sont tirées du film en préparation : le rendu de la scène, repeint en photographie sans qu'une pierre ne bouge.",
        ],
        "hoshen_legende": "Le 'Hoshen du Cohen Gadol, douze pierres aux noms des tribus.",
        "sources_titre": "Les sources",
        "sources": "Mishna <i>Middot</i>, <i>Tamid</i>, <i>Yoma</i>, <i>Kelim</i> ; Talmud de Babylone ; Rambam, <i>Hilkhot Beit HaBe'hira</i> et <i>Klei HaMikdash</i>. Les textes sont lus sur Sefaria, et chaque citation de la visite y renvoie.",
        "pied_auteur": "Une reconstitution de",
        "pied_textes": "Textes de la Mishna d'après Sefaria.",
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
        "intro": [
            "The tour is a three-dimensional scene you walk through with a keyboard, a mouse or a finger. Courtyards, gates, chambers, the altar and the Sanctuary are built in volumes to the measurements of tractate <i>Middot</i>, the only measured description of a standing Temple.",
            "Click a gate, a vessel or a garment and it tells you what it is, its measure, and the text behind it: <i>Middot</i>, <i>Tamid</i>, <i>Yoma</i>, the Rambam, with a link to Sefaria. Where the sources disagree or fall silent, the tour says which opinion was kept, which was set aside, and what is merely a choice of the project.",
        ],
        "montee_titre": "The ascent",
        "montee_intro": "The Mishnah counts ten degrees of holiness, from the land of Israel to the Kodesh HaKodashim, and defines each by those who may no longer enter (<i>Kelim</i> 1:6-9). The tour covers the last eight. So does this page: the further you go, the narrower the light.",
        "aller": "Go there",
        "degres": {
            "har_habayit": ("Har HaBayit", "הר הבית", "Holier than Jerusalem: zavim, zavot, menstruants and women after childbirth may not enter."),
            "heil": ("Chel", "חיל", "Holier than the Har HaBayit: non-Jews and those made impure by a corpse may not enter."),
            "ezrat_nashim": ("Ezrat Nashim", "עזרת נשים", "Holier than the Chel: one who immersed that same day may not enter before sunset."),
            "azara": ("Ezrat Israel", "עזרת ישראל", "Holier than the Ezrat Nashim: one who still owes an offering of atonement may not enter."),
            "mizbeach": ("Ezrat Kohanim", "עזרת כהנים", "Holier than the Ezrat Israel: Israelites enter only for what requires them, the semikhah, the shechitah and the tenufah."),
            "oulam": ("Between the Ulam and the altar", "בין האולם ולמזבח", "Holier than the Ezrat Kohanim: priests with a blemish or unkempt hair may not enter."),
            "heikhal": ("Heikhal", "היכל", "Holier still: no one enters without having washed hands and feet."),
            "kodesh_hakodashim": ("Kodesh HaKodashim", "קודש הקודשים", "Holiest of all: no one enters but the Kohen Gadol, on Yom Kippur, at the hour of the service."),
        },
        "methode_titre": "How it is made",
        "methode": [
            "The scene is generated by a script in Blender, measure by measure, from the project's technical sheet. The plan and the dimensions come from <i>Middot</i>; what the First Temple had without <i>Middot</i> repeating it returns when the Tanakh describes it and nothing abolishes it. It is therefore the Temple to come, neither the First nor the Second: the Ark is back on the Even HaShetiya, Yakhin and Boaz stand in the Ulam.",
            "The kohanim and Levi'im who people the tour are dressed after the Rambam, <i>Klei HaMikdash</i>. The images on this page come from the film in preparation: the render of the scene, repainted as a photograph without a single stone moving.",
        ],
        "hoshen_legende": "The Choshen of the Kohen Gadol, twelve stones bearing the names of the tribes.",
        "sources_titre": "The sources",
        "sources": "Mishnah <i>Middot</i>, <i>Tamid</i>, <i>Yoma</i>, <i>Kelim</i>; the Babylonian Talmud; Rambam, <i>Hilkhot Beit HaBechirah</i> and <i>Klei HaMikdash</i>. The texts are read on Sefaria, and every citation in the tour links there.",
        "pied_auteur": "A reconstruction by",
        "pied_textes": "Mishnah texts after Sefaria.",
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
        "intro": [
            "הסיור הוא סצנה תלת־ממדית שמהלכים בה במקלדת, בעכבר או באצבע. העזרות, השערים, הלשכות, המזבח וההיכל בנויים בנפחים לפי מידות מסכת <i>מידות</i>, התיאור המדוד היחיד של מקדש עומד.",
            "לחיצה על שער, על כלי או על בגד אומרת מהו, מה מידתו, ומצטטת את המקור: <i>מידות</i>, <i>תמיד</i>, <i>יומא</i>, הרמב״ם, עם קישור לספריא. במקום שהמקורות חלוקים או שותקים, הסיור מציין את הדעה שנתקבלה, את הדעה שנדחתה, ומה שאינו אלא בחירה של הפרויקט.",
        ],
        "montee_titre": "העלייה",
        "montee_intro": "המשנה מונה עשר קדושות, מארץ ישראל ועד קודש הקודשים, ומגדירה כל אחת במי שאינו נכנס לשם עוד (<i>כלים</i> א, ו–ט). הסיור עובר בשמונה האחרונות. וכך גם הדף הזה: ככל שמתקדמים, האור מצטמצם.",
        "aller": "ללכת לשם",
        "degres": {
            "har_habayit": ("הר הבית", "", "מְקֻדָּשׁ מִירוּשָׁלַיִם, שֶׁאֵין זָבִים וְזָבוֹת, נִדּוֹת וְיוֹלְדוֹת נִכְנָסִים לְשָׁם."),
            "heil": ("חיל", "", "מְקֻדָּשׁ מִמֶּנּוּ, שֶׁאֵין גּוֹיִם וּטְמֵא מֵת נִכְנָסִים לְשָׁם."),
            "ezrat_nashim": ("עזרת נשים", "", "מְקֻדֶּשֶׁת מִמֶּנּוּ, שֶׁאֵין טְבוּל יוֹם נִכְנָס לְשָׁם."),
            "azara": ("עזרת ישראל", "", "מְקֻדֶּשֶׁת מִמֶּנָּה, שֶׁאֵין מְחֻסַּר כִּפּוּרִים נִכְנָס לְשָׁם."),
            "mizbeach": ("עזרת כהנים", "", "מְקֻדֶּשֶׁת מִמֶּנָּה, שֶׁאֵין יִשְׂרָאֵל נִכְנָסִים לְשָׁם אֶלָּא בִשְׁעַת צָרְכֵיהֶם, לִסְמִיכָה לִשְׁחִיטָה וְלִתְנוּפָה."),
            "oulam": ("בין האולם ולמזבח", "", "מְקֻדָּשׁ מִמֶּנָּה, שֶׁאֵין בַּעֲלֵי מוּמִין וּפְרוּעֵי רֹאשׁ נִכְנָסִים לְשָׁם."),
            "heikhal": ("היכל", "", "מְקֻדָּשׁ מִמֶּנּוּ, שֶׁאֵין נִכְנָס לְשָׁם שֶׁלֹּא רְחוּץ יָדַיִם וְרַגְלָיִם."),
            "kodesh_hakodashim": ("קודש הקודשים", "", "מְקֻדָּשׁ מֵהֶם, שֶׁאֵין נִכְנָס לְשָׁם אֶלָּא כֹהֵן גָּדוֹל בְּיוֹם הַכִּפּוּרִים בִּשְׁעַת הָעֲבוֹדָה."),
        },
        "methode_titre": "איך זה נעשה",
        "methode": [
            "הסצנה נוצרת בסקריפט בבלנדר, מידה אחר מידה, מתוך הדף הטכני של הפרויקט. התוכנית והמידות לקוחות ממסכת <i>מידות</i>; מה שהיה במקדש הראשון ושמסכת <i>מידות</i> אינה חוזרת עליו שב אליו כאשר התנ״ך מתאר אותו ודבר אינו מבטלו. זהו אפוא המקדש העתיד להיבנות, לא הראשון ולא השני: הארון חזר על אבן השתייה, יכין ובועז עומדים באולם.",
            "הכהנים והלויים המאכלסים את הסיור לבושים על פי הרמב״ם, <i>הלכות כלי המקדש</i>. התמונות בדף זה לקוחות מן הסרט שבהכנה: רינדור הסצנה, שצויר מחדש כצילום בלי שאבן אחת תזוז.",
        ],
        "hoshen_legende": "חושן הכהן הגדול, שתים עשרה אבנים בשמות השבטים.",
        "sources_titre": "המקורות",
        "sources": "משנה <i>מידות</i>, <i>תמיד</i>, <i>יומא</i>, <i>כלים</i>; תלמוד בבלי; רמב״ם, <i>הלכות בית הבחירה</i> ו<i>הלכות כלי המקדש</i>. הטקסטים נקראים בספריא, וכל ציטוט בסיור מקשר לשם.",
        "pied_auteur": "שחזור מאת",
        "pied_textes": "נוסח המשנה על פי ספריא.",
    },
}

AUTEUR = {"fr": "David Bonan", "en": "David Bonan", "he": "דוד בונן"}


def image(nom, alt, classe=""):
    return (
        f'<img class="{classe}" src="/images/{nom}_2000.webp" '
        f'srcset="/images/{nom}_1000.webp 1000w, /images/{nom}_2000.webp 2000w" '
        f'sizes="(min-width: 1500px) 1400px, 100vw" alt="{alt}" loading="lazy" decoding="async">'
    )


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


def degre(code, t, identifiant, vue, rang):
    nom, hebreu, phrase = t["degres"][identifiant]
    titre = f'<span class="nom">{nom}</span>'
    if hebreu:
        titre += f' <span class="nom-he" lang="he" dir="rtl">{hebreu}</span>'
    return f'''
  <section class="degre" data-degre="{rang}" id="{identifiant}">
    <figure>{image(identifiant, nom)}</figure>
    <div class="texte">
      <h3>{titre}</h3>
      <p class="mishna">{phrase}</p>
      <a class="aller" href="/visite/?vue={vue}" data-langue="{code}">{t["aller"]}</a>
    </div>
  </section>'''


def page(code):
    t = TEXTES[code]
    url = f'{DOMAINE}/{t["chemin"]}'
    intro = "\n".join(f"    <p>{p}</p>" for p in t["intro"])
    methode = "\n".join(f"    <p>{p}</p>" for p in t["methode"])
    degres = "".join(degre(code, t, identifiant, vue, i + 1) for i, (identifiant, vue) in enumerate(DEGRES))
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
<meta property="og:image" content="{DOMAINE}/images/seuil_2000.webp">
<meta property="og:image:width" content="2000">
<meta property="og:image:height" content="1117">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Marcellus&family=Source+Serif+4:ital,opsz,wght@0,8..60,300..600;1,8..60,300..600&family=Frank+Ruhl+Libre:wght@300;400;500&display=swap">
<link rel="stylesheet" href="/style.css">
<link rel="preload" as="image" href="/images/seuil_2000.webp" imagesrcset="/images/seuil_1000.webp 1000w, /images/seuil_2000.webp 2000w" imagesizes="100vw">

<header class="seuil">
  <nav aria-label="{t["nav_langue"]}">
    {nav_langues(code)}
  </nav>
  <img class="fond" src="/images/seuil_2000.webp" srcset="/images/seuil_1000.webp 1000w, /images/seuil_2000.webp 2000w" sizes="100vw" alt="" fetchpriority="high">
  <div class="titre">
    <h1><span class="he" lang="he" dir="rtl">{t["hebreu"]}</span><span class="latin" lang="fr">{t["latin"]}</span></h1>
    <p class="accroche">{t["accroche"]}</p>
    <p class="action"><a class="entrer" href="/visite/" data-langue="{code}">{t["entrer"]}</a><span class="note">{t["entrer_note"]}</span></p>
  </div>
</header>

<main>
  <section class="propos" data-degre="0">
{intro}
  </section>

  <section class="montee-tete" data-degre="0">
    <h2>{t["montee_titre"]}</h2>
    <p>{t["montee_intro"]}</p>
  </section>
{degres}

  <section class="methode" data-degre="8">
    <h2>{t["methode_titre"]}</h2>
{methode}
    <figure class="hoshen">{image("hoshen", t["hoshen_legende"])}<figcaption>{t["hoshen_legende"]}</figcaption></figure>
    <h2>{t["sources_titre"]}</h2>
    <p>{t["sources"]}</p>
    <p class="action"><a class="entrer" href="/visite/" data-langue="{code}">{t["entrer"]}</a></p>
  </section>
</main>

<footer data-degre="8">
  <span>{t["pied_auteur"]} <a href="https://davidbonan.io">{AUTEUR[code]}</a></span>
  <span>{t["pied_textes"]}</span>
</footer>

<script src="/montee.js" defer></script>
</html>
'''


for code, t in TEXTES.items():
    cible = SITE / t["chemin"] / "index.html"
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(page(code), encoding="utf-8")
    print(cible.relative_to(SITE.parent))
