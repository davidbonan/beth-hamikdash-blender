import { Audio } from "@remotion/media";
import { Sequence, interpolate, staticFile } from "remotion";
import { FPS, frames, type Music, type SoundEffect, type VoiceLine } from "./storyboard";

const DUCK_RAMP_SECONDS = 0.25;
const FADE_OUT_SECONDS = 1.2;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const speakingSpans = (lines: VoiceLine[]) =>
  lines.flatMap((line) => {
    const words = line.words ?? [];
    return words.length ? [[line.at + words[0].start, line.at + words[words.length - 1].end]] : [];
  });

const duckingAt = (spans: number[][], t: number) =>
  Math.max(0, ...spans.map(([from, to]) => interpolate(t, [from - DUCK_RAMP_SECONDS, from, to, to + DUCK_RAMP_SECONDS], [0, 1, 1, 0], clamp)));

const MusicBed: React.FC<{ music: Music; voices: VoiceLine[]; durationInFrames: number }> = ({ music, voices, durationInFrames }) => {
  const spans = speakingSpans(voices);
  const musicStart = frames(music.at ?? 0);
  const end = durationInFrames / FPS;
  const volumeAt = (frame: number) => {
    const t = (frame + musicStart) / FPS;
    const level = music.volume + (music.underVoice - music.volume) * duckingAt(spans, t);
    return level * interpolate(t, [end - FADE_OUT_SECONDS, end], [1, 0], clamp);
  };
  return (
    <Sequence from={musicStart}>
      <Audio src={staticFile(music.audio)} trimBefore={frames(music.start ?? 0)} volume={volumeAt} />
    </Sequence>
  );
};

export const Soundtrack: React.FC<{ music?: Music; voices: VoiceLine[]; effects: SoundEffect[]; durationInFrames: number }> = ({
  music,
  voices,
  effects,
  durationInFrames,
}) => (
  <>
    {music && <MusicBed music={music} voices={voices} durationInFrames={durationInFrames} />}
    {[...voices, ...effects].map((sound, index) => (
      <Sequence key={index} from={frames(sound.at)}>
        <Audio src={staticFile(sound.audio)} volume={sound.volume ?? 1} />
      </Sequence>
    ))}
  </>
);
