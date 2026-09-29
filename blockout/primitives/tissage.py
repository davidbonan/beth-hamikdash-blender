import bpy
import json
import math

from .parametres import RACINE, Z_BAT, m
from .noeuds import _bsdf, _calc, _creuser, _grain, _neuf, _noeud, _position


# Les quatre matières de la parokhet (Shekalim 8:5 ; Rashi Ex. 26:31) — tekhelet,
# argaman, tola'at shani, lin, et aucun fil d'or (Ex. 26:31) —, les FACES du tissage
# qui les dosent et la palette qui en sort, tels que beit_hamikdash_parokhet.py les
# écrit dans parokhet.json : c'est lui la source, la carte tissée en dépend.
PAROKHET_JSON = RACINE / "visite" / "matieres" / "parokhet.json"
CARTE_PAROKHET = PAROKHET_JSON.with_name("parokhet_2048.webp")

def _lire_parokhet():
    try:
        return json.loads(PAROKHET_JSON.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"{PAROKHET_JSON.name} absent : lancer beit_hamikdash_parokhet.py d'abord.")

_PAROKHET = _lire_parokhet()
MATIERES_PAROKHET = tuple(tuple(rgb) for _, rgb in _PAROKHET["laines"])
DOSAGES_PAROKHET = {face: tuple(parts) for face, parts in _PAROKHET["dosages"].items()}
JOUR_PAROKHET = _PAROKHET["jour"]
PALETTE_PAROKHET = {face: tuple(rgb) for face, rgb in _PAROKHET["palette"].items()}
NIMA = 20 / 72   # amot : les 72 נִימִין de Shekalim 8:5 réparties sur les 20 amot de large
# La moyenne des quatre matières, et de combien un cordon s'en écarte. Les quatre teintes
# pures, tirées cordon par cordon, rendaient une neige de télévision : à dix amot un
# cordon fait un pixel, et quatre couleurs saturées tirées au sort par pixel ne se
# fondent pas, elles crépitent. Un fil de 24 brins qui contient les quatre EST de la
# couleur moyenne — ce qui change d'un fil à l'autre n'est que le dosage.
ECART_PAROKHET = 0.12
LONGUEUR_DOSAGE = 12   # en nimin : sur quelle longueur le dosage d'un cordon dérive
# Les FACES du tissage — « אֲרִיגָה שֶׁל שְׁתֵּי קִירוֹת » (Rashi Ex. 26:31) : deux parois de fils
# dont l'une passe devant l'autre là où le dessin le veut. Chaque cordon porte les quatre
# laines ; ce qui change d'une face à l'autre est celle qui AFFLEURE : quatre dosages
# aux coins d'un carré (clarté, rougeur) que la carte parcourt. Moyenner les quatre à
# parts égales rendait un mauve uni, où la figure ne se lisait qu'au ton.
# La carte — créatures ailées et lions — : R porte la hauteur du bombé, G la clarté de
# la face, B sa rougeur, l'alpha le masque de la figure. Lue par (y, z) de monde sur les
# 20 × 40 amot du rideau ; mêmes lectures et même palette dans visite/matieres.js.
BOMBE_PAROKHET = 0.12      # amot : ce dont une figure TISSÉE bombe l'étoffe, 6 cm — pas un relief
GRAIN_PAROKHET = (0.84, 0.82, 0.86)   # le jour d'une étoffe : un champ d'un ton parfaitement égal se lit peint

