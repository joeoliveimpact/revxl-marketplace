/* lh = line-height in cap units; pad = [top from cap top, bottom from baseline, sides] in cap units — measured in the app. */
/* family: 'block' = one square rectangle behind the whole paragraph; otherwise per-line shapes that fuse. */
export const STYLES = [
  { id: 'modern', label: 'Modern', font: 'Roboto Condensed', weight: 400, shape: 'rounded', letterSpacing: '-0.07em', lh: 1.57, pad: [0.62, 0.7, 0.51] },
  { id: 'classic', label: 'Classic', font: 'Inter Tight', weight: 700, shape: 'rounded', lh: 1.57, pad: [0.57, 0.65, 0.49] },
  { id: 'signature', label: 'Signature', font: 'Caveat', weight: 500, shape: 'pill', lh: 1.58, pad: [0.6, 0.73, 1.23] },
  { id: 'editor', family: 'block', label: 'Editor', font: 'JetBrains Mono', weight: 400, shape: 'square', letterSpacing: '0.02em', lh: 1.7, pad: [1.19, 1.19, 1.28] },
  { id: 'poster', label: 'Poster', font: 'Fraunces', weight: 800, shape: 'rounded', lh: 1.42, pad: [0.73, 0.83, 1.1] },
  { id: 'bubble', label: 'Bubble', font: 'Fredoka', weight: 700, shape: 'pill', lh: 1.53, pad: [0.62, 0.77, 1.28] },
  { id: 'deco', family: 'block', label: 'Deco', font: 'Quicksand', weight: 400, shape: 'square', lh: 1.53, pad: [1.19, 1.19, 1.28] },
  { id: 'squeeze', label: 'Squeeze', font: 'Anton', weight: 400, shape: 'square', lh: 1.35, pad: [0.2, 0.27, 0.34] },
  { id: 'typewriter', family: 'block', label: 'Typewriter', font: 'Courier Prime', weight: 700, shape: 'square', lh: 2.13, pad: [1.44, 1.33, 1.42] },
  { id: 'strong', label: 'Strong', font: 'Montserrat', weight: 900, italic: true, shape: 'rounded', lh: 1.4, pad: [0.45, 0.7, 0.55] },
  { id: 'meme', label: 'Meme', font: 'Comic Neue', weight: 700, shape: 'rounded', letterSpacing: '-0.06em', lh: 2.17, pad: [0.59, 0.8, 0.57] },
  { id: 'elegant', family: 'block', label: 'Elegant', font: 'Playfair Display', weight: 400, italic: true, shape: 'square', lh: 1.45, pad: [1.36, 1.25, 1.36] },
  { id: 'directional', label: 'Directional', font: 'Inter Tight', weight: 700, shape: 'pill', uppercase: true, lh: 1.64, pad: [0.68, 0.77, 1.34] },
  { id: 'literature', family: 'block', label: 'Literature', font: 'Libre Baskerville', weight: 400, shape: 'square', lh: 1.7, pad: [0.98, 0.98, 1.21] },
];
export const STYLE_MAP = Object.fromEntries(STYLES.map(s => [s.id, s]));

export const SWATCHES = [
  ['white', '#FFFFFF'], ['black', '#000000'], ['blue', '#3897F0'], ['green', '#70C050'], ['yellow', '#FDCB5C'], ['orange', '#FD8D32'], ['red', '#ED4956'], ['magenta', '#D10869'], ['purple', '#A307BA'],
  ['scarlet', '#ED0013'], ['salmon', '#ED858E'], ['light-salmon', '#FFD2D3'], ['light-sand', '#FFDBB4'], ['sand', '#FFC382'], ['dark-sand', '#D28F46'], ['brown', '#996439'], ['dark-brown', '#432324'], ['dark-green', '#1C4A29'],
  ['gray-1', '#262626'], ['gray-2', '#363636'], ['gray-3', '#555555'], ['gray-4', '#737373'], ['gray-5', '#999999'], ['gray-6', '#B2B2B2'], ['gray-7', '#C7C7C7'], ['gray-8', '#DBDBDB'], ['gray-9', '#EFEFEF'],
];
export const SWATCH_MAP = Object.fromEntries(SWATCHES);

export function swatchHex(s) { return SWATCH_MAP[s] || s; }
/* Every swatch has one measured partner. Light = partner fill + swatch letters. Solid = swatch fill + partner letters. */
export const PARTNERS = {'white':'#000000', 'black':'#FFFFFF', 'blue':'#E9F2F9', 'green':'#EFF6EE', 'yellow':'#FEF8E8', 'orange':'#FEF1E8', 'red':'#FAEAEB', 'magenta':'#FEDBEF', 'purple':'#F7D9FD', 'scarlet':'#FEE0E4', 'salmon':'#FBF0F0', 'light-salmon':'#261F1E', 'light-sand':'#2D2420', 'sand':'#352624', 'dark-sand':'#F8F1EA', 'brown':'#F6EBE5', 'dark-brown':'#F1DEE0', 'dark-green':'#DCF1E6', 'gray-1':'#E6E6E6', 'gray-2':'#E7E7E7', 'gray-3':'#ECECEC', 'gray-4':'#EEEEEE', 'gray-5':'#F4F4F4', 'gray-6':'#F5F5F5', 'gray-7':'#363636', 'gray-8':'#262626', 'gray-9':'#252525'};
function rgbOf(hex) { const n = parseInt(hex.slice(1), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
function lumOf(hex) { const [r, g, b] = rgbOf(hex); return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255; }
/* Custom colors (eyedropper) borrow the behaviour of the nearest of the 27 swatches: a pale tint over white,
   or — for the light swatches whose partner is dark (white, light salmon, light sand, sand, gray 7-9) — a dark shade.
   Brightness alone does not predict this: yellow is bright but takes a pale partner. */
export function partnerOf(color) {
  const hex = swatchHex(color).toUpperCase();
  if (SWATCH_MAP[color] || SWATCHES.some(([, h]) => h === hex)) {
    const named = SWATCHES.find(([, h]) => h === hex);
    if (named) return PARTNERS[named[0]];
  }
  const [r, g, b] = rgbOf(hex);
  let nearest = SWATCHES[0], best = Infinity;
  for (const entry of SWATCHES) {
    const [nr, ng, nb] = rgbOf(entry[1]);
    const d = (r - nr) ** 2 + (g - ng) ** 2 + (b - nb) ** 2;
    if (d < best) { best = d; nearest = entry; }
  }
  const darkPartner = lumOf(PARTNERS[nearest[0]]) < 0.5;
  const mix = darkPartner ? c => Math.round(c * 0.16) : c => Math.round(255 + (c - 255) * 0.12);
  return '#' + [r, g, b].map(v => mix(v).toString(16).padStart(2, '0')).join('').toUpperCase();
}
export const lightFill = partnerOf;
export const CREATE_MODE_BG = [1, 2, 3, 4, 5, 6, 7].map(i => `var(--cm-${i})`);
