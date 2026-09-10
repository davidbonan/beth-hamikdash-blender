"""Fabrique les nappes de `visite/matieres/` à partir des scans d'origine.

    python3 beit_hamikdash_nappes.py

Cinq jeux, tous CC0 : quatre de Poly Haven, un d'ambientCG. Deux fichiers par jeu.
La COULEUR porte la rugosité dans son canal alpha — l'alpha du WebP est codé à part et
à pleine définition, là où le bleu partirait en 4:2:0 avec le reste de la chrominance.
La NORMALE est en convention OpenGL, vert vers le haut, celle qu'attend three.

Le script imprime aussi la moyenne LINÉAIRE de chaque couleur et sa rugosité moyenne :
ce sont les constantes de `visite/nappes.js`, et la nappe est appliquée en rapport à
elles. Les recopier là-bas après avoir changé un scan, sinon la teinte dérive.

Demande `ffmpeg` et `cwebp` sur le PATH.
"""
import json
import pathlib
import subprocess
import urllib.request

RACINE = pathlib.Path(__file__).resolve().parent
SORTIE = RACINE / "visite" / "matieres"
BRUT = SORTIE / ".scans"
TAILLE = 1024

# Le calcaire est le meleke de Jérusalem : crème, piqué, sans veine. Les travertins
# sciés, eux, se lisent en carrelage de salle de bain, et les roches de falaise en
# lichen. L'étoffe n'a pas de couleur : celle du lin et du tekhelet est dictée.
POLY_HAVEN = {"pierre": "worn_rock_natural_01", "enduit": "beige_wall_001",
              "bois": "hinoki_planks", "etoffe": "rough_linen"}
AMBIENT_CG = {"metal": "Metal007"}
SANS_COULEUR = ("etoffe",)


def tirer(url, dest):
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    requete = urllib.request.Request(url, headers={"User-Agent": "beit-hamikdash/1.0"})
    with urllib.request.urlopen(requete) as flux:
        dest.write_bytes(flux.read())
    return dest


def scans_poly_haven():
    for nom, ident in POLY_HAVEN.items():
        fiche = json.loads(tirer(f"https://api.polyhaven.com/files/{ident}",
                                 BRUT / f"{ident}.json").read_text())
        for carte, suffixe in (("Diffuse", "couleur"), ("nor_gl", "normale"), ("Rough", "rugosite")):
            tirer(fiche[carte]["1k"]["jpg"]["url"], BRUT / f"{nom}_{suffixe}.jpg")


def scans_ambient_cg():
    for nom, ident in AMBIENT_CG.items():
        archive = tirer(f"https://ambientcg.com/get?file={ident}_1K-JPG.zip", BRUT / f"{ident}.zip")
        subprocess.run(["unzip", "-o", "-q", str(archive), "-d", str(BRUT / ident)], check=True)
        for carte, suffixe in (("Color", "couleur"), ("NormalGL", "normale"), ("Roughness", "rugosite")):
            (BRUT / f"{nom}_{suffixe}.jpg").write_bytes(
                (BRUT / ident / f"{ident}_1K-JPG_{carte}.jpg").read_bytes())


def ffmpeg(*arguments):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *arguments], check=True)


def moyenne(png):
    """Moyenne linéaire des trois canaux, et moyenne de l'alpha.

    En linéaire et pas en sRGB : c'est en linéaire que le nuanceur divise, et la
    différence entre les deux se lit en écart de clarté sur toute la pierre.
    """
    brut = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-f", "rawvideo",
                           "-pix_fmt", "rgba", "-"], capture_output=True, check=True).stdout
    table = [c / 12.92 if (c := i / 255) <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
             for i in range(256)]
    points = len(brut) // 4

    def canal(rang, echelle):
        return sum(echelle[brut[i]] for i in range(rang, len(brut), 4)) / points

    return ([canal(k, table) for k in range(3)], canal(3, range(256)) / 255)


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    scans_poly_haven()
    scans_ambient_cg()

    print("  À recopier dans visite/nappes.js :")
    for nom in (*POLY_HAVEN, *AMBIENT_CG):
        normale = BRUT / f"{nom}_normale_{TAILLE}.png"
        ffmpeg("-i", str(BRUT / f"{nom}_normale.jpg"), "-vf", f"scale={TAILLE}:{TAILLE}",
               "-frames:v", "1", str(normale))
        subprocess.run(["cwebp", "-quiet", "-q", "88", "-m", "6", "-sharp_yuv",
                        str(normale), "-o", str(SORTIE / f"{nom}_n_{TAILLE}.webp")], check=True)
        if nom in SANS_COULEUR:
            continue
        couleur = BRUT / f"{nom}_couleur_{TAILLE}.png"
        ffmpeg("-i", str(BRUT / f"{nom}_couleur.jpg"), "-i", str(BRUT / f"{nom}_rugosite.jpg"),
               "-filter_complex",
               f"[0:v]scale={TAILLE}:{TAILLE},format=rgb24[c];"
               f"[1:v]scale={TAILLE}:{TAILLE},format=gray[r];[c][r]alphamerge",
               "-frames:v", "1", str(couleur))
        subprocess.run(["cwebp", "-quiet", "-q", "82", "-alpha_q", "72", "-m", "6",
                        "-sharp_yuv", str(couleur),
                        "-o", str(SORTIE / f"{nom}_c_{TAILLE}.webp")], check=True)
        teinte, rugosite = moyenne(couleur)
        print(f"  {nom}: {{ moyenne: [{teinte[0]:.4f}, {teinte[1]:.4f}, "
              f"{teinte[2]:.4f}], rugosite: {rugosite:.4f} }},")

    octets = sum(f.stat().st_size for f in SORTIE.glob(f"*_{TAILLE}.webp"))
    print(f"\n  {TAILLE} : {octets / 1e6:.2f} Mo")


main()
