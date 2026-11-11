export type Format = "landscape" | "square" | "portrait";

export type TransitionKind = "cut" | "fade" | "slide" | "wipe" | "zoom" | "flash";

export type Transition = { type: TransitionKind; duration: number };

export type CameraKey = { t: number; x: number; y: number; zoom: number };

type ShotBase = { duration: number; label?: string; transition?: Transition };

export type FootageShot = ShotBase & {
  kind: "window" | "full";
  source: string;
  start?: number;
  speed?: number | [number, number];
  camera?: CameraKey[];
  filter?: string;
  cite?: string;
};

export type TitleShot = ShotBase & { kind: "title"; title: string; kicker?: string };

export type EndShot = ShotBase & { kind: "end"; cta?: string };

export type Shot = FootageShot | TitleShot | EndShot;

export type Word = { word: string; start: number; end: number };

export type VoiceLine = { audio: string; at: number; volume?: number; words?: Word[] };

export type SoundEffect = { audio: string; at: number; volume?: number };

export type Music = { audio: string; at?: number; start?: number; volume: number; underVoice: number };

export type Storyboard = {
  format?: Format;
  hook?: string;
  hookSeconds?: number;
  shots: Shot[];
  voice?: VoiceLine[];
  effects?: SoundEffect[];
  music?: Music;
};

export const FPS = 30;

export const SIZES: Record<Format, { width: number; height: number }> = {
  landscape: { width: 1920, height: 1080 },
  square: { width: 1080, height: 1080 },
  portrait: { width: 1080, height: 1920 },
};

export const frames = (seconds: number) => Math.round(seconds * FPS);

export const isFootage = (shot: Shot): shot is FootageShot => shot.kind === "window" || shot.kind === "full";

export type BlendedTransition = { type: Exclude<TransitionKind, "cut">; frames: number };

export type PlacedShot = {
  shot: Shot;
  lengthInFrames: number;
  leadInFrames: number;
  transitionOut?: BlendedTransition;
};

const blendOf = (shot: Shot | undefined): BlendedTransition | undefined => {
  const transition = shot?.transition;
  if (!transition || transition.type === "cut") return undefined;
  return { type: transition.type, frames: frames(transition.duration) };
};

export const placeShots = (shots: Shot[]): PlacedShot[] =>
  shots.map((shot, index) => {
    const transitionOut = index === shots.length - 1 ? undefined : blendOf(shot);
    const leadInFrames = Math.ceil((blendOf(shots[index - 1])?.frames ?? 0) / 2);
    return {
      shot,
      leadInFrames,
      transitionOut,
      lengthInFrames: frames(shot.duration) + leadInFrames + Math.floor((transitionOut?.frames ?? 0) / 2),
    };
  });

export const totalFrames = (shots: Shot[]) => shots.reduce((sum, shot) => sum + frames(shot.duration), 0);

export const timingPathOf = (audio: string) => audio.replace(/\.[a-z0-9]+$/, ".json");
