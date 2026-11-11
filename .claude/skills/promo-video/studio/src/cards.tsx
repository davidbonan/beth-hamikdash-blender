import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Backdrop } from "./Backdrop";
import { GOLD, LINEN, MARK_PATH, MUTED, displayStyle, textStyle } from "./brand";
import { FPS } from "./storyboard";

const DEFAULT_CTA = "bethhamikdach.com";

const rise = (frame: number, delay: number) => spring({ frame: frame - delay, fps: FPS, config: { damping: 16, stiffness: 140 } });

const risingStyle = (progress: number): React.CSSProperties => ({
  opacity: progress,
  transform: `translateY(${(1 - progress) * 28}px)`,
  filter: `blur(${(1 - progress) * 10}px)`,
});

const kickerStyle = (size: number): React.CSSProperties => ({ ...textStyle(size, 600), color: GOLD, letterSpacing: "0.14em", textTransform: "uppercase" });

export const TitleCard: React.FC<{ title: string; kicker?: string }> = ({ title, kicker }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const size = Math.min(width, height * 1.4) * 0.064;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <Backdrop />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: size * 0.4, padding: "0 8%" }}>
        {kicker && <div style={{ ...kickerStyle(size * 0.32), ...risingStyle(rise(frame, 0)) }}>{kicker}</div>}
        <div style={{ ...displayStyle(size), display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: size * 0.26 }}>
          {title.split(" ").map((word, index) => (
            <span key={index} style={{ display: "inline-block", ...risingStyle(rise(frame, 4 + index * 3)) }}>
              {word}
            </span>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const EndCard: React.FC<{ cta?: string }> = ({ cta }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const unit = Math.min(width, height * 1.78) / 1920;
  const glow = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <Backdrop />
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 42%, rgba(201,160,74,${0.2 * glow}) 0%, rgba(16,14,11,0) 45%)` }} />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "0 6%" }}>
        <Img src={staticFile(MARK_PATH)} style={{ width: Math.max(150 * unit, 110), borderRadius: 24 * unit, ...risingStyle(rise(frame, 0)) }} />
        <div style={{ ...displayStyle(Math.max(92 * unit, 56)), marginTop: 40 * unit, ...risingStyle(rise(frame, 6)) }}>Beit HaMikdach</div>
        <div style={{ ...textStyle(Math.max(36 * unit, 26), 400), color: MUTED, fontStyle: "italic", marginTop: 18 * unit, ...risingStyle(rise(frame, 10)) }}>
          Every stone cites its source.
        </div>
        <div
          style={{
            ...textStyle(Math.max(36 * unit, 28), 600),
            color: LINEN,
            marginTop: 52 * unit,
            padding: `${16 * unit}px ${40 * unit}px`,
            borderRadius: 999,
            border: "1px solid rgba(201,160,74,0.6)",
            background: "rgba(201,160,74,0.12)",
            ...risingStyle(rise(frame, 16)),
          }}
        >
          {cta ?? DEFAULT_CTA}
        </div>
        <div style={{ ...kickerStyle(Math.max(22 * unit, 18)), color: MUTED, marginTop: 28 * unit, ...risingStyle(rise(frame, 22)) }}>
          Free · in your browser · built to the Mishnah
        </div>
      </div>
    </AbsoluteFill>
  );
};
