/* @ds-bundle: {"format":4,"namespace":"IGStoryNative_12be32","components":[{"name":"StoryFrame","sourcePath":"components/story/StoryFrame.jsx"},{"name":"SafeZoneGuide","sourcePath":"components/story/StoryFrame.jsx"},{"name":"StoryText","sourcePath":"components/story/StoryText.jsx"},{"name":"STYLES","sourcePath":"components/story/story-styles.js"},{"name":"STYLE_MAP","sourcePath":"components/story/story-styles.js"},{"name":"SWATCHES","sourcePath":"components/story/story-styles.js"},{"name":"SWATCH_MAP","sourcePath":"components/story/story-styles.js"},{"name":"PARTNERS","sourcePath":"components/story/story-styles.js"},{"name":"CREATE_MODE_BG","sourcePath":"components/story/story-styles.js"}],"sourceHashes":{"components/story/StoryFrame.jsx":"0aff01fddf19","components/story/StoryText.jsx":"eb4816dafe05","components/story/story-styles.js":"f27f63665571"},"inlinedExternals":[],"unexposedExports":[{"name":"lightFill","sourcePath":"components/story/story-styles.js"},{"name":"partnerOf","sourcePath":"components/story/story-styles.js"},{"name":"swatchHex","sourcePath":"components/story/story-styles.js"}]} */

(() => {

const __ds_ns = (window.IGStoryNative_12be32 = window.IGStoryNative_12be32 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/story/StoryFrame.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* 1080x1920 canvas. background: 'photo' | 'screenshot' | swatch hex | 'cm-1'..'cm-7'. */
function StoryFrame({
  background = '#000000',
  scale = 1,
  guides = false,
  children,
  style,
  ...rest
}) {
  let bg = {
    background
  };
  let placeholder = null;
  if (background === 'photo' || background === 'screenshot') {
    bg = {
      background: background === 'photo' ? '#3A3F47' : '#F2F2F2'
    };
    placeholder = /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'absolute',
        inset: 0,
        display: 'grid',
        placeItems: 'center',
        color: background === 'photo' ? '#9AA1AA' : '#8E8E8E',
        fontFamily: '"Roboto Condensed"',
        fontSize: 40,
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        backgroundImage: background === 'photo' ? 'repeating-linear-gradient(45deg,transparent 0 40px,rgba(255,255,255,.04) 40px 80px)' : 'repeating-linear-gradient(0deg,transparent 0 120px,rgba(0,0,0,.06) 120px 121px)'
      }
    }, background === 'photo' ? 'Photo' : 'Screenshot');
  } else if (/^cm-[1-7]$/.test(background)) bg = {
    background: `var(--${background})`
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      width: 1080,
      height: 1920,
      position: 'relative',
      overflow: 'hidden',
      flex: 'none',
      transform: scale !== 1 ? `scale(${scale})` : undefined,
      transformOrigin: 'top left',
      ...bg,
      ...style
    }
  }, rest), placeholder, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 65,
      right: 65,
      top: 270,
      bottom: 384,
      display: 'flex',
      flexDirection: 'column'
    }
  }, children), guides && /*#__PURE__*/React.createElement(SafeZoneGuide, null));
}
function SafeZoneGuide() {
  const dash = '2px dashed rgba(255,255,255,.7)';
  const lbl = {
    position: 'absolute',
    fontFamily: '"Roboto Condensed"',
    fontSize: 28,
    color: '#fff',
    background: 'rgba(0,0,0,.55)',
    padding: '6px 12px'
  };
  return /*#__PURE__*/React.createElement("div", {
    "aria-hidden": true,
    style: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 65,
      right: 65,
      top: 270,
      bottom: 384,
      border: dash
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      top: 0,
      height: 270,
      background: 'rgba(0,0,0,.35)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      bottom: 0,
      height: 384,
      background: 'rgba(0,0,0,.35)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      ...lbl,
      top: 24,
      left: 65
    }
  }, "270px \xB7 progress bar + profile header \xB7 guide, not exported"), /*#__PURE__*/React.createElement("div", {
    style: {
      ...lbl,
      bottom: 24,
      left: 65
    }
  }, "384px \xB7 reply bar \xB7 guide, not exported"), /*#__PURE__*/React.createElement("div", {
    style: {
      ...lbl,
      top: 290,
      left: 85
    }
  }, "safe area \xB7 65px sides"));
}
Object.assign(__ds_scope, { StoryFrame, SafeZoneGuide });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/story/StoryFrame.jsx", error: String((e && e.message) || e) }); }

