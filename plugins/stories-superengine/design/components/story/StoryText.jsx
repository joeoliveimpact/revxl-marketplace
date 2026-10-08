import React from 'react';
import { STYLE_MAP, swatchHex, partnerOf } from './story-styles.js';

let uid = 0;
const probeStyle = { display: 'inline-block', width: 0, height: '1cap', verticalAlign: 'baseline' };

export function StoryText({ text = '', style = 'strong', color = 'white', background = 'off', align = 'center', size = 70, animation = 'none', effect = 'none', className, ...rest }) {
  const s = STYLE_MAP[style] || STYLE_MAP.strong;
  const hex = swatchHex(color);
  const partner = partnerOf(hex);
  const id = React.useMemo(() => 'goo' + (++uid), []);
  const rootRef = React.useRef(null);
  const [m, setM] = React.useState(null);
  const lines = String(text).split('\n');
  const n = lines.length;
  const off = background === 'off';
  const block = s.family === 'block';
  let ink = hex, fill = 'transparent';
  if (background === 'light') { fill = partner; ink = hex; }
  if (background === 'solid') { fill = hex; ink = partner; }
  const items = align === 'left' ? 'flex-start' : align === 'right' ? 'flex-end' : 'center';
  const [pT, pB, pX] = s.pad;
  const est = { top: `${Math.max(0, pT - (s.lh - 1) / 2)}cap`, bot: `${Math.max(0, pB - (s.lh - 1) / 2)}cap` };
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
  const groupLen = i => { let a = i, b = i; while (a > 0 && !blank[a - 1]) a--; while (b < n - 1 && !blank[b + 1]) b++; return b - a + 1; };
  const goo = !off && !block && s.shape !== 'square' && n > 1;
  const font = { fontFamily: `"${s.font}"`, fontWeight: s.weight, fontStyle: s.italic ? 'italic' : 'normal', fontSize: size + 'px', lineHeight: `${s.lh}cap`, letterSpacing: s.letterSpacing || 'normal', textTransform: s.uppercase ? 'uppercase' : 'none', whiteSpace: 'pre' };
  const col = { display: 'flex', flexDirection: 'column', alignItems: items, margin: 0 };
  const blockPad = block && !off ? { paddingTop: padTop, paddingBottom: padBot, paddingLeft: padX, paddingRight: padX } : {};
  const lineStyle = (i) => {
    if (block) return { ...font, display: 'block', textAlign: align };
    if (!off && blank[i]) return { ...font, display: 'block', height: `${Math.max(0, lineH - pTpx - pBpx)}px`, lineHeight: 0, overflow: 'hidden' };
    const st = { ...font, display: 'block', paddingLeft: padX, paddingRight: padX, paddingTop: firstOf(i) ? padTop : 0, paddingBottom: lastOf(i) ? padBot : 0, borderRadius: 0 };
    if (off) return st;
    const gl = groupLen(i);
    const shapeH = lineH * gl + pTpx + pBpx;
    if (s.shape === 'pill') { const h = lineH + (firstOf(i) ? pTpx : 0) + (lastOf(i) ? pBpx : 0); st.borderRadius = `${(gl > 1 ? h : shapeH) / 2}px`; }
    else if (s.shape === 'rounded') {
      const rR = shapeH * 0.1;
      const c = (m && m.corners[i]) || { tl: firstOf(i), tr: firstOf(i), br: lastOf(i), bl: lastOf(i) };
      st.borderRadius = `${c.tl ? rR : 0}px ${c.tr ? rR : 0}px ${c.br ? rR : 0}px ${c.bl ? rR : 0}px`;
    }
    return st;
  };
  const probeIdx = blank.indexOf(false);
  const measure = React.useCallback(() => {
    const root = rootRef.current; if (!root) return;
    const probe = root.querySelector('[data-probe]');
    const els = Array.from(root.querySelectorAll('[data-line]'));
    if (!probe || !els.length) return;
    const k = root.getBoundingClientRect().width / (root.offsetWidth || 1) || 1;
    const pr = probe.getBoundingClientRect(); const cap = pr.height / k; if (!cap) return;
    const pl = probe.parentElement; const r0 = pl.getBoundingClientRect(); const cs0 = getComputedStyle(pl);
    const curTop = parseFloat(cs0.paddingTop) || 0, curBot = parseFloat(cs0.paddingBottom) || 0;
    const lh = r0.height / k - curTop - curBot;
    const A = pr.top / k - (r0.top / k + curTop);
    const B = lh - A - cap;
    const nt = Math.max(0, pT * cap - A), nb = Math.max(0, pB * cap - B);
    const rects = els.map(e => e.getBoundingClientRect());
    const e = 1;
    const corners = rects.map((r, i) => {
      const p = i > 0 && !blank[i - 1] ? rects[i - 1] : null, q = i < n - 1 && !blank[i + 1] ? rects[i + 1] : null;
      return { tl: !p || p.left > r.left + e, tr: !p || p.right < r.right - e, br: !q || q.right < r.right - e, bl: !q || q.left > r.left + e };
    });
    setM(prev => (prev && Math.abs(prev.padTop - nt) < .5 && Math.abs(prev.padBot - nb) < .5 && Math.abs(prev.lineH - lh) < .5 && JSON.stringify(prev.corners) === JSON.stringify(corners)) ? prev : { padTop: nt, padBot: nb, lineH: lh, corners });
  }, [n, pT, pB, blank.join('')]);
  React.useLayoutEffect(() => { measure(); if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure); }, [measure, text, style, size, background, align, m && m.padTop]);
  const isPixel = effect === 'pixel';
  const perChar = animation !== 'none' || isPixel;
  const pixelStyle = isPixel ? pixelShadow(size, ink, off) : {};
  let ci = 0;
  const renderChars = (ln) => Array.from(ln).map((ch, i) => {
    const k = ci++;
    const st = { display: 'inline-block', whiteSpace: 'pre', ...pixelStyle };
    if (animation === 'typewriter') { st.opacity = 0; st.animation = `igs-type 1ms steps(1) ${k * 60}ms forwards`; }
    if (animation === 'pop') { st.opacity = 0; st.animation = `igs-pop 260ms cubic-bezier(.2,.9,.3,1.3) ${k * 70}ms forwards`; }
    if (animation === 'jump') { st.opacity = 0; st.animation = `igs-jump 520ms cubic-bezier(.3,1.4,.5,1) ${k * 55}ms forwards`; }
    return <span key={i} style={st}>{ch}</span>;
  });
  const content = (ln, i) => (!off && blank[i] && !block) ? null : (perChar ? renderChars(ln || ' ') : (ln || ' '));
  return (
    <div className={className} style={{ position: 'relative', display: 'flex', justifyContent: items, width: '100%' }} {...rest}>
      <div ref={rootRef} style={{ position: 'relative', display: 'inline-block' }}>
        {!off && (
          <div aria-hidden style={{ ...col, ...blockPad, position: 'absolute', inset: 0, background: block ? fill : 'transparent', filter: goo ? `url(#${id})` : 'none' }}>
            {lines.map((ln, i) => <span key={i} style={{ ...lineStyle(i), background: block || blank[i] ? 'transparent' : fill, color: 'transparent' }}>{blank[i] && !block ? null : (ln || ' ')}</span>)}
          </div>
        )}
        <div style={{ ...col, ...blockPad, position: 'relative' }} className={effect === 'none' ? undefined : 'igs-fx-' + effect}>
          {lines.map((ln, i) => <span key={i} data-line="" style={{ ...lineStyle(i), color: ink }}>{i === probeIdx && <span data-probe="" style={probeStyle} />}{content(ln, i)}</span>)}
        </div>
        {goo && (
          <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden>
            <filter id={id} x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur in="SourceGraphic" stdDeviation={10 * size / 70} result="b" /><feColorMatrix in="b" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 19 -9" result="g" /><feComposite in="SourceGraphic" in2="g" operator="atop" /></filter>
          </svg>
        )}
        {effect === 'sparkle' && <Sparkles size={size} />}
      </div>
      <StoryTextKeyframes />
    </div>
  );
}

