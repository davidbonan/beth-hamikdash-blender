import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { GOLD, LINEN, textStyle } from "./brand";
import { FPS, frames, type VoiceLine, type Word } from "./storyboard";

const enter = (frame: number, delay = 0) => spring({ frame: frame - delay, fps: FPS, config: { damping: 14, stiffness: 180 } });

const BottomBand: React.FC<{ children: React.ReactNode; opacity?: number }> = ({ children, opacity = 1 }) => {
  const { height } = useVideoConfig();
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: height * 0.34, opacity, pointerEvents: "none" }}>
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to top, rgba(16,14,11,0.88) 0%, rgba(16,14,11,0.55) 45%, rgba(16,14,11,0) 100%)" }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: height * 0.08, padding: "0 8%", display: "flex", justifyContent: "center" }}>
        {children}
      </div>
    </div>
  );
};

const PoppingWords: React.FC<{ text: string; size: number; stagger: number }> = ({ text, size, stagger }) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ ...textStyle(size), display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: size * 0.28 }}>
      {text.split(" ").map((word, index) => {
        const pop = enter(frame, index * stagger);
        return (
          <span key={index} style={{ display: "inline-block", opacity: pop, transform: `translateY(${(1 - pop) * size * 0.35}px)`, filter: `blur(${(1 - pop) * 8}px)` }}>
            {word}
          </span>
        );
      })}
    </div>
  );
};

const fadeOutAt = (frame: number, end: number) => interpolate(frame, [end - 6, end], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

export const Hook: React.FC<{ text: string; seconds: number }> = ({ text, seconds }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const end = frames(seconds);
  if (frame >= end) return null;
  return (
    <BottomBand opacity={fadeOutAt(frame, end)}>
      <PoppingWords text={text} size={width * 0.042} stagger={3} />
    </BottomBand>
  );
};

export const Label: React.FC<{ text: string; lengthInFrames: number; leadInFrames: number }> = ({ text, lengthInFrames, leadInFrames }) => {
  const frame = useCurrentFrame() - leadInFrames;
  const { width } = useVideoConfig();
  return (
    <BottomBand opacity={fadeOutAt(frame, lengthInFrames - leadInFrames)}>
      <PoppingWords text={text} size={width * 0.032} stagger={2} />
    </BottomBand>
  );
};

const CITE_DELAY_FRAMES = 6;

export const Cite: React.FC<{ text: string; leadInFrames: number }> = ({ text, leadInFrames }) => {
  const frame = useCurrentFrame() - leadInFrames;
  const { width, height } = useVideoConfig();
  const pop = enter(frame, CITE_DELAY_FRAMES);
  const size = Math.min(width, height) * 0.034;
  return (
    <div
      style={{
        ...textStyle(size, 400),
        position: "absolute",
        top: size * 1.8,
        left: size * 1.8,
        fontStyle: "italic",
        textAlign: "left",
        padding: `${size * 0.3}px ${size * 0.6}px`,
        borderLeft: `3px solid ${GOLD}`,
        background: "rgba(16,14,11,0.55)",
        opacity: pop,
        transform: `translateX(${(1 - pop) * -size}px)`,
      }}
    >
      {text}
    </div>
  );
};

type Chunk = { words: Word[]; from: number; to: number };

const WORDS_PER_CHUNK = 4;
const LINGER_SECONDS = 0.35;
const endsPhrase = (word: string) => /[.,!?…;:]$/.test(word);

const phrasesOf = (words: Word[]) => {
  const phrases: Word[][] = [[]];
  for (const word of words) {
    phrases[phrases.length - 1].push(word);
    if (endsPhrase(word.word)) phrases.push([]);
  }
  return phrases.filter((phrase) => phrase.length);
};

const balancedGroups = (phrase: Word[]) => {
  const count = Math.ceil(phrase.length / WORDS_PER_CHUNK);
  return Array.from({ length: count }, (_, index) =>
    phrase.slice(Math.round((index * phrase.length) / count), Math.round(((index + 1) * phrase.length) / count)),
  );
};

const chunksOf = (line: VoiceLine) => {
  const words = (line.words ?? []).map((word) => ({ ...word, start: word.start + line.at, end: word.end + line.at }));
  return phrasesOf(words).flatMap(balancedGroups);
};

const timedChunks = (lines: VoiceLine[]): Chunk[] => {
  const groups = lines.flatMap(chunksOf).sort((a, b) => a[0].start - b[0].start);
  return groups.map((group, index) => {
    const lingering = group[group.length - 1].end + LINGER_SECONDS;
    const next = groups[index + 1]?.[0].start ?? Infinity;
    return { words: group, from: group[0].start, to: Math.min(lingering, next) };
  });
};

const displayed = (word: string) => word.replace(/[.,;:…]+$/, "");

export const Captions: React.FC<{ lines: VoiceLine[] }> = ({ lines }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const t = frame / FPS;
  const chunk = timedChunks(lines).find((candidate) => t >= candidate.from && t < candidate.to);
  if (!chunk) return null;
  const size = width * 0.03;
  return (
    <BottomBand>
      <div style={{ ...textStyle(size, 650), display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: size * 0.26 }}>
        {chunk.words.map((word, index) => (
          <span key={index} style={{ color: t >= word.start && t < (chunk.words[index + 1]?.start ?? chunk.to) ? GOLD : LINEN }}>
            {displayed(word.word)}
          </span>
        ))}
      </div>
    </BottomBand>
  );
};
