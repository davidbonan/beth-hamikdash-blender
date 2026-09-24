#!/bin/sh
# memoire.sh — empreinte (celle que jetsam juge sur iPhone) des processus WebKit du simulateur démarré.
# WebContent porte le JavaScript et la page, GPU porte les textures et les tampons WebGL.
for pid in $(pgrep -f "SimulatorRuntime.*com.apple.WebKit.(WebContent|GPU)"); do
  nom=$(ps -o command= -p "$pid" | sed -E 's#.*/(com\.apple\.WebKit\.[A-Za-z]+).*#\1#')
  empreinte=$(footprint "$pid" 2>/dev/null | sed -nE 's/.*Footprint: ([0-9.]+ [KMG]B).*/\1/p')
  echo "$pid $nom $empreinte"
done
