import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { GLOW, NIGHT } from "./brand";

export const Backdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const drift = Math.sin(frame / 90) * 4;
  return (
    <AbsoluteFill style={{ backgroundColor: NIGHT }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 70% 60% at ${50 + drift}% 0%, ${GLOW} 0%, rgba(16,14,11,0) 70%)` }} />
    </AbsoluteFill>
  );
};

export const Grain: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.45) 100%)" }} />
      <svg width={width} height={height} style={{ position: "absolute", opacity: 0.05, mixBlendMode: "overlay" }}>
        <filter id="grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={frame % 24} />
        </filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </AbsoluteFill>
  );
};
