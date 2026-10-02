from .figures_tamid import _shomer_levi, roles_du_tamid


# La visite libre : un lieu, un geste — la zerika à l'autel, deux Léviim qui jouent, un Israélite, la garde de Nikanor.
FIGURES_DE_LA_VISITE = ("zerika", "leviim_6", "leviim_7", "anshei_maamad_1")


def roles_de_la_visite():
    return [r for r in roles_du_tamid() if r.nom in FIGURES_DE_LA_VISITE] + [_shomer_levi()]
