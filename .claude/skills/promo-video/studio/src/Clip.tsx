import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { Fragment } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Grain } from "./Backdrop";
import { NIGHT } from "./brand";
import { EndCard, TitleCard } from "./cards";
import { Footage } from "./Footage";
import { Soundtrack } from "./Soundtrack";
import { FPS, isFootage, placeShots, type PlacedShot, type Storyboard } from "./storyboard";
import { Captions, Cite, Hook, Label } from "./texts";
import { presentationOf } from "./transitions";

const DEFAULT_HOOK_SECONDS = 2.2;

const ShotContent: React.FC<{ placed: PlacedShot }> = ({ placed }) => {
  const frame = useCurrentFrame();
  const { shot, leadInFrames, lengthInFrames } = placed;
  return (
    <AbsoluteFill>
      {shot.kind === "title" && <TitleCard title={shot.title} kicker={shot.kicker} />}
      {shot.kind === "end" && <EndCard cta={shot.cta} />}
      {isFootage(shot) && <Footage shot={shot} t={(frame - leadInFrames) / FPS} />}
      {isFootage(shot) && shot.cite && <Cite text={shot.cite} leadInFrames={leadInFrames} />}
      {shot.label && <Label text={shot.label} lengthInFrames={lengthInFrames} leadInFrames={leadInFrames} />}
    </AbsoluteFill>
  );
};

export const Clip: React.FC<Storyboard> = (storyboard) => {
  const { durationInFrames } = useVideoConfig();
  const placed = placeShots(storyboard.shots);
  return (
    <AbsoluteFill style={{ backgroundColor: NIGHT }}>
      <TransitionSeries>
        {placed.map((shot, index) => (
          <Fragment key={index}>
            <TransitionSeries.Sequence durationInFrames={shot.lengthInFrames}>
              <ShotContent placed={shot} />
            </TransitionSeries.Sequence>
            {shot.transitionOut && (
              <TransitionSeries.Transition
                presentation={presentationOf(shot.transitionOut.type)}
                timing={linearTiming({ durationInFrames: shot.transitionOut.frames })}
              />
            )}
          </Fragment>
        ))}
      </TransitionSeries>
      <Grain />
      {storyboard.hook && <Hook text={storyboard.hook} seconds={storyboard.hookSeconds ?? DEFAULT_HOOK_SECONDS} />}
      <Captions lines={storyboard.voice ?? []} />
      <Soundtrack music={storyboard.music} voices={storyboard.voice ?? []} effects={storyboard.effects ?? []} durationInFrames={durationInFrames} />
    </AbsoluteFill>
  );
};
