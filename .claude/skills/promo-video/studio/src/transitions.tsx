import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import type { TransitionPresentation, TransitionPresentationComponentProps } from "@remotion/transitions";
import { AbsoluteFill, interpolate } from "remotion";
import type { TransitionKind } from "./storyboard";

type NoProps = Record<string, never>;

const peakAtMiddle = (progress: number) => interpolate(progress, [0, 0.5, 1], [0, 1, 0]);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const ZoomThrough: React.FC<TransitionPresentationComponentProps<NoProps>> = ({ children, presentationDirection, presentationProgress: p }) => {
  if (presentationDirection === "exiting") {
    const scale = interpolate(p, [0, 1], [1, 2.6], { easing: (x) => x * x });
    return (
      <AbsoluteFill style={{ transform: `scale(${scale})`, opacity: interpolate(p, [0.4, 0.7], [1, 0], clamp), filter: `blur(${p * 14}px)` }}>
        {children}
      </AbsoluteFill>
    );
  }
  const scale = interpolate(p, [0, 1], [0.82, 1], { easing: (x) => 1 - (1 - x) ** 3 });
  return (
    <AbsoluteFill style={{ transform: `scale(${scale})`, opacity: interpolate(p, [0.35, 0.65], [0, 1], clamp), filter: `blur(${(1 - p) * 10}px)` }}>
      {children}
    </AbsoluteFill>
  );
};

const Flash: React.FC<TransitionPresentationComponentProps<NoProps>> = ({ children, presentationDirection, presentationProgress: p }) => {
  if (presentationDirection === "exiting") return <AbsoluteFill style={{ opacity: p < 0.5 ? 1 : 0 }}>{children}</AbsoluteFill>;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: p < 0.5 ? 0 : 1 }}>{children}</AbsoluteFill>
      <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 50%, #FFFFFF 0%, #F6E2AC 50%, #C9A04A 100%)", opacity: peakAtMiddle(p) ** 1.5 }} />
    </AbsoluteFill>
  );
};

const custom = (component: React.FC<TransitionPresentationComponentProps<NoProps>>): TransitionPresentation<NoProps> => ({ component, props: {} });

export const presentationOf = (kind: Exclude<TransitionKind, "cut">) =>
  ({
    fade: fade(),
    slide: slide({ direction: "from-right" }),
    wipe: wipe({ direction: "from-left" }),
    zoom: custom(ZoomThrough),
    flash: custom(Flash),
  })[kind] as TransitionPresentation<Record<string, unknown>>;
