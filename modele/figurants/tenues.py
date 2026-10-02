from .matieres import DRAP_NOIR, LIN, feutre, laine, lin, velours
from .corps import Gabarit, Humain
from .maillage import Maillage
from .habillage import (COSTUME, KUTONET, ROBE, TALITH_TISSU, Tissu, _poils, appliquer_visibilite, calotte,
                        chapeau, empiecement, lier, talith, tzitzit)


# « מְלֻבָּשִׁים בּוּץ » (Divrei HaYamim II 5:12).
def levi(nom, gabarit=Gabarit(), gris=False, barbe=True):
    poils = _poils(nom, gris)
    if not barbe:
        poils["barbe"] = None
    h = Humain(nom, gabarit, **poils)
    robe = h.vetir_mpfb(KUTONET)
    h.detendre()
    empiecement(h, robe)
    coiffure = Maillage()
    calotte(coiffure, h, LIN, rayon=0.066)
    lier(h, coiffure, f"{nom}_kippa", lin(), "head")
    appliquer_visibilite(h, h.visible & ~h.efface)
    return h


# Pieds nus : « לֹא יִכָּנֵס לְהַר הַבַּיִת בְּמַקְלוֹ וּבְמִנְעָלוֹ » (Berakhot 9:5).
def fidele(nom, tenue, gabarit=Gabarit(), gris=False, barbe=True, tete="kippa"):
    poils = _poils(nom, gris)
    if not barbe:
        poils["barbe"] = None
    h = Humain(nom, gabarit, **poils)
    h.vetir_mpfb({"costume": COSTUME, "robe": ROBE}[tenue])
    h.detendre()
    if tete == "chapeau":
        coiffure = Maillage()
        chapeau(coiffure, h)
        lier(h, coiffure, f"{nom}_chapeau", feutre(), "head")
    if tete == "talith":
        draper_talith(h)
    if tete in ("kippa", "talith"):
        coiffure = Maillage()
        calotte(coiffure, h, DRAP_NOIR)
        lier(h, coiffure, f"{nom}_kippa", velours(), "head")
    appliquer_visibilite(h, h.visible & ~h.efface)
    h.ranger()
    return h


def draper_talith(humain):
    h = humain
    drap = Maillage()
    coins = talith(drap, h)
    haut = h.obstacle("haut", h.visible, h.vetements_mpfb)
    objet = lier(h, drap, f"{h.nom}_talith", laine(), tissu=Tissu(haut, **TALITH_TISSU))
    franges = Maillage()
    tzitzit(franges, [objet.data.vertices[i].co.copy() for i in coins])
    lier(h, franges, f"{h.nom}_tzitzit", laine())
