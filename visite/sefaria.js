// Sefaria distingue la michna du folio : `Middot 2:1` est une michna, `Yoma 54a` un
// folio de guemara. Le nom du traité est le même, le préfixe non — d'où le test sur
// la forme de la cote plutôt qu'une table à double entrée.
const TRAITES = {
  middot: "Middot", tamid: "Tamid", yoma: "Yoma", shekalim: "Shekalim",
  soucca: "Sukkah", souccah: "Sukkah", sukkah: "Sukkah", succa: "Sukkah",
  kelim: "Kelim", arakhin: "Arakhin", erakhin: "Arakhin", taanit: "Taanit",
  zevahim: "Zevachim", zevachim: "Zevachim",
  menahot: "Menachot", menachot: "Menachot",
  "baba batra": "Bava Batra", "bava batra": "Bava Batra",
  houlin: "Chullin", chullin: "Chullin", horayot: "Horayot",
  sanhedrin: "Sanhedrin", negaim: "Negaim", ketoubot: "Ketubot", ketubot: "Ketubot", meila: "Meilah", meilah: "Meilah", keritot: "Keritot",
  pesachim: "Pesachim", pesahim: "Pesachim", "pessahim": "Pesachim",
};
const OUVRAGES = {
  "rambam beit habehira": "Mishneh Torah, The Chosen Temple",
  "beit habehira": "Mishneh Torah, The Chosen Temple",
  "rambam klei hamikdash": "Mishneh Torah, Vessels of the Sanctuary and Those Who Serve Therein",
  "rambam biat hamikdash": "Mishneh Torah, Admission into the Sanctuary",
  "melakhim i": "I Kings", "i rois": "I Kings", "rois i": "I Kings", "i melakhim": "I Kings",
  "divrei hayamim ii": "II Chronicles", "ii chroniques": "II Chronicles",
  yechezkel: "Ezekiel", ezechiel: "Ezekiel",
  shemot: "Exodus", exode: "Exodus",
  vayikra: "Leviticus", levitique: "Leviticus",
  devarim: "Deuteronomy", deuteronome: "Deuteronomy",
  bamidbar: "Numbers", nombres: "Numbers",
  "i samuel": "I Samuel", "shmuel i": "I Samuel",
  yirmeyahou: "Jeremiah", jeremie: "Jeremiah",
  yehezkel: "Ezekiel",
  "rambam temidin": "Mishneh Torah, Daily Offerings and Additional Offerings",
  "rambam tefila": "Mishneh Torah, Prayer and the Priestly Blessing",
  "rashi exode": "Rashi on Exodus", "rashi shemot": "Rashi on Exodus",
  "rashi sur yoma": "Rashi on Yoma",
  "rashi sur pesachim": "Rashi on Pesachim",
  "rashi sur zevahim": "Rashi on Zevachim",
  "rashi sur soucca": "Rashi on Sukkah",
  "rosh sur tamid": "Commentary of the Rosh on Tamid",
  "rambam sur middot": "Rambam on Mishnah Middot",
  "bartenura sur middot": "Bartenura on Mishnah Middot",
  "bartenura sur soucca": "Bartenura on Mishnah Sukkah",
  "divrei hayamim i": "I Chronicles",
  "yerushalmi soucca": "Jerusalem Talmud Sukkah",
  "rambam maasse hakorbanot": "Mishneh Torah, Sacrificial Procedure",
  "rambam sanhedrin": "Mishneh Torah, The Sanhedrin and the Penalties within Their Jurisdiction",
  "rambam arakhin": "Mishneh Torah, Appraisals and Devoted Property",
  "rambam matnot aniyim": "Mishneh Torah, Gifts to the Poor",
  "rashi sur sanhedrin": "Rashi on Sanhedrin",
  "sifrei devarim": "Sifrei Devarim",
  "hagahot yaavetz sur sanhedrin": "Haggahot Ya'avetz on Sanhedrin",
  "rambam mikvaot": "Mishneh Torah, Immersion Pools",
  "rambam avodat yom hakippurim": "Mishneh Torah, Service on the Day of Atonement",
  "yerushalmi yoma": "Jerusalem Talmud Yoma",
  "tosefta sanhedrin": "Tosefta Sanhedrin",
  "avot derabbi natan": "Avot DeRabbi Natan",
  avot: "Pirkei Avot",
  zekharia: "Zechariah", "melakhim ii": "II Kings",
  "rashi sur divrei hayamim ii": "Rashi on II Chronicles",
  "rashi sur menachot": "Rashi on Menachot",
  "rambam sur menahot": "Rambam on Mishnah Menachot", "rambam sur menachot": "Rambam on Mishnah Menachot",
  "shemot rabba": "Shemot Rabbah", "shir hashirim rabba": "Shir HaShirim Rabbah",
  "teshouvot haradbaz ii": "Teshuvot HaRadbaz Volume 2",
};
// Un commentaire porte le livre commenté dans sa cote : « Bartenura », « Middot 3:3 ».
const COMMENTAIRES = {
  bartenura: "Bartenura on Mishnah", "tosfot yom tov": "Tosafot Yom Tov on Mishnah",
  "tiferet israel": "Yachin on Mishnah", rashash: "Rashash on Mishnah", boaz: "Boaz on Mishnah",
  radak: "Radak on", "metsoudat david": "Metzudat David on", "melekhet shelomoh": "Melekhet Shelomoh on Mishnah",
};

const pele = (s) => (s || "").toLowerCase().normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "").replace(/['’.,]/g, "").replace(/\s+/g, " ").trim();

const url = (tref) => "https://www.sefaria.org/" +
  encodeURIComponent(tref.replace(/ /g, "_")).replace(/%2C/g, ",").replace(/%3A/g, ":");

function lienCommentaire(commentaire, ref) {
  const cote = /^(?:sur )?(.+) (\d[\d:–-]*)$/.exec((ref || "").trim());
  if (!cote) return null;
  const livre = pele(cote[1]);
  const commente = TRAITES[livre] ?? OUVRAGES[livre];
  return commente ? url(`${commentaire} ${commente} ${cote[2]}`) : null;
}

export function lienSefaria(oeuvre, ref) {
  const clef = pele(oeuvre);
  if (COMMENTAIRES[clef]) return lienCommentaire(COMMENTAIRES[clef], ref);
  if (clef === "rambam") return lienSefaria(`Rambam ${ref.replace(/ [\d:–-]+$/, "")}`, ref.match(/[\d:–-]+$/)?.[0]);
  const direct = OUVRAGES[clef];
  if (direct) return url(`${direct} ${ref}`);
  const traite = TRAITES[clef.replace(/^(mishna|mishnah|talmud) /, "")];
  if (!traite) return null;                       // archéologie, choix du projet : pas de cote Sefaria
  const folio = /^\d+[ab](?:[–-]\d*[ab])?$/.test((ref || "").trim());
  return url(`${folio ? traite : "Mishnah " + traite} ${ref}`);
}
