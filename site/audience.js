if (location.hostname === "bethhamikdach.com") {
  const balise = document.createElement("script");
  balise.src = "https://static.cloudflareinsights.com/beacon.min.js";
  balise.defer = true;
  balise.dataset.cfBeacon = JSON.stringify({ token: "5fc9072e758d4623b321af15c740227c" });
  document.head.append(balise);
}
