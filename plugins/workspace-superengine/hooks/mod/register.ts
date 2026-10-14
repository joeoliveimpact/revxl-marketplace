import type { EngineInterface, Register } from 'claude-code'
import { BUTTONS, MIN_VERSION, heartbeatPath, heartbeatRecord, lastText, parseHandoff, sectionText,
  versionAtLeast } from './logic'

// workspace-superengine mod (plan Step 4): the band (c e k w), the Workspace pane (/workspace), and the N6 heartbeat.
// Nothing here relies on session.end, reads session.start's surface or isInteractive, hooks telemetry, injects on
// prompt submit, calls Linear or starts a process. Every failure falls back to the plain hooks and skills.

type Api = EngineInterface
const PANE = 'wse-workspace'

/** The mod runs only on a Claude Code at least MIN_VERSION; older (or unreadable), the floor alone. */
async function active($: Api): Promise<boolean> {
  try {
    const v = await $.session.version()
    return versionAtLeast(v.base ?? v.version, MIN_VERSION)
  } catch { return false }
}

/** Puts `text` in the prompt box for the client to send. Never submits. */
async function fill($: Api, text: string) {
  const r = await $.prompt.fill({ text, mode: 'replace' }).catch(() => undefined)
  if (!r?.isFilled) $.ui.toast(`Couldn't fill the prompt box. Type ${text} instead.`)
}

async function openPane($: Api) {
  await $.ui.open({ id: PANE, title: 'Workspace', focus: true, closeOnEscape: true })
  $.ui.invalidate('ui.render')   // an already-open pane re-reads handoff.md
}

/** N6: one $.fs.write of the v1 record (Joe 10.14.26). hooks/session-start prunes the folder (older than 7 days). */
async function heartbeat($: Api) {
  const sid = await $.session.id()
  const path = heartbeatPath((await $.env.get('USERPROFILE')) || (await $.env.get('HOME')), sid)
  if (!path) return void $.ui.log('workspace-superengine heartbeat: skipped, no home folder or session id', { to: 'debug' })
  let version: unknown = null
  try { version = JSON.parse(await $.fs.read($.plugin.root + '/.claude-plugin/plugin.json')).version } catch { /* null */ }
  await $.fs.write(path, JSON.stringify(heartbeatRecord(version, sid, await $.clock.now())) + '\n')
  $.ui.log(`workspace-superengine heartbeat: wrote ${path}`, { to: 'debug' })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const r = await next(e)
    if (!(await active($))) {
      $.ui.log(`workspace-superengine: Claude Code older than ${MIN_VERSION}, mod off; plain hooks and skills only`,
        { to: 'debug' })
      return r
    }
    await $.command.register({ name: 'workspace', description: 'Open the Workspace pane: next actions, blockers, ' +
      'last session' }).catch(() => {})
    $.clock.after(0, () => void heartbeat($).catch(() => {}))   // silent on failure; never blocks or breaks the start
    return r
  })

  on('command.run', { command: 'workspace' }, async $ => {
    await openPane($)
    return { text: 'Workspace pane opened.' }
  })

  // Layout A (N6): our one row, then every band beneath ours below it. No plugin-name headline.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey || !(await active($))) return next(e)
    const { Box, Button } = $.ui.resolve(e)
    const row = Box({ key: 'wse-row', flexDirection: 'row', columnGap: 1, children: BUTTONS.map(b =>
      Button({ key: b.key, label: b.label, hotkey: b.hotkey, plain: true,
        onPress: () => void (b.fill ? fill($, b.fill) : openPane($)) })) })
    return Box({ flexDirection: 'column', children: [row, await next(e)] })
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button, Markdown } = $.ui.resolve(e)
    const file = (await $.session.root()) + '/handoff.md'
    let text: string | null = null, err = ''
    try { text = await $.fs.read(file) } catch (x) {
      if (await $.fs.exists(file).catch(() => false)) err = String((x as Error).message || x)
    }
    if (err) return Text({ children: [`handoff.md could not be read: ${err}`] })
    const h = parseHandoff(text)
    if (!h.exists) return Box({ flexDirection: 'column', children: [
      Text({ bold: true, children: ['No handoff yet'] }),
      Text({ children: ['This folder has no handoff.md. /super-setup sets the workspace up.'] }),
      Button({ key: 'wse-setup', label: 'Set up this workspace', onPress: () => void fill($, '/super-setup') })] })
    return Box({ flexDirection: 'column', children: [
      Text({ dimColor: true, children: [lastText(h)] }),
      Text({ bold: true, children: ['Next (P0)'] }),
      Markdown({ text: sectionText(h.p0, '## P0') }),
      Text({ bold: true, children: ['Blockers'] }),
      Markdown({ text: sectionText(h.blockers, '## Blockers') })] })
  })
}