/* Pixel: hard-edged near-black outline (8-direction text-shadow, no blur) + stepped down-right shadow. Off mode adds a top-light tint. */
function pixelShadow(size, ink, off) {
  const o = Math.max(1, Math.round(size / 35));
  const ring = [[o, 0], [-o, 0], [0, o], [0, -o], [o, o], [-o, o], [o, -o], [-o, -o]].map(([x, y]) => `${x}px ${y}px 0 #101010`);
  const steps = [];
  for (let i = 1; i <= Math.max(2, Math.round(size / 18)); i++) steps.push(`${i * o}px ${i * o}px 0 #101010`);
  return {
    textShadow: [...ring, ...steps].join(','),
    ...(off ? { backgroundImage: `linear-gradient(#FFFFFF 0%, ${ink} 85%)`, WebkitBackgroundClip: 'text', color: 'transparent', textShadow: 'none', filter: `drop-shadow(${o}px ${o}px 0 #101010) drop-shadow(${o}px ${o}px 0 #101010) drop-shadow(-${o}px 0 0 #101010) drop-shadow(0 -${o}px 0 #101010)` } : {}),
  };
}

/* Sparkle: small 4-point glints on single letters, one larger soft starburst near the top-left; repeats every 2s. */
function Sparkles({ size = 70 }) {
  const star = (x, y, w, delay, color = '#fff') => (
    <span key={x + y} style={{ position: 'absolute', left: x, top: y, width: w, height: w, marginLeft: -w / 2, marginTop: -w / 2, color, animation: `igs-glint 2000ms ${delay}ms ease-in-out infinite`, opacity: 0, filter: 'drop-shadow(0 0 2px rgba(255,255,255,.9))' }}>
      <svg viewBox="0 0 24 24" width={w} height={w} style={{ display: 'block' }}><path fill="currentColor" d="M12 0 L13.4 10.6 L24 12 L13.4 13.4 L12 24 L10.6 13.4 L0 12 L10.6 10.6 Z" /></svg>
    </span>
  );
  const big = size * 1.1;
  return <div aria-hidden style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 2 }}>
    <span style={{ position: 'absolute', left: '8%', top: '14%', width: big, height: big, marginLeft: -big / 2, marginTop: -big / 2, animation: 'igs-flare 2000ms 200ms ease-in-out infinite', opacity: 0, filter: `blur(${size / 60}px)` }}>
      <svg viewBox="0 0 24 24" width={big} height={big} style={{ display: 'block' }}><path fill="#fff" d="M12 0 L13 11 L24 12 L13 13 L12 24 L11 13 L0 12 L11 11 Z" /><circle cx="12" cy="12" r="2.2" fill="#fff" /></svg>
    </span>
    {star('30%', '40%', size * 0.34, 0)}{star('47%', '28%', size * 0.22, 600, '#F5E6B5')}{star('66%', '62%', size * 0.26, 1000)}{star('86%', '36%', size * 0.2, 1400, '#F5E6B5')}
  </div>;
}

function StoryTextKeyframes() {
  return <style>{`
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
`}</style>;
}
