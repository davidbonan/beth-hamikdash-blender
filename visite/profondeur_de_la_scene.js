// La distance à l'œil de ce que la scène a tracé, relue dans sa profondeur par les passes d'écran que la géométrie arrête.
export const PROFONDEUR_DE_LA_SCENE = { tProfondeur: { value: null }, uProche: { value: 0 }, uLoin: { value: 0 } };

export const DISTANCE_LUE = /* glsl */`
    uniform sampler2D tProfondeur;
    uniform float uProche, uLoin;
    // En mètres ; nulle sur le ciel, qui n'écrit pas sa profondeur.
    float distanceLue(vec2 uv){
      float profondeur = texture2D(tProfondeur, uv).x;
      return profondeur >= 1.0 ? 0.0 : uProche * uLoin / (uLoin - profondeur * (uLoin - uProche));
    }`;
