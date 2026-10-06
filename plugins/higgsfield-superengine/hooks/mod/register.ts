import type { Register } from 'claude-code'
import { SUBMIT_RE, capFromAnswer, meterColor, dotGroup, parseJson, jobsFromLog, hhmm, submitStep, type Job } from './logic'

const PANE = 'hf-details'
const ASK = 'Higgsfield: how much can Claude spend in this session without asking you each time?'
const NOT_NOW = 'The client chose not to set a Higgsfield spending cap for this session yet, so nothing was sent. ' +
  'Ask them before trying again; the cap box will appear again with the next paid job.'
const BALANCE_ASK = 'What balance does your Higgsfield console show (Billing page)? Type the dollar amount under Other.'
const MEDIA = /\.(png|jpe?g|webp|gif|mp4|mov|webm)$/i

let st: any = null        // last `ledger.py status --session` result
let err = ''              // why the ledger could not be read ('' = fine)
let used = false          // this session touched Higgsfield: show the band
let jobs: Job[] = []
let asking: Promise<string | undefined> | null = null   // one box for parallel submits ("3 variations")

async function root($: any): Promise<string> { return await $.session.root() }

async function ledgerRun($: any, args: string[]): Promise<any> {
  let py = ''
  try { py = (await $.fs.read((await root($)) + '/higgsfield/.python')).trim() } catch { /* setup not done */ }
  if (!py) throw new Error('Higgsfield setup is not finished in this folder')
  const r = await $.process.run([py, '-B', $.plugin.root + '/scripts/ledger.py', ...args], { timeoutMs: 20000 })
  const o = parseJson(r.stdout)
  if (!o) throw new Error('the spend record gave no answer')
  return o
}

async function readLogs($: any): Promise<string[]> {
  const now = new Date(await $.clock.now()), lines: string[] = []
  for (const back of [1, 0]) {
    const d = new Date(now.getTime() - back * 86400000)
    const day = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    try { lines.push(...(await $.fs.read(`${await root($)}/higgsfield/${day}/log.jsonl`)).split(/\r?\n/)) } catch { /* none */ }
  }
  return lines
}

async function refresh($: any) {
  try {
    st = await ledgerRun($, ['status', '--session', await $.session.id()])
    err = st.ok === false ? String(st.message || 'the spend record could not be read') : ''
    if (!err) jobs = jobsFromLog(await readLogs($), st.session_entries ?? [])
  } catch (x) { err = String((x as Error).message || x) || 'the spend record could not be read' }
  $.ui.invalidate('ui.render')
}

/** The figures the client sees: the chat's picked cap, else the 24 h limit (same rule as the guard and the quote). */
function figures(s: any) {
  const picked = !!s?.session_cap_set
  const spent = Number((picked ? s?.session_spent : s?.spent_24h) ?? 0)
  const cap = Number((picked ? s?.session_cap : s?.cap_usd) ?? 5)
  const left = Number((picked ? s?.session_headroom : s?.headroom_usd) ?? Math.max(cap - spent, 0))
  return { picked, spent, cap, left, ratio: Math.min(spent / cap, 1) }
}

async function capAnswer($: any): Promise<string | undefined> {
  if (!asking) asking = $.ui.ask(ASK, { header: 'Session cap', options: ['$5', '$10', '$20', 'Not now'] })
    .catch(() => undefined).finally(() => { asking = null })
  return asking
}

async function setCap($: any, usd: number): Promise<boolean> {
  try {
    const o = await ledgerRun($, ['session-cap', 'set', await $.session.id(), String(usd)])
    if (o.ok === false) throw new Error(o.message)
  } catch {
    return false
  }
  $.ui.log(`Higgsfield session cap set to $${usd.toFixed(2)} by the client.`)
  await refresh($)
  return true
}

async function pressCap($: any, usd: number) {
  if (!(await setCap($, usd))) $.ui.toast("Couldn't save the cap, try again")
}

async function openDetails($: any) {
  await $.ui.open({ id: PANE, title: 'Higgsfield', focus: true, closeOnEscape: true })
  await refresh($)
}

/** Job files are relative to the session root, or absolute; only media files inside the session root open. */
async function openFile($: any, file: string) {
  const r = await root($)
  const abs = /^([A-Za-z]:)?[\\/]/.test(file) ? file : r + '/' + file.replace(/\\/g, '/')
  const real = (await $.fs.stat(abs, { resolve: true }).catch(() => undefined))?.realPath
  const base = (await $.fs.stat(r, { resolve: true }).catch(() => undefined))?.realPath?.replace(/[\\/]$/, '')
  const inside = !!real && !!base && real.startsWith(base) && /[\\/]/.test(real.charAt(base.length))
  if (!inside || !MEDIA.test(real!)) return void $.ui.toast('Only Higgsfield images and videos in this folder open from here.')
  try { await $.process.run(/^[A-Za-z]:/.test(real!) ? ['explorer.exe', real!] : ['open', real!]) }
  catch { $.ui.toast("Couldn't open the file.") }
}

