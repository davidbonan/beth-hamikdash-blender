import { Composition, staticFile, type CalculateMetadataFunction } from "remotion";
import { Clip } from "./Clip";
import { FPS, SIZES, timingPathOf, totalFrames, type Storyboard, type VoiceLine } from "./storyboard";

const withWordTimings = async (line: VoiceLine): Promise<VoiceLine> => {
  const response = await fetch(staticFile(timingPathOf(line.audio)));
  if (!response.ok) throw new Error(`Word timings not found: ${timingPathOf(line.audio)} (${response.status})`);
  const timing: { words: VoiceLine["words"] } = await response.json();
  return { ...line, words: timing.words };
};

const calculateMetadata: CalculateMetadataFunction<Storyboard> = async ({ props }) => ({
  ...SIZES[props.format ?? "landscape"],
  durationInFrames: Math.max(1, totalFrames(props.shots)),
  props: { ...props, voice: await Promise.all((props.voice ?? []).map(withWordTimings)) },
});

const EMPTY: Storyboard = { hook: "Pass a storyboard with --props", shots: [{ kind: "end", duration: 3 }] };

export const Root: React.FC = () => (
  <Composition
    id="Clip"
    component={Clip}
    {...SIZES.landscape}
    fps={FPS}
    durationInFrames={1}
    defaultProps={EMPTY}
    calculateMetadata={calculateMetadata}
  />
);