def _carte_parokhet(mat):
    """(hauteur du bombé, clarté, rougeur, masque de la figure) au point ombré, lus dans
    CARTE_PAROKHET."""
    liens = mat.node_tree.links
    axe = _noeud(mat, "ShaderNodeSeparateXYZ", -1700, 900)
    liens.new(_position(mat), axe.inputs["Vector"])
    uv = _noeud(mat, "ShaderNodeCombineXYZ", -1400, 900)
    liens.new(_calc(mat, "DIVIDE", _calc(mat, "ADD", axe.outputs["Y"], m(10)), m(20)), uv.inputs["X"])
    liens.new(_calc(mat, "DIVIDE", _calc(mat, "SUBTRACT", axe.outputs["Z"], m(Z_BAT)), m(40)), uv.inputs["Y"])
    carte = _noeud(mat, "ShaderNodeTexImage", -1200, 900)
    carte.image = bpy.data.images.load(str(CARTE_PAROKHET), check_existing=True)
    carte.image.colorspace_settings.name = "Non-Color"
    carte.image.alpha_mode = "CHANNEL_PACKED"
    carte.extension = "EXTEND"
    liens.new(uv.outputs["Vector"], carte.inputs["Vector"])
    canaux = _noeud(mat, "ShaderNodeSeparateColor", -1000, 900)
    liens.new(carte.outputs["Color"], canaux.inputs["Color"])
    return canaux.outputs["Red"], canaux.outputs["Green"], canaux.outputs["Blue"], carte.outputs["Alpha"]

def _melange(mat, facteur, couleur1, couleur2, x, y):
    """Un MixRGB dont chaque entrée est une couleur ou une sortie de nœud, comme `_calc`."""
    noeud = _noeud(mat, "ShaderNodeMixRGB", x, y)
    for entree, valeur in (("Fac", facteur), ("Color1", couleur1), ("Color2", couleur2)):
        if isinstance(valeur, tuple):
            noeud.inputs[entree].default_value = (*valeur, 1.0) if len(valeur) == 3 else valeur
        elif isinstance(valeur, (int, float)):
            noeud.inputs[entree].default_value = valeur
        else:
            mat.node_tree.links.new(valeur, noeud.inputs[entree])
    return noeud.outputs["Color"]

def _laine_tiree(mat, face, tirage, y):
    """La laine d'un cordon, tirée dans les parts de DOSAGES_PAROKHET[face] : une rampe
    en paliers dont chaque palier commence au dosage cumulé des laines qui le précèdent."""
    rampe = _noeud(mat, "ShaderNodeValToRGB", -1000, y)
    rampe.color_ramp.interpolation = 'CONSTANT'
    paliers = [(sum(DOSAGES_PAROKHET[face][:i]), MATIERES_PAROKHET[i])
               for i, part in enumerate(DOSAGES_PAROKHET[face]) if part > 0]
    rampe.color_ramp.elements.remove(rampe.color_ramp.elements[1])
    for k, (position, couleur) in enumerate(paliers):
        element = rampe.color_ramp.elements[0] if k == 0 else rampe.color_ramp.elements.new(position)
        element.position = position
        element.color = (*(JOUR_PAROKHET * c for c in couleur), 1.0)
    mat.node_tree.links.new(tirage, rampe.inputs["Factor"])
    return rampe.outputs["Color"]

