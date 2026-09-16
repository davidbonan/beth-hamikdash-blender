// Cartes de beit_hamikdash_occlusion.py ; en aoMap, elles n'assombrissent que la lumière sans direction.
import * as THREE from "three";

export async function cartesOcclusion(cartes) {
  const chargeur = new THREE.TextureLoader();
  return new Map(await Promise.all(Object.entries(cartes).map(async ([concept, { carte, canal }]) => {
    const texture = await chargeur.loadAsync(carte);
    texture.flipY = false;
    texture.channel = canal;
    texture.colorSpace = THREE.NoColorSpace;
    return [concept, texture];
  })));
}
