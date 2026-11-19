// Cartes de beit_hamikdash_occlusion.py : l'occlusion en aoMap n'assombrit que la lumière sans direction ; la lumière cuite la remplace.
import * as THREE from "three";
import { PROFIL, plafonner } from "./qualite.js";

const chargeur = new THREE.ImageBitmapLoader()
  .setOptions({ imageOrientation: "none", premultiplyAlpha: "none", colorSpaceConversion: "none" });

const envoyees = [];

async function charger(texture, carte) {
  texture.image = await chargeur.loadAsync(carte);
  await plafonner(texture, PROFIL.textures.decor);
  texture.needsUpdate = true;
}

async function texture({ carte, canal }, format, colorSpace) {
  const texture = new THREE.Texture();
  texture.format = format;
  texture.flipY = false;
  texture.channel = canal;
  texture.colorSpace = colorSpace;
  await charger(texture, carte);
  texture.onUpdate = () => texture.image.close();
  envoyees.push({ texture, carte });
  return texture;
}

// Une image relâchée ne se renvoie pas : un contexte rendu par le navigateur recevait des cartes noires.
export function rechargerCartes() {
  return Promise.all(envoyees.map(({ texture, carte }) => charger(texture, carte)));
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
