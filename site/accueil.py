#!/usr/bin/env python3
"""Écrit index.html, en/index.html et he/index.html depuis un gabarit et les textes ci-dessous.

    python3 site/accueil.py

L'accueil est une montée en images : l'affiche en seuil, puis les degrés de sainteté
(Kelim 1:8-9) un à un sur une scène épinglée, chacun par l'image du film prise de ce point
(site/images/<degré>_1000 et _2000.webp) qui se fond dans la suivante au fil du défilement,
et le Kodesh HaKodashim en finale. Chaque légende mène à la visite, à la vue du même point.

Avant la montée, les lishkot : une plongée sur les cours (site/images/lishkot_*.webp, caméra
ACC_09_Lishkot), un repère par chambre à sa place projetée dans le cadre.

Deux kavanot en encadrent le parcours, sur fond nuit : Choulhan Aroukh OH 95:2 après le seuil,
Berakhot 30a avant le Kodesh HaKodashim.
"""
import json
from pathlib import Path

SITE = Path(__file__).resolve().parent
DOMAINE = "https://bethhamikdach.com"

# Les degrés dans l'ordre de la montée, et la vue de la visite prise du même point.
DEGRES = [
    ("har_habayit", "har_habayit"),
    ("heil", "face_porte_est"),
    ("ezrat_nashim", "ezrat_nashim"),
    ("azara", "azara"),
    ("mizbeach", "mizbeach"),
    ("oulam", "oulam"),
    ("heikhal", "heikhal"),
    ("kodesh_hakodashim", "kodesh_hakodashim"),
]

# Chaque chambre à la place où la caméra ACC_09_Lishkot la projette, en % du cadre, dans l'ordre de la marche.
CHAMBRES = [
    ("lishkat_hanezirim", 72.2, 90.9),
    ("lishkat_haetzim", 79.4, 65.1),
    ("lishkat_hametzoraim", 64.2, 51.4),
    ("lishkat_beit_shemanya", 56.3, 75.5),
    ("lishkat_pinchas", 56.9, 53.6),
    ("lishkat_osei_chavitin", 54.7, 60.0),
    ("beit_hamoked", 61.0, 36.2),
    ("beit_hatevila", 35.6, 28.2),
    ("beit_hanitzotz", 45.3, 22.4),
    ("lishkat_hagazit", 40.8, 19.9),
    ("lishkat_hagola", 37.9, 14.7),
    ("lishkat_haetz", 41.0, 12.9),
    ("lishkat_hamelach", 45.3, 68.7),
    ("lishkat_haparva", 37.8, 60.8),
    ("lishkat_hamedichin", 34.6, 58.0),
    ("lishkat_parhedrin", 43.9, 74.0),
    ("beit_avtinas", 47.4, 75.1),
]
SOUTERRAINES = {"beit_hatevila"}

