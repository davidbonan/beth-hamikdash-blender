// Cartes de beit_hamikdash_occlusion.py : l'occlusion en aoMap n'assombrit que la lumière sans direction ; la lumière cuite la remplace.
import * as THREE from "three";
import { PROFIL, plafonner } from "./qualite.js";

const chargeur = new THREE.ImageBitmapLoader()
  .setOptions({ imageOrientation: "none", premultiplyAlpha: "none", colorSpaceConversion: "none" });

async function texture({ carte, canal }, format, colorSpace) {
  const image = await chargeur.loadAsync(carte);
  const texture = new THREE.Texture(image);
  texture.format = format;
  texture.flipY = false;
  texture.channel = canal;
  texture.colorSpace = colorSpace;
  await plafonner(texture, PROFIL.textures.decor);
  texture.onUpdate = () => texture.image.close();
  texture.needsUpdate = true;
  return texture;
}

// aoMap ne lit que le rouge : un seul canal, et l'image relâchée une fois envoyée au GPU.
export async function cartesOcclusion(cartes) {
  return new Map(await Promise.all(Object.entries(cartes).map(async ([concept, carte]) =>
    [concept, await texture(carte, THREE.RedFormat, THREE.NoColorSpace)])));
}

// L'irradiance, divisée par son échelle et encodée en sRGB pour tenir les ombres sur huit bits.
export async function cartesLumiere(cartes) {
  return new Map(await Promise.all(Object.entries(cartes).map(async ([concept, carte]) =>
    [concept, { texture: await texture(carte, THREE.RGBAFormat, THREE.SRGBColorSpace), echelle: carte.echelle }])));
}