async function openBilling($: any) {   // a fixed URL, never data from the log
  const url = 'https://open.higgsfield.ai/dashboard'
  try { await $.process.run(/^[A-Za-z]:/.test(await root($)) ? ['explorer.exe', url] : ['open', url]) }
  catch { $.ui.toast("Couldn't open the browser.") }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => next(e))

  // Cap box before the first paid job of the session; refresh after anything that touches Higgsfield.
  on('tool.call', { tool: ['Bash', 'PowerShell'], command: /higgsfield|hf_rest|ledger\.py/i }, async ($, e, next) => {
    const cmd = String((e as any).command ?? '')
    used = true
    if (SUBMIT_RE.test(cmd)) {
      await refresh($)
      if (err) $.ui.toast('Higgsfield spend record unavailable: the 24 h limit applies.')
      const answer = !err && st && !st.session_cap_set ? await capAnswer($) : undefined
      const step = submitStep(st, err, answer)
      if (step.kind === 'refuse') return { deny: NOT_NOW }
      if (step.kind === 'set' && !(await setCap($, step.usd))) $.ui.toast("Couldn't save the cap: the 24 h limit applies.")
      await refresh($)   // the second of two parallel submits sees the cap the first one set
    }
    const r = await next(e)   // the permission check (guard + Allow box) and the tool run here
    await refresh($)
    return r
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if ((e as any).props?.hasSurvey || !(used || st?.session_cap_set)) return next(e)
    const { Box, Text, Button, Svg }: any = $.ui.resolve(e)
    if (err) return Box({ children: [Text({ dimColor: true, children: ['Higgsfield: spend record unavailable (' + err + ')'] })] })
    const { picked, spent, cap, left, ratio } = figures(st), color = meterColor(ratio), W = 180
    const bar = `<svg xmlns="http://www.w3.org/2000/svg" width="${W + 22}" height="16" viewBox="0 0 ${W + 22} 16">` +
      `<path d="M7 1 L8.6 6.4 L14 8 L8.6 9.6 L7 15 L5.4 9.6 L0 8 L5.4 6.4 Z" fill="${color}"/>` +
      dotGroup(20, 1, W, 14, ratio, color) + `</svg>`
    const words = picked ? `of $${cap.toFixed(2)} this session · $${left.toFixed(2)} left`
      : `of $${cap.toFixed(2)} (24 h limit) · you pick this chat's cap with the next paid job`
    const press = (label: string, usd: number) => Button({ key: label, label, onPress: () => void pressCap($, usd) })
    return Box({ flexDirection: 'row', columnGap: 1, children: [
      Svg ? Svg({ source: bar, alt: `Higgsfield: $${spent.toFixed(2)} ${words}`, width: W + 22, height: 16 })
          : Text({ children: ['higgsfield'] }),
      Text({ bold: true, children: ['$' + spent.toFixed(2)] }),
      Text({ dimColor: true, children: [words] }),
      press('+$5', cap + 5), press('×2', cap * 2), press('Back to $5', 5),
      Button({ key: 'details', label: 'Details', onPress: () => void openDetails($) }),
    ] })
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if ((e as any).requestId !== PANE) return next(e)
    const { Box, Text, Button, Svg }: any = $.ui.resolve(e)
    if (err || !st) return Text({ dimColor: true, children: ['Higgsfield: spend record unavailable. ' + err] })
    const { picked, spent, cap, left, ratio } = figures(st)
    const ageDays = st.balance_at ? Math.floor(((await $.clock.now()) / 1000 - st.balance_at) / 86400) : null
    const tile = (k: string, label: string, value: string, sub?: string) => Box({ key: k, flexDirection: 'column', flexGrow: 1,
      width: '33%', borderStyle: 'round', borderColor: '#3f3f46', paddingX: 1, children: [
        Text({ dimColor: true, children: [label] }), Text({ bold: true, children: [value] }),
        ...(sub ? [Text({ dimColor: true, children: [sub] })] : [])] })
    const meter = `<svg xmlns="http://www.w3.org/2000/svg" width="460" height="22" viewBox="0 0 460 22">` +
      dotGroup(0, 2, 460, 20, ratio, meterColor(ratio)) + `</svg>`
    const byModel: [string, number][] = []
    for (const j of jobs) { const f = byModel.find(m => m[0] === j.model); f ? (f[1] += j.cost) : byModel.push([j.model, j.cost]) }
    byModel.sort((a, b) => b[1] - a[1])
    const top = byModel.slice(0, 6)
    const max = Math.max(...top.map(m => m[1]), 0.01), RH = 22, CW = 300
    const chart = `<svg xmlns="http://www.w3.org/2000/svg" width="${CW}" height="${Math.max(top.length, 1) * RH}" ` +
      `font-family="system-ui,sans-serif" font-size="12">` + top.map(([m, v], i) =>
        `<text x="0" y="${i * RH + 14}" fill="#e4e4e7">${m}</text>` + dotGroup(100, i * RH + 5, 150, 9, v / max, '#22c55e', false) +
        `<text x="${CW}" y="${i * RH + 14}" fill="#a1a1aa" text-anchor="end">$${v.toFixed(2)}</text>`).join('') + `</svg>`
    const dot: any = { done: '#22c55e', running: '#f59e0b', refunded: '#9ca3af', charged: '#a1a1aa' }
    const cell = (k: string, w: string, ...children: any[]) => Box({ key: k, width: w, flexDirection: 'row', columnGap: 1, children })
    const statusDot = (s: string) => Svg ? [Svg({ source: `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" ` +
      `viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" fill="${dot[s] ?? '#a1a1aa'}"/></svg>`, alt: s, width: 10, height: 10 })] : []
    const updateBalance = async () => {
      let a: string | undefined
      try { a = await $.ui.ask(BALANCE_ASK, { header: 'Balance', options: ['Not now', 'Open Higgsfield'] }) } catch { return }
      if (a === 'Open Higgsfield') return void openBilling($)
      const usd = capFromAnswer(a?.replace(/,/g, '')) ?? (/^\s*\$?\s*\d+(\.\d+)?\s*$/.test(a ?? '') ? Number(a!.replace(/[$\s]/g, '')) : null)
      if (usd === null) return void (a && a !== 'Not now' && $.ui.toast('That did not look like a dollar amount; nothing changed.'))
      try { await ledgerRun($, ['balance', 'set', String(usd)]); $.ui.log(`Higgsfield balance recorded as $${usd} by the client.`) } catch { $.ui.toast("Couldn't save the balance.") }
      await refresh($)
    }
    return Box({ flexDirection: 'column', gap: 1, children: [
      Box({ key: 'tiles', flexDirection: 'row', columnGap: 1, children: [
        tile('t1', picked ? 'SPENT THIS SESSION' : 'SPENT, LAST 24 H', `$${spent.toFixed(2)}`),
        tile('t2', 'LEFT', `$${left.toFixed(2)}`, picked ? `of $${cap.toFixed(2)} session cap` : `of $${cap.toFixed(2)} (24 h limit)`),
        tile('t3', 'ACCOUNT', st.balance == null ? 'not set' : `≈ $${Number(st.balance).toFixed(2)}`,
             ageDays == null ? 'press Update balance' : ageDays === 0 ? 'updated today' : `updated ${ageDays} days ago`)] }),
      Svg ? Svg({ source: meter, alt: `${picked ? 'Session' : '24 h limit'} ${Math.round(ratio * 100)}% used`, width: 460, height: 22 }) : Text({ children: [''] }),
      Box({ key: 'meta', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', children: [
        Text({ dimColor: true, children: [`Last 24 h $${Number(st.spent_24h).toFixed(2)} · Last 7 days $${Number(st.spent_7d).toFixed(2)}`] }),
        Button({ key: 'upd', label: 'Update balance', onPress: () => void updateBalance() })] }),
      Text({ bold: true, children: ['Jobs this session'] }),
      Box({ key: 'jobs', flexDirection: 'column', children: jobs.length ? jobs.map((j, i) => Box({ key: 'j' + i, flexDirection: 'row', alignItems: 'center', children: [
        cell('t', '20%', Text({ dimColor: true, children: [hhmm(j.time)] })),
        cell('m', '36%', Text({ children: [`${j.model} · ${j.kind}`] })),
        cell('c', '14%', Text({ children: ['$' + j.cost.toFixed(2)] })),
        cell('s', '18%', ...statusDot(j.status), Text({ children: [j.status] })),
        cell('o', '12%', j.files.length ? Button({ key: 'open' + i, label: 'Open', onPress: () => void openFile($, j.files[0]!) }) : Text({ children: [''] }))] }))
        : [Text({ dimColor: true, children: ['No paid jobs in this session yet.'] })] }),
      Text({ bold: true, children: ['Spend by model'] }),
      top.length && Svg ? Svg({ source: chart, alt: top.map(([m, v]) => `${m} $${v.toFixed(2)}`).join(', '), width: CW, height: top.length * RH })
        : Text({ dimColor: true, children: ['Nothing yet.'] }),
    ] })
  })
}
