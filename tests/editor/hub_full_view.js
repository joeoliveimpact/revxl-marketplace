// H14 browser proof. Runs inside the existing locked, owned-fixture browser harness.
"use strict";
module.exports = async (page, browser, job, options) => {
  const need = (ok, why) => { if (!ok) throw new Error(why); };
  const check = async (expression, why) => need(await page.evaluate(expression), why);
  const run = js => page.evaluate(js);
  const ready = () => page.waitForFunction("window.Hub && Hub.ready");
  const beatReady = () => page.waitForFunction("document.querySelector('#panel iframe')?.contentDocument?.querySelector('#board:not([hidden]) #needs')");
  const enter = async () => {
    await run("document.querySelector('#fullview').click()");
    await page.waitForFunction("document.body.dataset.boardview==='full'");
  };
  const exitReady = async () => {
    await page.waitForFunction("!document.body.dataset.boardview && !fullExit");
    await check("document.activeElement.id==='fullview' && document.querySelector('#fullview').getAttribute('aria-pressed')==='false'", "exit focus or pressed state");
  };
  const kept = () => check(`(() => {
    const f=document.querySelector('#panel iframe');
    return f===window.__frame && f.getAttribute('src')===window.__src &&
      f.contentWindow.__keep==='x' && f.contentDocument.querySelector('#needs').value==='H14 unsent draft';
  })()`, "iframe, document or unsent draft changed");
  const pages = (await browser.pages()).length;
  await page.evaluateOnNewDocument(() => {
    window.__opened = 0;
    window.open = () => { window.__opened++; };
  });
  await page.evaluate(() => {
    window.__opened = 0;
    window.open = () => { window.__opened++; };
  });
  await run(`document.querySelector('#tab-beat-map').click()`);
  await beatReady();
  await run(`(() => {
    window.__frame=document.querySelector('#panel iframe'); window.__src=__frame.getAttribute('src');
    window.__history=history.length;
    document.querySelector('#boards').scrollIntoView(); window.scrollBy(0,-80);
    window.__scroll=[scrollX,scrollY];
    const w=__frame.contentWindow, field=w.document.querySelector('#needs');
    w.__keep='x'; field.value='H14 unsent draft'; field.dispatchEvent(new Event('input',{bubbles:true}));
    document.querySelector('#fullview').click();
  })()`);
  await check(`(() => {
    const f=document.querySelector('#panel iframe'), r=f.getBoundingClientRect(), bar=document.querySelector('#fullbar');
    const steps=[...document.querySelectorAll('#fullsteps button')];
    return document.body.dataset.boardview==='full' && !bar.hidden &&
      Math.abs(r.left)<2 && Math.abs(r.width-innerWidth)<=2 &&
      Math.abs(r.top-bar.getBoundingClientRect().bottom)<=2 && Math.abs(r.bottom-innerHeight)<=2 &&
      document.querySelector('#fullreel').textContent===current().title &&
      document.querySelector('#fullboard').textContent==='Beat Map' &&
      steps.length===DATA.stages.length && steps.filter(b=>b.getAttribute('aria-current')==='step').length===1 &&
      steps.every((b,i)=>b.textContent.includes(String(i+1)) && b.getAttribute('aria-label')===
        'Step '+(i+1)+' of '+DATA.stages.length+': '+DATA.stages[i].name+', '+(i===current().cur?'current':current().done[i]?'done':'to do')) &&
      ['.rail','.side','#tabs'].every(s=>document.querySelector(s).inert) &&
      document.documentElement.scrollWidth<=innerWidth && document.activeElement.id==='fullback' &&
      document.querySelector('#fullview').getAttribute('aria-pressed')==='true';
  })()`, "Full view bounds, bar, inert regions, steps or focus");
  await kept();
  await check(`document.body.dataset.layout===${JSON.stringify(options.layout)} && BoardClient.controls.mode()===${JSON.stringify(options.controls)}`, "Full view changed the layout or controls mode");
  await run("document.querySelector('#fullback').click()");
  await exitReady();
  await check("__scroll[1]>0 && scrollX===__scroll[0] && scrollY===__scroll[1] && !document.querySelector('[data-full-hidden]') && ['.rail','.side','#tabs'].every(s=>!document.querySelector(s).inert)", "exit did not restore scroll or inert regions");
  await kept();
  for (const via of ["hub", "frame", "back"]) {
    await enter();
    if (via === "hub") await run("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))");
    if (via === "frame") {
      // Dialog Escape and an already-consumed Escape belong to the board.
      await run(`(() => {
        const d=__frame.contentDocument, dialog=d.createElement('dialog'), field=d.createElement('input');
        dialog.append(field); d.body.append(dialog); dialog.showModal(); field.focus();
        field.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
        dialog.close(); dialog.remove();
        const e=new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}); e.preventDefault(); d.dispatchEvent(e);
      })()`);
      await check("document.body.dataset.boardview==='full'", "dialog or consumed Escape left Full view");
      await run("__frame.contentDocument.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))");
    }
    if (via === "back") await run("history.back()");
    await exitReady(); await kept();
    await check("scrollY===__scroll[1] && history.length===__history+1 && location.pathname==='/editor/hub/' && !new URL(location).searchParams.has('view')", "history grew across cycles or hub/scroll was lost");
  }
  if (options.coreOnly) return;
  await enter();
  // Reload control and the actual 15 second timer must keep the frame and field focus.
  await run("__frame.contentDocument.querySelector('#needs').focus(); document.querySelector('#reload').click()");
  await page.waitForNetworkIdle({idleTime:100});
  await kept();
  await check("document.body.dataset.boardview==='full' && __frame.contentDocument.activeElement.id==='needs'", "Reload stole focus or Full view");
  await page.waitForResponse(r => r.url().endsWith('/editor/hub/hub-data.json'), {timeout:17000});
  await page.waitForNetworkIdle({idleTime:100});
  await kept();
  await check("document.body.dataset.boardview==='full' && __frame.contentDocument.activeElement.id==='needs'", "timer stole focus or Full view");
  await run("document.querySelector('#fullsteps button[data-step=\"1\"]').click()");
  await check("TAB==='cut-board' && document.body.dataset.boardview==='full'", "built step did not switch inside Full view");
  await run("document.querySelector('#fullback').click()"); await exitReady();
  await enter();
  await run(`openBoard(${JSON.stringify(options.unbuilt)})`);
  await page.waitForFunction("!document.body.dataset.boardview && !fullExit");
  await check("!document.querySelector('.rail').inert && document.querySelector('#fullview').hidden", "unavailable board did not leave Full view");
  await run("openBoard('beat-map')"); await beatReady(); await enter();
  await run("selectReel('reel-02')");
  await check("CUR==='reel-02' && !document.body.dataset.boardview && !TAB && !document.querySelector('.side').inert", "reel switch did not leave Full view");

  await page.goto(job.base+'/editor/hub/?reel=reel-01&board=beat-map&view=full'); await ready(); await beatReady();
  await check("TAB==='beat-map' && document.body.dataset.boardview==='full'", "address did not open Full view");
  await page.reload(); await ready(); await beatReady();
  await check("TAB==='beat-map' && document.body.dataset.boardview==='full' && new URL(location).searchParams.get('view')==='full'", "reload lost address options");
  await run(`(() => {
    window.__hubKeep='x'; window.__frame=document.querySelector('#panel iframe'); window.__src=__frame.getAttribute('src');
    __frame.contentWindow.__keep='x';
    const field=__frame.contentDocument.querySelector('#needs');
    field.value='H14 unsent draft'; field.dispatchEvent(new Event('input',{bubbles:true}));
    history.back();
  })()`);
  await exitReady(); await kept();
  await check("window.__hubKeep==='x' && TAB==='beat-map' && location.pathname==='/editor/hub/' && new URL(location).searchParams.get('reel')==='reel-01' && new URL(location).searchParams.get('board')==='beat-map' && !new URL(location).searchParams.has('view')", "direct Full view Back lost the hub document or address");
  await enter();
  await run("__frame.contentDocument.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))");
  await exitReady(); await kept();
  await enter();
  await run("new Promise(resolve => { __frame.addEventListener('load',resolve,{once:true}); __frame.contentWindow.location.reload(); })");
  await beatReady();
  await run("document.querySelector('#panel iframe').contentDocument.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))");
  await exitReady();
  await page.goto(job.base+'/editor/hub/?reel=reel-01&board=review&view=full'); await ready();
  await run("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))"); await exitReady();
  for (const board of ['nope', options.unbuilt]) {
    await page.goto(job.base+'/editor/hub/?reel=reel-01&board='+board+'&view=full'); await ready();
    await check("!TAB && !document.body.dataset.boardview && document.querySelector('#status').textContent===\"That board isn't ready yet, so the hub opened instead.\"", "invalid board address was not ignored");
  }

  // Advance the fixture using the real stage builder while this browser stays open.
  const fs = require('fs'), cp = require('child_process');
  const refresh = changes => {
    for (const [path, value] of changes) {
      if (value === null) { if (fs.existsSync(path)) fs.unlinkSync(path); }
      else fs.writeFileSync(path, JSON.stringify(value)+'\n');
    }
    cp.execFileSync(options.python, ['-X','utf8','-I','-B',options.rows,'--root',options.root]);
  };
  const cuts=options.reel+'/work/cuts.json';
  refresh([[cuts,null]]);
  await page.goto(job.base+'/editor/hub/?reel=reel-01&board=cut-board'); await ready();
  await enter();
  refresh([[cuts,{segments:[{out_out_f:24}]}]]);
  await run("load()");
  await check("TAB==='tweak-board' && document.body.dataset.boardview==='full' && document.querySelector('#status').textContent==='Moved to Tweak Board for the next step.'", "step follow did not open next board in Full view");
  await check(`(() => {
    const s=document.querySelector('#status'), r=s.getBoundingClientRect();
    const visible=el => { const css=getComputedStyle(el); return !el.inert && !el.hidden && css.display!=='none' && css.visibility==='visible' && +css.opacity>0; };
    let el=s;
    while (el) { if (!visible(el)) return false; el=el.parentElement; }
    return r.width>0 && r.height>0 && r.left>=0 && r.right<=innerWidth &&
      r.top>=document.querySelector('#fullbar').getBoundingClientRect().bottom && r.bottom<=innerHeight &&
      s.contains(document.elementFromPoint(r.left+r.width/2,r.top+r.height/2));
  })()`, "Full view step-follow message is inert, hidden or outside the viewport");
  await run("document.querySelector('#fullback').click()"); await exitReady();
  refresh([[cuts,null]]);
  await run("openBoard('beat-map'); load()"); await beatReady();
  await run("document.querySelector('#status').textContent=''; window.__other=document.querySelector('#panel iframe')");
  refresh([[cuts,{segments:[{out_out_f:24}]}]]);
  await run("load()");
  await check("TAB==='beat-map' && document.querySelector('#panel iframe')===__other && !document.querySelector('#status').textContent", "step follow switched another tab or announced it");
  // A focused field on the previous stage's board also prevents following.
  refresh([[cuts,null]]); await run("load();");
  await run("openBoard('cut-board')");
  await page.waitForFunction("document.querySelector('#panel iframe')?.contentWindow.location.pathname==='/editor/cut-board/' && document.querySelector('#panel iframe').contentDocument.readyState==='complete'");
  await run("const f=document.querySelector('#panel iframe').contentDocument; const input=f.createElement('input'); f.body.append(input); input.focus(); document.querySelector('#status').textContent=''");
  refresh([[cuts,{segments:[{out_out_f:24}]}]]); await run("load()");
  await check("TAB==='cut-board' && !document.querySelector('#status').textContent", "step follow discarded a focused field");
  refresh([[cuts,null]]); await run("load()");
  await run("window.__focusedFrame=document.querySelector('#panel iframe'); const button=__focusedFrame.contentDocument.createElement('button'); button.textContent='Keep working'; __focusedFrame.contentDocument.body.append(button); button.focus()");
  await check("document.activeElement===__focusedFrame && __focusedFrame.contentDocument.activeElement.tagName==='BUTTON'", "board button did not receive focus");
  refresh([[cuts,{segments:[{out_out_f:24}]}]]); await run("load()");
  await check("TAB==='cut-board' && document.querySelector('#panel iframe')===__focusedFrame && !document.querySelector('#status').textContent", "step follow discarded a focused board button");
  refresh([[cuts,null]]); await run("load()");
  await run("document.querySelector('#fullview').focus()");
  refresh([[cuts,{segments:[{out_out_f:24}]}]]); await run("load()");
  await check("TAB==='tweak-board' && document.querySelector('#status').textContent==='Moved to Tweak Board for the next step.'", "step follow ignored the previous board with focus in the hub");
  refresh([[cuts,null]]);
  await page.goto(job.base+'/editor/hub/?reel=reel-01'); await ready();
  refresh([[cuts,{segments:[{out_out_f:24}]}]]); await run("load()");
  await check("TAB==='tweak-board' && document.querySelector('#status').textContent==='Moved to Tweak Board for the next step.'", "step follow ignored an empty panel");

  await run("openBoard('review')");
  await page.waitForFunction("document.querySelector('#panel iframe')?.contentWindow.ReviewReady");
  const review = await (await page.$('#panel iframe')).contentFrame();
  await review.waitForFunction("document.querySelector('#master').readyState>=1");
  await review.evaluate(async () => {
    window.__video=document.querySelector('#master');
    const seeked=new Promise(r=>__video.addEventListener('seeked',r,{once:true}));
    __video.currentTime=0.75; await seeked;
  });
  await enter(); await run("document.querySelector('#fullback').click()"); await exitReady();
  need(await review.evaluate(() => document.querySelector('#master')===window.__video && Math.abs(__video.currentTime-0.75)<=0.5), "Master review video reset");
  // A real playing video remains playing across both toggles.
  await review.evaluate(() => { __video.muted=true; return __video.play(); });
  await enter(); await check("!document.querySelector('#panel iframe').contentDocument.querySelector('#master').paused", "Full view paused review");
  await run("document.querySelector('#fullback').click()"); await exitReady();
  need(await review.evaluate(() => !__video.paused), "exit paused review");
  // Exercise every board-section and bar control with page-count proof, including unavailable tabs.
  await run(`(() => {
    for (const el of document.querySelectorAll('#boards button,#boards [role=tab]')) el.click();
  })()`);
  await run("openBoard('review')");
  await enter();
  await run("for (const el of document.querySelectorAll('#fullsteps button:not(:disabled)')) el.click()");
  await run("document.querySelector('#fullback').click()"); await exitReady();
  need((await browser.pages()).length===pages, "hub control created another page");
  await check("!window.__opened", "hub control opened another window");
};
