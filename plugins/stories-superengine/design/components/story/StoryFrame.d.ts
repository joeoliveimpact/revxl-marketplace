import * as React from 'react';
/**
 * 1080×1920 story canvas with full-bleed background and the safe-area content box (270 top / 384 bottom / 65 sides).
 * @startingPoint section="Story" subtitle="Blank 1080×1920 story canvas" viewport="1080x1920"
 */
export interface StoryFrameProps {
  /** 'photo' | 'screenshot' placeholder, any swatch hex as a flat fill, or 'cm-1'..'cm-7' create-mode wash. */
  background?: string;
  /** CSS scale applied from top-left (for previews). */
  scale?: number;
  /** Draw the dashed safe-zone overlay (never exported). */
  guides?: boolean;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}
export declare function StoryFrame(props: StoryFrameProps): JSX.Element;
export declare function SafeZoneGuide(): JSX.Element;