def parokhet(name):
    """Étoffe chinée des quatre matières, et non quatre bandes de couleur.

    « וְעַל שִׁבְעִים וּשְׁתַּיִם נִימִין נֶאֱרֶגֶת, וְעַל כָּל נִימָא וְנִימָא עֶשְׂרִים וְאַרְבָּעָה חוּטִין »
    (Shekalim 8:5), et Rashi Ex. 26:31 : « כָּל מִין וָמִין הָיָה כָפוּל בְּכָל חוּט וָחוּט שִׁשָּׁה
    חוּטִין ». Les quatre matières — trois laines et le lin — sont retordues DANS chaque fil : le champ est un pourpre
    changeant où les quatre teintes se lisent de près, pas un drapeau à quatre bandes —
    huit champs de cinq amot rendaient un pavillon national en travers du Devir.

    Un tirage uniforme par cordon, lu sur une rampe dont les paliers sont le dosage
    cumulé de la face, donne les laines dans les parts de cette face ; une rampe posée
    sur un bruit les aurait pondérées par la loi du bruit, et un tirage à parts égales
    semait des cordons de lin pur sur le champ violet, qui crépitaient en neige. Le
    cordon des nimin, large de 20/72 d'ama, donne au tissu son corps.

    Là où la carte de beit_hamikdash_parokhet.py dit une figure, le cordon se couche
    et une autre face affleure : c'est la seconde paroi d'un maassé 'hoshev, « אֲרִיגָה
    שֶׁל שְׁתֵּי קִירוֹת » (Rashi, ibid.), les mêmes laines dosées autrement (PALETTE_PAROKHET).
    C'est ce qui fait voir un lion de lin à crinière écarlate sur le champ violet sans y
    mettre un fil d'or, qu'Ex. 26:31 ne donne pas — et sans un volume : la figure bombe
    l'étoffe de BOMBE_PAROKHET, elle n'y est pas posée.
    """
    mat, neuf = _neuf(name, PALETTE_PAROKHET["fond"])
    if not neuf:
        return mat
    liens = mat.node_tree.links
    bsdf = _bsdf(mat)
    bsdf.inputs["Roughness"].default_value = 0.90
    bsdf.inputs["Sheen Weight"].default_value = 0.50
    bsdf.inputs["Sheen Roughness"].default_value = 0.45
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    bombe, clarte, rougeur, figure = _carte_parokhet(mat)
    axe = _noeud(mat, "ShaderNodeSeparateXYZ", -1700, 0)
    liens.new(_position(mat), axe.inputs["Vector"])
    chaine, trame = axe.outputs["Y"], axe.outputs["Z"]
    cellule = _noeud(mat, "ShaderNodeCombineXYZ", -1400, 0)
    liens.new(_calc(mat, "FLOOR", _calc(mat, "DIVIDE", chaine, m(NIMA))), cellule.inputs["X"])
    liens.new(_calc(mat, "FLOOR", _calc(mat, "DIVIDE", trame, m(NIMA * LONGUEUR_DOSAGE))),
              cellule.inputs["Y"])
    tirage = _noeud(mat, "ShaderNodeTexWhiteNoise", -1200, 0)
    tirage.noise_dimensions = '2D'
    liens.new(cellule.outputs["Vector"], tirage.inputs["Vector"])
    laine = _melange(mat, clarte, _laine_tiree(mat, "fond", tirage.outputs["Value"], 0),
                     _laine_tiree(mat, "clair", tirage.outputs["Value"], -200), -840, 0)
    # La face qui affleure, aux coins du carré (clarté, rougeur) que la carte parcourt.
    palette = PALETTE_PAROKHET
    sombre = _melange(mat, rougeur, palette["fond"], palette["chaud"], -1000, 600)
    clair = _melange(mat, rougeur, palette["clair"], palette["clair_chaud"], -1000, 400)
    face = _melange(mat, clarte, sombre, clair, -840, 500)
    dosage = _melange(mat, ECART_PAROKHET, face, laine, -700, 200)
    jour = _noeud(mat, "ShaderNodeMixRGB", -500, 0)
    jour.blend_type = 'MULTIPLY'
    jour.inputs["Color2"].default_value = (*GRAIN_PAROKHET, 1.0)
    liens.new(dosage, jour.inputs["Color1"])
    liens.new(_grain(mat, 2.5), jour.inputs["Factor"])
    liens.new(jour.outputs["Color"], bsdf.inputs["Base Color"])
    # Le cordon de la chaîne domine le fond, celui de la trame domine la figure : le
    # fil s'y couche dans l'autre sens.
    for k, (sens, largeur, force_fond, force_figure, creux) in enumerate((
            (chaine, NIMA, 0.6, 0.4, NIMA * 0.18), (trame, NIMA / 3, 0.4, 0.6, NIMA * 0.07))):
        cordon = _noeud(mat, "ShaderNodeMath", -900, -500 - 200 * k)
        cordon.operation = "SINE"
        liens.new(_calc(mat, "MULTIPLY", sens, 2 * math.pi / m(largeur)), cordon.inputs[0])
        _creuser(mat, cordon.outputs[0],
                 _calc(mat, "MULTIPLY_ADD", figure, force_figure - force_fond, force_fond), creux)
    _creuser(mat, bombe, 1.0, BOMBE_PAROKHET)
    _creuser(mat, _grain(mat, 0.05), 0.4, 0.008)
    return mat
