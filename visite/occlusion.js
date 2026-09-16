// Cartes de beit_hamikdash_occlusion.py ; en aoMap, elles n'assombrissent que la lumière sans direction.
import * as THREE from "three";

// aoMap ne lit que le rouge : un seul canal, et l'image relâchée une fois envoyée au GPU.
export async function cartesOcclusion(cartes) {
  const chargeur = new THREE.ImageBitmapLoader()
    .setOptions({ imageOrientation: "none", premultiplyAlpha: "none", colorSpaceConversion: "none" });
  return new Map(await Promise.all(Object.entries(cartes).map(async ([concept, { carte, canal }]) => {
    const image = await chargeur.loadAsync(carte);
    const texture = new THREE.Texture(image);
    texture.format = THREE.RedFormat;
    texture.flipY = false;
    texture.channel = canal;
    texture.colorSpace = THREE.NoColorSpace;
    texture.onUpdate = () => image.close();
    texture.needsUpdate = true;
    return [concept, texture];
  })));
}
