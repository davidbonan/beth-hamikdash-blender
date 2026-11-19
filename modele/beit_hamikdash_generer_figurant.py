"""python3 modele/beit_hamikdash_generer_figurant.py <sorte>_<k> <âge MakeHuman> "<qui, sa tenue>" [--depuis <variante>] [--modele-seul]

Écrit modele/figurants/generes/<sorte>_<k>.png, .glb et .json : le portrait (Nano Banana Pro) puis son volume (Rodin 2.5,
20 000 triangles) sur fal.ai, environ 0,55 $. `--depuis` repart du portrait d'une autre variante, pour le même visage sous
une autre tenue.
"""
import json
import pathlib
import sys

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent / ".claude" / "skills" / "fal-video"))
import fal_commun as F  # noqa: E402

DOSSIER = ICI / "figurants" / "generes"
# Les bras écartés du corps : collés, Rodin les soude à la robe et la ceinture suit le coude.
CADRE = ("Full-body character reference photograph, standing straight in a strict A-pose: both arms held straight out and down "
         "at 40 degrees from the body, well clear of the torso and of any sash or mantle, palms facing down, fingers together, "
         "legs slightly apart, front view, barefoot. {qui} Plain light grey seamless studio background, soft even lighting, "
         "photorealistic, sharp focus, whole body visible from head to feet.")
DEPUIS = ("Same person, same face, same A-pose, same framing and background. Change only the clothing: {qui}")
RODIN = {"TAPose": True, "geometry_file_format": "glb", "material": "PBR", "quality_mesh_option": "20K Triangle",
         "tier": "Gen-2.5-Medium", "texture_delight": True}


def portrait(qui, depuis, cle):
    image = {"aspect_ratio": "3:4", "num_images": 1, "output_format": "png"}
    if depuis:
        source = json.loads((DOSSIER / f"{depuis}.json").read_text())["portrait"]
        prompt = DEPUIS.format(qui=qui)
        r = F.genere("fal-ai/nano-banana-pro/edit", {"prompt": prompt, "image_urls": [source], **image}, cle)
    else:
        prompt = CADRE.format(qui=qui)
        r = F.genere("fal-ai/nano-banana-pro", {"prompt": prompt, **image}, cle)
    return prompt, r["images"][0]["url"]


def main():
    variante, age, qui, *options = sys.argv[1:]
    DOSSIER.mkdir(exist_ok=True)
    cle = F.cle_api()
    trace = DOSSIER / f"{variante}.json"
    if "--modele-seul" in options:
        provenance = json.loads(trace.read_text())
    else:
        depuis = options[options.index("--depuis") + 1] if "--depuis" in options else None
        prompt, url = portrait(qui, depuis, cle)
        provenance = {"age": float(age), "prompt": prompt, "portrait": url}
        F.telecharge(url, str(DOSSIER / f"{variante}.png"))
        trace.write_text(json.dumps(provenance, ensure_ascii=False, indent=1))
    r = F.genere("fal-ai/hyper3d/rodin/v2.5", {"image_urls": [provenance["portrait"]], **RODIN}, cle)
    provenance.update(rodin=RODIN, modele=r["model_mesh"]["url"])
    F.telecharge(provenance["modele"], str(DOSSIER / f"{variante}.glb"))
    trace.write_text(json.dumps(provenance, ensure_ascii=False, indent=1))
    print(f"{variante} : {DOSSIER / f'{variante}.glb'}")


if __name__ == "__main__":
    main()