// components/story/story-styles.js
try { (() => {
/* lh = line-height in cap units; pad = [top from cap top, bottom from baseline, sides] in cap units — measured in the app. */
/* family: 'block' = one square rectangle behind the whole paragraph; otherwise per-line shapes that fuse. */
const STYLES = [{
  id: 'modern',
  label: 'Modern',
  font: 'Roboto Condensed',
  weight: 400,
  shape: 'rounded',
  lh: 1.57,
  pad: [0.62, 0.7, 0.51]
}, {
  id: 'classic',
  label: 'Classic',
  font: 'Inter Tight',
  weight: 700,
  shape: 'rounded',
  lh: 1.57,
  pad: [0.57, 0.65, 0.49]
}, {
  id: 'signature',
  label: 'Signature',
  font: 'Caveat',
  weight: 500,
  shape: 'pill',
  lh: 1.58,
  pad: [0.6, 0.73, 1.23]
}, {
  id: 'editor',
  family: 'block',
  label: 'Editor',
  font: 'JetBrains Mono',
  weight: 400,
  shape: 'square',
  letterSpacing: '0.02em',
  lh: 1.7,
  pad: [1.19, 1.19, 1.28]
}, {
  id: 'poster',
  label: 'Poster',
  font: 'Fraunces',
  weight: 800,
  shape: 'rounded',
  lh: 1.42,
  pad: [0.73, 0.83, 1.1]
}, {
  id: 'bubble',
  label: 'Bubble',
  font: 'Fredoka',
  weight: 700,
  shape: 'pill',
  lh: 1.53,
  pad: [0.62, 0.77, 1.28]
}, {
  id: 'deco',
  family: 'block',
  label: 'Deco',
  font: 'Quicksand',
  weight: 400,
  shape: 'square',
  lh: 1.53,
  pad: [1.19, 1.19, 1.28]
}, {
  id: 'squeeze',
  label: 'Squeeze',
  font: 'Anton',
  weight: 400,
  shape: 'square',
  lh: 1.35,
  pad: [0.2, 0.27, 0.34]
}, {
  id: 'typewriter',
  family: 'block',
  label: 'Typewriter',
  font: 'Courier Prime',
  weight: 700,
  shape: 'square',
  lh: 2.13,
  pad: [1.44, 1.33, 1.42]
}, {
  id: 'strong',
  label: 'Strong',
  font: 'Montserrat',
  weight: 900,
  italic: true,
  shape: 'rounded',
  lh: 1.4,
  pad: [0.45, 0.7, 0.55]
}, {
  id: 'meme',
  label: 'Meme',
  font: 'Comic Neue',
  weight: 700,
  shape: 'rounded',
  lh: 2.17,
  pad: [0.59, 0.8, 0.57]
}, {
  id: 'elegant',
  family: 'block',
  label: 'Elegant',
  font: 'Playfair Display',
  weight: 400,
  italic: true,
  shape: 'square',
  lh: 1.45,
  pad: [1.36, 1.25, 1.36]
}, {
  id: 'directional',
  label: 'Directional',
  font: 'Inter Tight',
  weight: 700,
  shape: 'pill',
  uppercase: true,
  lh: 1.64,
  pad: [0.68, 0.77, 1.34]
}, {
  id: 'literature',
  family: 'block',
  label: 'Literature',
  font: 'Libre Baskerville',
  weight: 400,
  shape: 'square',
  lh: 1.7,
  pad: [0.98, 0.98, 1.21]
}];
const STYLE_MAP = Object.fromEntries(STYLES.map(s => [s.id, s]));
const SWATCHES = [['white', '#FFFFFF'], ['black', '#000000'], ['blue', '#3897F0'], ['green', '#70C050'], ['yellow', '#FDCB5C'], ['orange', '#FD8D32'], ['red', '#ED4956'], ['magenta', '#D10869'], ['purple', '#A307BA'], ['scarlet', '#ED0013'], ['salmon', '#ED858E'], ['light-salmon', '#FFD2D3'], ['light-sand', '#FFDBB4'], ['sand', '#FFC382'], ['dark-sand', '#D28F46'], ['brown', '#996439'], ['dark-brown', '#432324'], ['dark-green', '#1C4A29'], ['gray-1', '#262626'], ['gray-2', '#363636'], ['gray-3', '#555555'], ['gray-4', '#737373'], ['gray-5', '#999999'], ['gray-6', '#B2B2B2'], ['gray-7', '#C7C7C7'], ['gray-8', '#DBDBDB'], ['gray-9', '#EFEFEF']];
const SWATCH_MAP = Object.fromEntries(SWATCHES);
function swatchHex(s) {
  return SWATCH_MAP[s] || s;
}
/* Every swatch has one measured partner. Light = partner fill + swatch letters. Solid = swatch fill + partner letters. */
const PARTNERS = {
  'white': '#000000',
  'black': '#FFFFFF',
  'blue': '#E9F2F9',
  'green': '#EFF6EE',
  'yellow': '#FEF8E8',
  'orange': '#FEF1E8',
  'red': '#FAEAEB',
  'magenta': '#FEDBEF',
  'purple': '#F7D9FD',
  'scarlet': '#FEE0E4',
  'salmon': '#FBF0F0',
  'light-salmon': '#261F1E',
  'light-sand': '#2D2420',
  'sand': '#352624',
  'dark-sand': '#F8F1EA',
  'brown': '#F6EBE5',
  'dark-brown': '#F1DEE0',
  'dark-green': '#DCF1E6',
  'gray-1': '#E6E6E6',
  'gray-2': '#E7E7E7',
  'gray-3': '#ECECEC',
  'gray-4': '#EEEEEE',
  'gray-5': '#F4F4F4',
  'gray-6': '#F5F5F5',
  'gray-7': '#363636',
  'gray-8': '#262626',
  'gray-9': '#252525'
};
function rgbOf(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [n >> 16 & 255, n >> 8 & 255, n & 255];
}
function lumOf(hex) {
  const [r, g, b] = rgbOf(hex);
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}
/* Custom colors (eyedropper) borrow the behaviour of the nearest of the 27 swatches: a pale tint over white,
   or — for the light swatches whose partner is dark (white, light salmon, light sand, sand, gray 7-9) — a dark shade.
   Brightness alone does not predict this: yellow is bright but takes a pale partner. */
function partnerOf(color) {
  const hex = swatchHex(color).toUpperCase();
  if (SWATCH_MAP[color] || SWATCHES.some(([, h]) => h === hex)) {
    const named = SWATCHES.find(([, h]) => h === hex);
    if (named) return PARTNERS[named[0]];
  }
  const [r, g, b] = rgbOf(hex);
  let nearest = SWATCHES[0],
    best = Infinity;
  for (const entry of SWATCHES) {
    const [nr, ng, nb] = rgbOf(entry[1]);
    const d = (r - nr) ** 2 + (g - ng) ** 2 + (b - nb) ** 2;
    if (d < best) {
      best = d;
      nearest = entry;
    }
  }
  const darkPartner = lumOf(PARTNERS[nearest[0]]) < 0.5;
  const mix = darkPartner ? c => Math.round(c * 0.16) : c => Math.round(255 + (c - 255) * 0.12);
  return '#' + [r, g, b].map(v => mix(v).toString(16).padStart(2, '0')).join('').toUpperCase();
}
const lightFill = partnerOf;
const CREATE_MODE_BG = [1, 2, 3, 4, 5, 6, 7].map(i => `var(--cm-${i})`);
Object.assign(__ds_scope, { STYLES, STYLE_MAP, SWATCHES, SWATCH_MAP, swatchHex, PARTNERS, partnerOf, lightFill, CREATE_MODE_BG });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/story/story-styles.js", error: String((e && e.message) || e) }); }

// components/story/StoryText.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
let uid = 0;
const probeStyle = {
  display: 'inline-block',
  width: 0,
  height: '1cap',
  verticalAlign: 'baseline'
};
function StoryText({
  text = '',
  style = 'strong',
  color = 'white',
  background = 'off',
  align = 'center',
  size = 70,
  animation = 'none',
  effect = 'none',
  className,
  ...rest
}) {
  const s = __ds_scope.STYLE_MAP[style] || __ds_scope.STYLE_MAP.strong;
  const hex = __ds_scope.swatchHex(color);
  const partner = __ds_scope.partnerOf(hex);
  const id = React.useMemo(() => 'goo' + ++uid, []);
  const rootRef = React.useRef(null);
  const [m, setM] = React.useState(null);
  const lines = String(text).split('\n');
  const n = lines.length;
  const off = background === 'off';
  const block = s.family === 'block';
  let ink = hex,
    fill = 'transparent';
  if (background === 'light') {
    fill = partner;
    ink = hex;
  }
  if (background === 'solid') {
    fill = hex;
    ink = partner;
  }
  const items = align === 'left' ? 'flex-start' : align === 'right' ? 'flex-end' : 'center';
  const [pT, pB, pX] = s.pad;
  const est = {
    top: `${Math.max(0, pT - (s.lh - 1) / 2)}cap`,
    bot: `${Math.max(0, pB - (s.lh - 1) / 2)}cap`
  };
  const padTop = off ? 0 : m ? m.padTop + 'px' : est.top;
  const padBot = off ? 0 : m ? m.padBot + 'px' : est.bot;
  const padX = off ? 0 : `${pX}cap`;
  const lineH = m ? m.lineH : size * s.lh * 0.7;
  const pTpx = m ? m.padTop : size * 0.7 * Math.max(0, pT - (s.lh - 1) / 2);
  const pBpx = m ? m.padBot : size * 0.7 * Math.max(0, pB - (s.lh - 1) / 2);
  // Per-line family: blank lines split the text into separate shapes.
  const blank = lines.map(l => l.trim() === '');
  const firstOf = i => !block && (i === 0 || blank[i - 1]);
  const lastOf = i => !block && (i === n - 1 || blank[i + 1]);
  const groupLen = i => {
    let a = i,
      b = i;
    while (a > 0 && !blank[a - 1]) a--;
    while (b < n - 1 && !blank[b + 1]) b++;
    return b - a + 1;
  };
  const goo = !off && !block && s.shape !== 'square' && n > 1;
  const font = {
    fontFamily: `"${s.font}"`,
    fontWeight: s.weight,
    fontStyle: s.italic ? 'italic' : 'normal',
    fontSize: size + 'px',
    lineHeight: `${s.lh}cap`,
    letterSpacing: s.letterSpacing || 'normal',
    textTransform: s.uppercase ? 'uppercase' : 'none',
    whiteSpace: 'pre'
  };
  const col = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: items,
    margin: 0
  };
  const blockPad = block && !off ? {
    paddingTop: padTop,
    paddingBottom: padBot,
    paddingLeft: padX,
    paddingRight: padX
  } : {};
  const lineStyle = i => {
    if (block) return {
      ...font,
      display: 'block',
      textAlign: align
    };
    if (!off && blank[i]) return {
      ...font,
      display: 'block',
      height: `${Math.max(0, lineH - pTpx - pBpx)}px`,
      lineHeight: 0,
      overflow: 'hidden'
    };
    const st = {
      ...font,
      display: 'block',
      paddingLeft: padX,
      paddingRight: padX,
      paddingTop: firstOf(i) ? padTop : 0,
      paddingBottom: lastOf(i) ? padBot : 0,
      borderRadius: 0
    };
    if (off) return st;
    const gl = groupLen(i);
    const shapeH = lineH * gl + pTpx + pBpx;
    if (s.shape === 'pill') {
      const h = lineH + (firstOf(i) ? pTpx : 0) + (lastOf(i) ? pBpx : 0);
      st.borderRadius = `${(gl > 1 ? h : shapeH) / 2}px`;
    } else if (s.shape === 'rounded') {
      const rR = shapeH * 0.1;
      const c = m && m.corners[i] || {
        tl: firstOf(i),
        tr: firstOf(i),
        br: lastOf(i),
        bl: lastOf(i)
      };
      st.borderRadius = `${c.tl ? rR : 0}px ${c.tr ? rR : 0}px ${c.br ? rR : 0}px ${c.bl ? rR : 0}px`;
    }
    return st;
  };
  const probeIdx = blank.indexOf(false);
  const measure = React.useCallback(() => {
    const root = rootRef.current;
    if (!root) return;
    const probe = root.querySelector('[data-probe]');
    const els = Array.from(root.querySelectorAll('[data-line]'));
    if (!probe || !els.length) return;
    const k = root.getBoundingClientRect().width / (root.offsetWidth || 1) || 1;
    const pr = probe.getBoundingClientRect();
    const cap = pr.height / k;
    if (!cap) return;
    const pl = probe.parentElement;
    const r0 = pl.getBoundingClientRect();
    const cs0 = getComputedStyle(pl);
    const curTop = parseFloat(cs0.paddingTop) || 0,
      curBot = parseFloat(cs0.paddingBottom) || 0;
    const lh = r0.height / k - curTop - curBot;
    const A = pr.top / k - (r0.top / k + curTop);
    const B = lh - A - cap;
    const nt = Math.max(0, pT * cap - A),
      nb = Math.max(0, pB * cap - B);
    const rects = els.map(e => e.getBoundingClientRect());
    const e = 1;
    const corners = rects.map((r, i) => {
      const p = i > 0 && !blank[i - 1] ? rects[i - 1] : null,
        q = i < n - 1 && !blank[i + 1] ? rects[i + 1] : null;
      return {
        tl: !p || p.left > r.left + e,
        tr: !p || p.right < r.right - e,
        br: !q || q.right < r.right - e,
        bl: !q || q.left > r.left + e
      };
    });
    setM(prev => prev && Math.abs(prev.padTop - nt) < .5 && Math.abs(prev.padBot - nb) < .5 && Math.abs(prev.lineH - lh) < .5 && JSON.stringify(prev.corners) === JSON.stringify(corners) ? prev : {
      padTop: nt,
      padBot: nb,
      lineH: lh,
      corners
    });
  }, [n, pT, pB, blank.join('')]);
  React.useLayoutEffect(() => {
    measure();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
  }, [measure, text, style, size, background, align, m && m.padTop]);
  const isPixel = effect === 'pixel';
  const perChar = animation !== 'none' || isPixel;
  const pixelStyle = isPixel ? pixelShadow(size, ink, off) : {};
  let ci = 0;
  const renderChars = ln => Array.from(ln).map((ch, i) => {
    const k = ci++;
    const st = {
      display: 'inline-block',
      whiteSpace: 'pre',
      ...pixelStyle
    };
    if (animation === 'typewriter') {
      st.opacity = 0;
      st.animation = `igs-type 1ms steps(1) ${k * 60}ms forwards`;
    }
    if (animation === 'pop') {
      st.opacity = 0;
      st.animation = `igs-pop 260ms cubic-bezier(.2,.9,.3,1.3) ${k * 70}ms forwards`;
    }
    if (animation === 'jump') {
      st.opacity = 0;
      st.animation = `igs-jump 520ms cubic-bezier(.3,1.4,.5,1) ${k * 55}ms forwards`;
    }
    return /*#__PURE__*/React.createElement("span", {
      key: i,
      style: st
    }, ch);
  });
  const content = (ln, i) => !off && blank[i] && !block ? null : perChar ? renderChars(ln || ' ') : ln || ' ';
  return /*#__PURE__*/React.createElement("div", _extends({
    className: className,
    style: {
      position: 'relative',
      display: 'flex',
      justifyContent: items,
      width: '100%'
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    ref: rootRef,
    style: {
      position: 'relative',
      display: 'inline-block'
    }
  }, !off && /*#__PURE__*/React.createElement("div", {
    "aria-hidden": true,
    style: {
      ...col,
      ...blockPad,
      position: 'absolute',
      inset: 0,
      background: block ? fill : 'transparent',
      filter: goo ? `url(#${id})` : 'none'
    }
  }, lines.map((ln, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      ...lineStyle(i),
      background: block || blank[i] ? 'transparent' : fill,
      color: 'transparent'
    }
  }, blank[i] && !block ? null : ln || ' '))), /*#__PURE__*/React.createElement("div", {
    style: {
      ...col,
      ...blockPad,
      position: 'relative'
    },
    className: effect === 'none' ? undefined : 'igs-fx-' + effect
  }, lines.map((ln, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    "data-line": "",
    style: {
      ...lineStyle(i),
      color: ink
    }
  }, i === probeIdx && /*#__PURE__*/React.createElement("span", {
    "data-probe": "",
    style: probeStyle
  }), content(ln, i)))), goo && /*#__PURE__*/React.createElement("svg", {
    width: "0",
    height: "0",
    style: {
      position: 'absolute'
    },
    "aria-hidden": true
  }, /*#__PURE__*/React.createElement("filter", {
    id: id,
    x: "-20%",
    y: "-20%",
    width: "140%",
    height: "140%"
  }, /*#__PURE__*/React.createElement("feGaussianBlur", {
    in: "SourceGraphic",
    stdDeviation: 10 * size / 70,
    result: "b"
  }), /*#__PURE__*/React.createElement("feColorMatrix", {
    in: "b",
    mode: "matrix",
    values: "1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 19 -9",
    result: "g"
  }), /*#__PURE__*/React.createElement("feComposite", {
    in: "SourceGraphic",
    in2: "g",
    operator: "atop"
  }))), effect === 'sparkle' && /*#__PURE__*/React.createElement(Sparkles, {
    size: size
  })), /*#__PURE__*/React.createElement(StoryTextKeyframes, null));
}

