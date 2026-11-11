import { AbsoluteFill, Easing, Freeze, Img, OffthreadVideo, interpolate, staticFile } from "remotion";
import { Backdrop } from "./Backdrop";
import { FPS, type CameraKey, type FootageShot } from "./storyboard";

const WIDE: CameraKey = { t: 0, x: 0.5, y: 0.5, zoom: 1 };

const isStill = (source: string) => /\.(png|jpe?g|webp)$/i.test(source);

const sourceSecondsAt = (shot: FootageShot, t: number) => {
  const [from, to] = Array.isArray(shot.speed) ? shot.speed : [shot.speed ?? 1, shot.speed ?? 1];
  const start = shot.start ?? 0;
  if (t < 0) return Math.max(0, start + from * t);
  if (t <= shot.duration) return start + from * t + ((to - from) * t * t) / (2 * shot.duration);
  return start + ((from + to) / 2) * shot.duration + to * (t - shot.duration);
};

const cameraAt = (keys: CameraKey[] | undefined, t: number): CameraKey => {
  if (!keys?.length) return WIDE;
  const next = keys.findIndex((key) => key.t > t);
  if (next === -1) return keys[keys.length - 1];
  if (next === 0) return keys[0];
  const [a, b] = [keys[next - 1], keys[next]];
  const progress = interpolate(t, [a.t, b.t], [0, 1], { easing: Easing.inOut(Easing.cubic) });
  const blend = (from: number, to: number) => from + (to - from) * progress;
  return { t, x: blend(a.x, b.x), y: blend(a.y, b.y), zoom: blend(a.zoom, b.zoom) };
};

const keepInFrame = (center: number, zoom: number) => Math.min(Math.max(center, 0.5 / zoom), 1 - 0.5 / zoom);

const WINDOW_STYLE: React.CSSProperties = {
  maxWidth: "88%",
  maxHeight: "80%",
  borderRadius: 18,
  outline: "1px solid rgba(255,255,255,0.10)",
  boxShadow: "0 40px 120px rgba(0,0,0,0.65), 0 0 0 1px rgba(0,0,0,0.6), 0 0 160px rgba(201,160,74,0.18)",
};
const FULL_STYLE: React.CSSProperties = { width: "100%", height: "100%", objectFit: "cover" };

const Media: React.FC<{ shot: FootageShot; t: number; style: React.CSSProperties }> = ({ shot, t, style }) =>
  isStill(shot.source) ? (
    <Img src={staticFile(shot.source)} style={style} />
  ) : (
    // A frozen OffthreadVideo seeks through trimBefore, which lets `speed` ramp freely.
    <Freeze frame={0}>
      <OffthreadVideo src={staticFile(shot.source)} trimBefore={Math.round(sourceSecondsAt(shot, t) * FPS)} muted style={style} />
    </Freeze>
  );

export const Footage: React.FC<{ shot: FootageShot; t: number }> = ({ shot, t }) => {
  const camera = cameraAt(shot.camera, t);
  const zoom = Math.max(1, camera.zoom);
  const x = keepInFrame(camera.x, zoom);
  const y = keepInFrame(camera.y, zoom);
  const isWindow = shot.kind === "window";
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${zoom}) translate(${(0.5 - x) * 100}%, ${(0.5 - y) * 100}%)`, filter: shot.filter }}>
        {isWindow && <Backdrop />}
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <Media shot={shot} t={t} style={isWindow ? WINDOW_STYLE : FULL_STYLE} />
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
