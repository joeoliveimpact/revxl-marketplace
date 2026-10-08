import * as React from 'react';
/**
 * Native Instagram Stories text block: one of the 14 style-picker styles, one of the 27 swatches,
 * the A-button background (off / light / solid), alignment, and optional video animation + effect.
 * @startingPoint section="Story" subtitle="One native text block with a word bubble" viewport="700x260"
 */
export interface StoryTextProps {
  /** Text; use \n for multiple lines. Each line gets its own bubble; rounded/pill styles fuse (gooey). */
  text: string;
  /** Picker order: modern, classic, signature, editor, poster, bubble, deco, squeeze, typewriter, strong, meme, elegant, directional, literature */
  style?: 'modern' | 'classic' | 'signature' | 'editor' | 'poster' | 'bubble' | 'deco' | 'squeeze' | 'typewriter' | 'strong' | 'meme' | 'elegant' | 'directional' | 'literature';
  /** Swatch name (e.g. "blue") or one of the 27 hex codes. */
  color?: string;
  /** A-button cycle: off (letters = swatch), light (pale fill, swatch letters), solid (swatch fill, white letters). */
  background?: 'off' | 'light' | 'solid';
  align?: 'left' | 'center' | 'right';
  /** Font size in px on a 1080-wide canvas. Default 70. */
  size?: number;
  /** Video stories only. */
  animation?: 'none' | 'typewriter' | 'pop' | 'jump';
  /** Video stories only. */
  effect?: 'none' | 'sparkle' | 'neon' | 'shimmer' | 'pixel';
  className?: string;
}
export declare function StoryText(props: StoryTextProps): JSX.Element;