/* Pixel: hard-edged near-black outline (8-direction text-shadow, no blur) + stepped down-right shadow. Off mode adds a top-light tint. */
function pixelShadow(size, ink, off) {
  const o = Math.max(1, Math.round(size / 35));
  const ring = [[o, 0], [-o, 0], [0, o], [0, -o], [o, o], [-o, o], [o, -o], [-o, -o]].map(([x, y]) => `${x}px ${y}px 0 #101010`);
  const steps = [];
  for (let i = 1; i <= Math.max(2, Math.round(size / 18)); i++) steps.push(`${i * o}px ${i * o}px 0 #101010`);
  return {
    textShadow: [...ring, ...steps].join(','),
    ...(off ? {
      backgroundImage: `linear-gradient(#FFFFFF 0%, ${ink} 85%)`,
      WebkitBackgroundClip: 'text',
      color: 'transparent',
      textShadow: 'none',
      filter: `drop-shadow(${o}px ${o}px 0 #101010) drop-shadow(${o}px ${o}px 0 #101010) drop-shadow(-${o}px 0 0 #101010) drop-shadow(0 -${o}px 0 #101010)`
    } : {})
  };
}

/* Sparkle: small 4-point glints on single letters, one larger soft starburst near the top-left; repeats every 2s. */
function Sparkles({
  size = 70
}) {
  const star = (x, y, w, delay, color = '#fff') => /*#__PURE__*/React.createElement("span", {
    key: x + y,
    style: {
      position: 'absolute',
      left: x,
      top: y,
      width: w,
      height: w,
      marginLeft: -w / 2,
      marginTop: -w / 2,
      color,
      animation: `igs-glint 2000ms ${delay}ms ease-in-out infinite`,
      opacity: 0,
      filter: 'drop-shadow(0 0 2px rgba(255,255,255,.9))'
    }
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: w,
    height: w,
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("path", {
    fill: "currentColor",
    d: "M12 0 L13.4 10.6 L24 12 L13.4 13.4 L12 24 L10.6 13.4 L0 12 L10.6 10.6 Z"
  })));
  const big = size * 1.1;
  return /*#__PURE__*/React.createElement("div", {
    "aria-hidden": true,
    style: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      zIndex: 2
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      left: '8%',
      top: '14%',
      width: big,
      height: big,
      marginLeft: -big / 2,
      marginTop: -big / 2,
      animation: 'igs-flare 2000ms 200ms ease-in-out infinite',
      opacity: 0,
      filter: `blur(${size / 60}px)`
    }
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: big,
    height: big,
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("path", {
    fill: "#fff",
    d: "M12 0 L13 11 L24 12 L13 13 L12 24 L11 13 L0 12 L11 11 Z"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: "12",
    cy: "12",
    r: "2.2",
    fill: "#fff"
  }))), star('30%', '40%', size * 0.34, 0), star('47%', '28%', size * 0.22, 600, '#F5E6B5'), star('66%', '62%', size * 0.26, 1000), star('86%', '36%', size * 0.2, 1400, '#F5E6B5'));
}
function StoryTextKeyframes() {
  return /*#__PURE__*/React.createElement("style", null, `
@keyframes igs-type{to{opacity:1}}
@keyframes igs-pop{0%{opacity:0;transform:scale(.1)}60%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:scale(1)}}
@keyframes igs-jump{0%{opacity:0;transform:translateY(1.4em) rotate(-6deg)}45%{opacity:1;transform:translateY(-.35em) rotate(4deg)}100%{opacity:1;transform:translateY(0) rotate(0)}}
@keyframes igs-glint{0%,20%{opacity:0;transform:scale(.3) rotate(0)}32%{opacity:1;transform:scale(1) rotate(15deg)}50%{opacity:0;transform:scale(.4) rotate(30deg)}100%{opacity:0}}
@keyframes igs-flare{0%,10%{opacity:0;transform:scale(.4)}30%{opacity:.95;transform:scale(1)}60%{opacity:0;transform:scale(1.15)}100%{opacity:0}}
@keyframes igs-neon{0%,100%{text-shadow:0 0 .08em rgba(255,255,255,.35)}50%{text-shadow:0 0 .35em rgba(255,255,255,.95),0 0 .7em rgba(255,255,255,.6)}}
@keyframes igs-shimmer{0%{-webkit-mask-position:120% 0}100%{-webkit-mask-position:-20% 0}}
.igs-fx-neon{animation:igs-neon 2000ms ease-in-out infinite}
.igs-fx-sparkle{text-shadow:0 0 .1em rgba(255,255,255,.7),0 0 .25em rgba(255,255,255,.45)}
.igs-fx-shimmer{-webkit-mask-image:linear-gradient(90deg,#000 0%,#000 40%,rgba(0,0,0,.5) 50%,#000 60%,#000 100%);-webkit-mask-size:300% 100%;animation:igs-shimmer 1000ms linear infinite}
`);
}
Object.assign(__ds_scope, { StoryText });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/story/StoryText.jsx", error: String((e && e.message) || e) }); }

__ds_ns.StoryFrame = __ds_scope.StoryFrame;

__ds_ns.SafeZoneGuide = __ds_scope.SafeZoneGuide;

__ds_ns.StoryText = __ds_scope.StoryText;

__ds_ns.STYLES = __ds_scope.STYLES;

__ds_ns.STYLE_MAP = __ds_scope.STYLE_MAP;

__ds_ns.SWATCHES = __ds_scope.SWATCHES;

__ds_ns.SWATCH_MAP = __ds_scope.SWATCH_MAP;

__ds_ns.PARTNERS = __ds_scope.PARTNERS;

__ds_ns.CREATE_MODE_BG = __ds_scope.CREATE_MODE_BG;

})();
