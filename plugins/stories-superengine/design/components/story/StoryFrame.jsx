import React from 'react';

/* 1080x1920 canvas. background: 'photo' | 'screenshot' | swatch hex | 'cm-1'..'cm-7'. */
export function StoryFrame({ background = '#000000', scale = 1, guides = false, children, style, ...rest }) {
  let bg = { background };
  let placeholder = null;
  if (background === 'photo' || background === 'screenshot') {
    bg = { background: background === 'photo' ? '#3A3F47' : '#F2F2F2' };
    placeholder = <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: background === 'photo' ? '#9AA1AA' : '#8E8E8E', fontFamily: '"Roboto Condensed"', fontSize: 40, letterSpacing: '0.1em', textTransform: 'uppercase', backgroundImage: background === 'photo' ? 'repeating-linear-gradient(45deg,transparent 0 40px,rgba(255,255,255,.04) 40px 80px)' : 'repeating-linear-gradient(0deg,transparent 0 120px,rgba(0,0,0,.06) 120px 121px)' }}>{background === 'photo' ? 'Photo' : 'Screenshot'}</div>;
  } else if (/^cm-[1-7]$/.test(background)) bg = { background: `var(--${background})` };
  return (
    <div style={{ width: 1080, height: 1920, position: 'relative', overflow: 'hidden', flex: 'none', transform: scale !== 1 ? `scale(${scale})` : undefined, transformOrigin: 'top left', ...bg, ...style }} {...rest}>
      {placeholder}
      <div style={{ position: 'absolute', left: 65, right: 65, top: 270, bottom: 384, display: 'flex', flexDirection: 'column' }}>{children}</div>
      {guides && <SafeZoneGuide />}
    </div>
  );
}

export function SafeZoneGuide() {
  const dash = '2px dashed rgba(255,255,255,.7)';
  const lbl = { position: 'absolute', fontFamily: '"Roboto Condensed"', fontSize: 28, color: '#fff', background: 'rgba(0,0,0,.55)', padding: '6px 12px' };
  return <div aria-hidden style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
    <div style={{ position: 'absolute', left: 65, right: 65, top: 270, bottom: 384, border: dash }} />
    <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: 270, background: 'rgba(0,0,0,.35)' }} />
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 384, background: 'rgba(0,0,0,.35)' }} />
    <div style={{ ...lbl, top: 24, left: 65 }}>270px · progress bar + profile header · guide, not exported</div>
    <div style={{ ...lbl, bottom: 24, left: 65 }}>384px · reply bar · guide, not exported</div>
    <div style={{ ...lbl, top: 290, left: 85 }}>safe area · 65px sides</div>
  </div>;
}