TEXTES = {
    "fr": {
        "chemin": "",
        "sens": "ltr",
        "nom_langue": "Français",
        "titre": "Beit HaMikdach, le Temple de Jérusalem en trois dimensions",
        "description": "Le Temple de Jérusalem reconstruit aux cotes de la Mishna. Une visite libre, du Har HaBayit au Kodesh HaKodashim, où chaque pierre cite sa source.",
        "nav_langue": "Langue",
        "nav_depot": "Le projet sur GitHub",
        "hebreu": "בית המקדש",
        "latin": "Beit HaMikdach",
        "accroche": "Le Temple de Jérusalem, reconstruit en trois dimensions aux cotes de la Mishna. On y entre à pied, on y marche librement, et chaque pierre dit d'où elle vient.",
        "entrer": "Entrer dans la visite",
        "entrer_note": "Gratuit, sans installation. Dix minutes ou une heure.",
        "kavanot": {
            "amida": ("Il doit incliner un peu la tête, les yeux baissés vers la terre, et se considérer comme s'il se tenait dans le Beit HaMikdach ; et dans son cœur, se tourner vers le haut, vers le ciel.", "Choul'han Aroukh, Ora'h 'Haïm 95:2"),
            "makom_ehad": ("Celui qui se tient hors de la terre d'Israël dirige son cœur vers la terre d'Israël ; en terre d'Israël, vers Jérusalem ; à Jérusalem, vers le Beit HaMikdach ; dans le Beit HaMikdach, vers le Kodesh HaKodashim ; dans le Kodesh HaKodashim, vers le Beit HaKaporet… Ainsi tout Israël dirige son cœur vers un seul lieu.", "Berakhot 30a"),
        },
        "degres_titre": "Les degrés de sainteté",
        "ouverture": "Du Har HaBayit au Kodesh HaKodashim, la Mishna Kelim compte les degrés de sainteté. À chacun, moins de monde entre.",
        "voir": "Voir dans la visite",
        "mishna": "Mishna Kelim",
        "lishkot_titre": "Les lishkot",
        "lishkot_ouverture": "Autour des cours, dix-sept chambres, chacune à son service. Le Sanhédrin siège dans l'une, on sale les peaux dans une autre, le Cohen Gadol s'immerge sur un toit. Toutes sont bâties dans la visite.",
        "sous_terre": "sous terre",
        "chambres": {
            "lishkat_hanezirim": ("Les nazirs y font cuire leurs offrandes de paix, et y jettent sous la marmite la chevelure qu'ils ont rasée.", "Middot 2:5"),
            "lishkat_haetzim": ("Les cohanim atteints d'un défaut y trient le bois de l'autel et écartent toute bûche véreuse.", "Middot 2:5"),
            "lishkat_hametzoraim": ("La cour sans toit des metzoraïm.", "Middot 2:5"),
            "lishkat_beit_shemanya": ("La réserve du vin et de l'huile, selon Abba Shaoul.", "Middot 2:5"),
            "lishkat_pinchas": ("Pin'has, l'habilleur, y vêt les cohanim pour le service.", "Middot 1:4 ; Shekalim 5:1"),
            "lishkat_osei_chavitin": ("On y prépare les 'havitin, l'offrande quotidienne du Cohen Gadol.", "Middot 1:4"),
            "beit_hamoked": ("Une grande salle voûtée où dorment les anciens de la garde, les clefs de l'Azara en main.", "Middot 1:8"),
            "beit_hatevila": ("Sous l'Azara, au bout d'un tunnel éclairé : le cohen devenu impur la nuit s'y immerge puis se réchauffe au feu.", "Tamid 1:1"),
            "beit_hanitzotz": ("L'étage au-dessus de la porte : les cohanim y montent la garde en haut, les Léviim en bas.", "Middot 1:5"),
            "lishkat_hagazit": ("La salle de pierre taillée, où siège le Grand Sanhédrin d'Israël.", "Middot 5:4"),
            "lishkat_hagola": ("Un puits creusé, une roue posée dessus : c'est de là que l'eau vient à toute l'Azara.", "Middot 5:4"),
            "lishkat_haetz": ("« J'ai oublié à quoi elle servait », dit Rabbi Eliézer ben Yaakov.", "Middot 5:4"),
            "lishkat_hamelach": ("On y garde le sel des korbanot.", "Middot 5:3"),
            "lishkat_haparva": ("On y sale les peaux des offrandes ; sur son toit, le bain du Cohen Gadol à Kippour.", "Middot 5:3"),
            "lishkat_hamedichin": ("On y rince les entrailles des offrandes ; une montée en vis mène au toit de la Parva.", "Middot 5:3"),
            "lishkat_parhedrin": ("Le Cohen Gadol y demeure les sept jours qui précèdent Kippour.", "Yoma 1:1"),
            "beit_avtinas": ("La famille d'Avtinas y prépare l'encens, dont elle garde le secret.", "Tamid 1:1 ; Yoma 3:11"),
        },
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
        "nav_depot": "The project on GitHub",
        "hebreu": "בית המקדש",
        "latin": "Beit HaMikdach",
        "accroche": "The Temple of Jerusalem, rebuilt in three dimensions to the measurements of the Mishnah. You enter on foot, walk where you like, and every stone tells you where it comes from.",
        "entrer": "Enter the tour",
        "entrer_note": "Free, nothing to install. Ten minutes or an hour.",
        "kavanot": {
            "amida": ("He should bow his head slightly, his eyes cast down toward the earth, and consider himself as if standing in the Beit HaMikdash; and in his heart direct himself upward, toward heaven.", "Shulchan Arukh, Orach Chayim 95:2"),
            "makom_ehad": ("One standing outside the Land of Israel directs his heart toward the Land of Israel; in the Land of Israel, toward Jerusalem; in Jerusalem, toward the Beit HaMikdash; in the Beit HaMikdash, toward the Kodesh HaKodashim; in the Kodesh HaKodashim, toward the Beit HaKaporet… Thus all Israel direct their hearts toward one place.", "Berakhot 30a"),
        },
        "degres_titre": "The degrees of holiness",
        "ouverture": "From the Har HaBayit to the Kodesh HaKodashim, Mishnah Kelim counts the degrees of holiness. At each one, fewer may enter.",
        "voir": "See it in the tour",
        "mishna": "Mishnah Kelim",
        "lishkot_titre": "The lishkot",
        "lishkot_ouverture": "Around the courts, seventeen chambers, each with its own service. The Sanhedrin sits in one, hides are salted in another, the Kohen Gadol immerses on a rooftop. Every one of them is built in the tour.",
        "sous_terre": "underground",
        "chambres": {
            "lishkat_hanezirim": ("The nazirites cook their peace offerings here, and throw the hair they have shaved under the pot.", "Middot 2:5"),
            "lishkat_haetzim": ("Blemished kohanim sort the wood for the altar here and set aside every wormy log.", "Middot 2:5"),
            "lishkat_hametzoraim": ("The roofless court of the metzora'im.", "Middot 2:5"),
            "lishkat_beit_shemanya": ("The store of wine and oil, according to Abba Shaul.", "Middot 2:5"),
            "lishkat_pinchas": ("Pinchas the dresser clothes the kohanim here for the service.", "Middot 1:4; Shekalim 5:1"),
            "lishkat_osei_chavitin": ("The chavitin are made here, the daily offering of the Kohen Gadol.", "Middot 1:4"),
            "beit_hamoked": ("A great vaulted hall where the elders of the watch sleep, the keys of the Azara in their hands.", "Middot 1:8"),
            "beit_hatevila": ("Beneath the Azara, at the end of a lamplit tunnel: a kohen made impure in the night immerses here, then warms himself by the fire.", "Tamid 1:1"),
            "beit_hanitzotz": ("The upper storey over the gate: kohanim keep watch above, Levites below.", "Middot 1:5"),
            "lishkat_hagazit": ("The hall of hewn stone, where the Great Sanhedrin of Israel sits.", "Middot 5:4"),
            "lishkat_hagola": ("A cistern dug out, a wheel set over it: from here water reaches the whole Azara.", "Middot 5:4"),
            "lishkat_haetz": ("“I have forgotten what it was used for,” says Rabbi Eliezer ben Yaakov.", "Middot 5:4"),
            "lishkat_hamelach": ("The salt for the korbanot is kept here.", "Middot 5:3"),
            "lishkat_haparva": ("The hides of the offerings are salted here; on its roof, the bath of the Kohen Gadol on Yom Kippur.", "Middot 5:3"),
            "lishkat_hamedichin": ("The entrails of the offerings are rinsed here; a winding stair climbs to the roof of the Parva.", "Middot 5:3"),
            "lishkat_parhedrin": ("The Kohen Gadol stays here for the seven days before Yom Kippur.", "Yoma 1:1"),
            "beit_avtinas": ("The house of Avtinas prepares the incense here, and keeps its secret.", "Tamid 1:1; Yoma 3:11"),
        },
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
        "nav_depot": "הפרויקט בגיטהאב",
        "hebreu": "בית המקדש",
        "latin": "Beit HaMikdach",
        "accroche": "בית המקדש, משוחזר בתלת־ממד לפי מידות המשנה. נכנסים ברגל, מהלכים בחופשיות, וכל אבן אומרת מניין היא באה.",
        "entrer": "כניסה לסיור",
        "entrer_note": "חינם, ללא התקנה. עשר דקות או שעה.",
        "kavanot": {
            "amida": ("", "שולחן ערוך, אורח חיים צה, ב"),
            "makom_ehad": ("", "ברכות ל, א"),
        },
        "degres_titre": "מעלות הקדושה",
        "ouverture": "מהר הבית ועד קודש הקודשים מונה משנה כלים את מעלות הקדושה. בכל מעלה נכנסים פחות.",
        "voir": "לראות בסיור",
        "mishna": "משנה כלים",
        "lishkot_titre": "הלשכות",
        "lishkot_ouverture": "סביב העזרות שבע־עשרה לשכות, לכל אחת עבודתה. באחת יושבת הסנהדרין, באחרת מולחים עורות, ועל גג אחת טובל הכהן הגדול. כולן בנויות בסיור.",
        "sous_terre": "מתחת לקרקע",
        "chambres": {
            "lishkat_hanezirim": ("שֶׁשָּׁם הַנְּזִירִים מְבַשְּׁלִין אֶת שַׁלְמֵיהֶן, וּמְגַלְּחִין אֶת שְׂעָרָן, וּמְשַׁלְּחִים תַּחַת הַדּוּד.", "מידות ב, ה"),
            "lishkat_haetzim": ("שֶׁשָּׁם הַכֹּהֲנִים בַּעֲלֵי מוּמִין מַתְלִיעִין הָעֵצִים.", "מידות ב, ה"),
            "lishkat_hametzoraim": ("חצר שאינה מקורה, לשכת המצורעים.", "מידות ב, ה"),
            "lishkat_beit_shemanya": ("אַבָּא שָׁאוּל אוֹמֵר, שָׁם הָיוּ נוֹתְנִין יַיִן וָשֶׁמֶן.", "מידות ב, ה"),
            "lishkat_pinchas": ("בה מלביש פנחס המלביש את הכהנים לעבודה.", "מידות א, ד; שקלים ה, א"),
            "lishkat_osei_chavitin": ("בה עושים את החביתין, מנחת הכהן הגדול שבכל יום.", "מידות א, ד"),
            "beit_hamoked": ("כִּפָּה, וּבַיִת גָּדוֹל הָיָה, מֻקָּף רוֹבָדִין שֶׁל אֶבֶן, וְזִקְנֵי בֵית אָב יְשֵׁנִים שָׁם, וּמַפְתְּחוֹת הָעֲזָרָה בְּיָדָם.", "מידות א, ח"),
            "beit_hatevila": ("תחת העזרה, בסוף מסבה מוארת בנרות: כהן שנטמא בלילה טובל שם ומתחמם כנגד המדורה.", "תמיד א, א"),
            "beit_hanitzotz": ("עֲלִיָּה בְנוּיָה עַל גַּבָּיו, שֶׁהַכֹּהֲנִים שׁוֹמְרִים מִלְמַעְלָן וְהַלְוִיִּם מִלְּמַטָּן.", "מידות א, ה"),
            "lishkat_hagazit": ("שָׁם הָיְתָה סַנְהֶדְרִי גְדוֹלָה שֶׁל יִשְׂרָאֵל יוֹשֶׁבֶת.", "מידות ה, ד"),
            "lishkat_hagola": ("שָׁם הָיָה בוֹר קָבוּעַ, וְהַגַּלְגַּל נָתוּן עָלָיו, וּמִשָּׁם מַסְפִּיקִים מַיִם לְכָל הָעֲזָרָה.", "מידות ה, ד"),
            "lishkat_haetz": ("אָמַר רַבִּי אֱלִיעֶזֶר בֶּן יַעֲקֹב, שָׁכַחְתִּי מֶה הָיְתָה מְשַׁמֶּשֶׁת.", "מידות ה, ד"),
            "lishkat_hamelach": ("שָׁם הָיוּ נוֹתְנִים מֶלַח לַקָּרְבָּן.", "מידות ה, ג"),
            "lishkat_haparva": ("שָׁם הָיוּ מוֹלְחִין עוֹרוֹת קָדָשִׁים, וְעַל גַּגָּהּ הָיָה בֵית הַטְּבִילָה לְכֹהֵן גָּדוֹל בְּיוֹם הַכִּפּוּרִים.", "מידות ה, ג"),
            "lishkat_hamedichin": ("שֶׁשָּׁם הָיוּ מְדִיחִין קִרְבֵי הַקֳּדָשִׁים, וּמִשָּׁם מְסִבָּה עוֹלָה לְגַג בֵּית הַפַּרְוָה.", "מידות ה, ג"),
            "lishkat_parhedrin": ("שם שוהה הכהן הגדול שבעת ימים קודם יום הכיפורים.", "יומא א, א"),
            "beit_avtinas": ("שם מכינים בית אבטינס את הקטורת, ששמרו את סודה.", "תמיד א, א; יומא ג, יא"),
        },
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

FICHES = {code: json.loads((SITE.parent / "visite" / f"contenu_a{'' if code == 'fr' else '.' + code}.json").read_text(encoding="utf-8"))
          for code in TEXTES}

DEPOT = "https://github.com/davidbonan/beth-hamikdash-blender"
TAILLES = "100vw"

MARQUE_GITHUB = (
    '<svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor" aria-hidden="true">'
    '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94 '
    '-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07 '
    '-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 '
    '1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 '
    '0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>'
)


def lien_depot(t):
    return (f'<a class="depot" href="{DEPOT}" target="_blank" rel="noopener"'
            f' title="{t["nav_depot"]}" aria-label="{t["nav_depot"]}">{MARQUE_GITHUB}</a>')


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


def echelon(t, rang, degre):
    nom = t["degres"][degre][0]
    courant = ' aria-current="true"' if rang == 1 else ""
    return f'\n      <li data-degre="{degre}"><a href="#{degre}"{courant}><span class="rang">{rang}</span>{nom}</a></li>'


def image(t, degre, taille="2000", differe=True, decorative=False):
    nom = "" if decorative else t["degres"][degre][0]
    charge = ' loading="lazy"' if differe else ' fetchpriority="high"'
    return (f'<img src="/images/{degre}_{taille}.webp" srcset="/images/{degre}_1000.webp 1000w, /images/{degre}_2000.webp 2000w" '
            f'sizes="{TAILLES}" alt="{nom}" decoding="async"{charge}>')


def vue(t, rang, degre):
    return f'\n        <div class="vue" data-degre="{degre}" style="--fil: --{degre}">{image(t, degre, differe=rang > 1, decorative=True)}</div>'


def titre_degre(t, degre):
    nom, hebreu, _, _ = t["degres"][degre]
    titre = f'<span class="nom">{nom}</span>'
    if hebreu:
        titre += f' <span class="nom-he" lang="he" dir="rtl">{hebreu}</span>'
    return titre


def legende(t, degre, lien="", action=""):
    _, _, ref, phrase = t["degres"][degre]
    return f'''<div class="legende">
          <h3>{titre_degre(t, degre)}</h3>
          <div class="texte">
            <p class="mishna">{phrase}</p>
            <p class="source">{t["mishna"]} {ref}</p>{lien}
          </div>{action}
        </div>'''


def degre(t, degre, vue):
    lien = f'\n            <a class="entrer-ici" href="/visite/?vue={vue}" data-langue="{t["code"]}">{t["voir"]}</a>'
    return f'''
      <li id="{degre}" style="--fil: --{degre}">
        {legende(t, degre, lien)}
      </li>'''


def sanctuaire(t, degre, vue):
    action = (f'\n          <p class="action"><a class="entrer" href="/visite/?vue={vue}" data-langue="{t["code"]}">{t["entrer"]}</a></p>')
    fumee = "".join('<span class="fumee"></span>' for _ in range(3))
    volutes = ('<svg width="0" height="0" aria-hidden="true"><filter id="volutes" x="-20%" y="-20%" width="140%" height="140%">'
               '<feTurbulence type="fractalNoise" baseFrequency=".009" numOctaves="3" seed="7"/>'
               '<feDisplacementMap in="SourceGraphic" scale="160" xChannelSelector="R" yChannelSelector="G"/></filter></svg>')
    return f'''<section class="sanctuaire" id="{degre}" aria-labelledby="{degre}-titre">
    {volutes}
    <div class="fond">{image(t, degre)}{fumee}<span class="braise"></span><span class="reflet"></span></div>
    {legende(t, degre, action=action).replace("<h3>", f'<h3 id="{degre}-titre">', 1)}
  </section>'''


KAVANOT = {
    "amida": "צריך שיכוף ראשו מעט שיהיו עיניו למטה לארץ <mark>ויחשוב כאלו עומד בבית המקדש</mark> ובלבו יכוין למעלה לשמים",
    "makom_ehad": "היה עומד בחוץ לארץ יכוין את לבו כנגד ארץ ישראל… היה עומד בבית קדשי הקדשים יכוין את לבו כנגד בית הכפורת…<br><mark>נמצאו כל ישראל מכוונין את לבם למקום אחד</mark>",
}


def kavana(t, passage):
    traduction, source = t["kavanot"][passage]
    if traduction:
        traduction = f'\n      <p class="traduction">{traduction}</p>'
    return f'''<section class="kavana" aria-label="{source}">
    <p class="source"><cite>{source}</cite></p>
    <blockquote>
      <p class="he" lang="he" dir="rtl">{KAVANOT[passage]}</p>{traduction}
    </blockquote>
  </section>'''


def nom_chambre(t, chambre):
    hebreu = FICHES["fr"][chambre]["he"]
    if t["code"] == "he":
        return hebreu, ""
    fiche = FICHES[t["code"]][chambre]
    return fiche.get("nom", fiche.get("translit")), hebreu


def repere(t, rang, chambre, x, y):
    nom, _ = nom_chambre(t, chambre)
    souterraine = ' data-souterraine' if chambre in SOUTERRAINES else ""
    courant = ' aria-current="true"' if rang == 1 else ""
    return (f'\n        <a class="repere" href="#{chambre}" data-chambre="{chambre}" style="--x: {x}; --y: {y}"{souterraine}{courant}>'
            f'<span class="rang">{rang}</span><span class="nom">{nom}</span></a>')


def carte_chambre(t, rang, chambre):
    nom, hebreu = nom_chambre(t, chambre)
    role, source = t["chambres"][chambre]
    titre = f'<span class="nom">{nom}</span>'
    if hebreu:
        titre += f' <span class="nom-he" lang="he" dir="rtl">{hebreu}</span>'
    if chambre in SOUTERRAINES:
        titre += f' <span class="sous-terre">{t["sous_terre"]}</span>'
    return f'''
        <li id="{chambre}" data-chambre="{chambre}">
          <h3><span class="rang">{rang}</span>{titre}</h3>
          <p class="role">{role}</p>
          <p class="source">{source}</p>
          <a class="entrer-ici" href="/visite/?vue={chambre}" data-langue="{t["code"]}">{t["voir"]}</a>
        </li>'''


def lishkot(t):
    reperes = "".join(repere(t, rang, c, x, y) for rang, (c, x, y) in enumerate(CHAMBRES, 1))
    chambres = "".join(carte_chambre(t, rang, c) for rang, (c, _, _) in enumerate(CHAMBRES, 1))
    return f'''<section class="lishkot" aria-labelledby="lishkot-titre">
    <div class="plongee">
      <div class="cadre">
        <img src="/images/lishkot_2000.webp" srcset="/images/lishkot_1000.webp 1000w, /images/lishkot_2000.webp 2000w" sizes="(max-width: 860px) 170vw, (min-aspect-ratio: 16/9) 100vw, 180vh" alt="" decoding="async" loading="lazy">{reperes}
      </div>
      <div class="entete">
        <h2 id="lishkot-titre">{t["lishkot_titre"]}</h2>
        <p>{t["lishkot_ouverture"]}</p>
      </div>
      <ol class="chambres">{chambres}
      </ol>
    </div>
  </section>'''


def page(code):
    t = {**TEXTES[code], "code": code}
    url = f'{DOMAINE}/{t["chemin"]}'
    *montee, dernier = DEGRES
    echelle = "".join(echelon(t, rang, d) for rang, (d, _) in enumerate(DEGRES, 1))
    vues = "".join(vue(t, rang, d) for rang, (d, _) in enumerate(montee, 1))
    fils = ", ".join(f"--{d}" for d, _ in montee)
    degres = "".join(degre(t, d, v) for d, v in montee)
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
<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" as="image" href="/images/affiche_2000.webp" imagesrcset="/images/affiche_1000.webp 1000w, /images/affiche_2000.webp 2000w" imagesizes="100vw" media="(min-aspect-ratio: 4/5)">
<link rel="preload" as="image" href="/images/affiche_portrait_720.webp" media="(max-aspect-ratio: 4/5)">

<main>
  <header class="seuil">
    <picture class="affiche">
      <source media="(max-aspect-ratio: 4/5)" srcset="/images/affiche_portrait_720.webp">
      <img src="/images/affiche_2000.webp" srcset="/images/affiche_1000.webp 1000w, /images/affiche_2000.webp 2000w" sizes="100vw" alt="" fetchpriority="high">
    </picture>
    <div class="barre">
      <nav aria-label="{t["nav_langue"]}">
        {nav_langues(code)}
      </nav>
      {lien_depot(t)}
    </div>
    <div class="titre">
      <h1><span class="he" lang="he" dir="rtl">{t["hebreu"]}</span><span class="latin" lang="fr">{t["latin"]}</span></h1>
      <p class="accroche">{t["accroche"]}</p>
      <p class="action"><a class="entrer" href="/visite/" data-langue="{code}">{t["entrer"]}</a><span class="note">{t["entrer_note"]}</span></p>
    </div>
  </header>

  {kavana(t, "amida")}

  {lishkot(t)}

  <section class="montee" aria-labelledby="montee-titre">
    <div class="ouverture">
      <h2 id="montee-titre">{t["degres_titre"]}</h2>
      <p>{t["ouverture"]}</p>
    </div>
    <div class="ascension" style="timeline-scope: {fils}; --fin: --{montee[-1][0]}">
      <div class="scene">{vues}
        <span class="nuit-tombe"></span>
        <nav class="echelle" aria-label="{t["degres_titre"]}"><ol>{echelle}
        </ol></nav>
      </div>
      <ol class="degres">{degres}
      </ol>
    </div>
  </section>

  {kavana(t, "makom_ehad")}

  {sanctuaire(t, *dernier)}
</main>

<script src="/accueil.js" defer></script>
<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "5fc9072e758d4623b321af15c740227c"}}'></script>
</html>
'''


for code, t in TEXTES.items():
    cible = SITE / t["chemin"] / "index.html"
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(page(code), encoding="utf-8")
    print(cible.relative_to(SITE.parent))
