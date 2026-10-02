import math

from ..primitives.volumes import alea
from ..har_habayit import HX1
from .calage import PAYS, _nappe_du_pays
from .herode import esplanade_herode, murs_herode
from .place_du_kotel import place_du_kotel
from .ville import _cases_baties, murailles, olivier, ville


_nappe_du_pays()
esplanade_herode()
murs_herode()
place_du_kotel()
murailles()
CASES_BATIES = _cases_baties(ville())
# Les oliviers du mont des Oliviers et de la pente du Kidron, là où rien n'est bâti.
for i in range(1300):
    nom = f"Olivier_{i:04d}"
    x, y = HX1 + 120 + 3000 * alea(nom, 5), -2400 + 4800 * alea(nom, 6)
    if alea(nom, 0) > 0.7 or (math.floor(x / 10), math.floor(y / 10)) in CASES_BATIES:
        continue
    olivier(nom, x, y, PAYS)
