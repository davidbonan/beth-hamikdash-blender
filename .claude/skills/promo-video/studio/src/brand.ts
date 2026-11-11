import { loadFont as loadFrankRuhl } from "@remotion/google-fonts/FrankRuhlLibre";
import { loadFont as loadMarcellus } from "@remotion/google-fonts/Marcellus";
import { loadFont as loadSourceSerif } from "@remotion/google-fonts/SourceSerif4";

export const MARK_PATH = "brand/mark.svg";

export const NIGHT = "#100E0B";
export const LINEN = "#F6F1E6";
export const GOLD = "#C9A04A";
export const PALE_GOLD = "#F6E2AC";
export const MUTED = "rgba(246,241,230,0.66)";
export const GLOW = "rgba(201,160,74,0.30)";

const HEBREW = loadFrankRuhl("normal", { weights: ["400", "500"], subsets: ["hebrew"] }).fontFamily;
export const DISPLAY = `${loadMarcellus("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily}, ${HEBREW}`;
loadSourceSerif("italic", { weights: ["400"], subsets: ["latin"] });
export const SERIF = `${loadSourceSerif("normal", { weights: ["400", "600"], subsets: ["latin"] }).fontFamily}, ${HEBREW}`;

export const textStyle = (size: number, weight = 600): React.CSSProperties => ({
  fontFamily: SERIF,
  fontWeight: weight,
  fontSize: size,
  lineHeight: 1.15,
  color: LINEN,
  textAlign: "center",
  textShadow: "0 2px 18px rgba(0,0,0,0.55)",
});

export const displayStyle = (size: number): React.CSSProperties => ({
  ...textStyle(size, 400),
  fontFamily: DISPLAY,
  letterSpacing: "0.02em",
});
