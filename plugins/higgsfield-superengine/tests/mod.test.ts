import { test, expect, mock } from 'claude-code/testing'

// E1 engine smoke: the mod's hooks run in the real engine, every $ call it makes answered by a stub beneath it.
test('E1: a Bash submit with no picked cap asks once; $10 sets this chat cap and the call goes on', async ($, on) => {
  const runs: string[] = []
  let capSet = false, asked = 0, reached = false
  mock.clock(on, { now: Date.UTC(2026, 9, 6, 12) })
  // a call on $ is answered { value } (OpEventResult)
  on('session.root', async () => ({ value: 'C:/ws' }))
  on('session.id', async () => ({ value: 'sid-e1' }))
  on('fs.read', async ($, e) => {
    // the engine hands Windows paths over with backslashes
    if (e.path.replace(/\\/g, '/') === 'C:/ws/higgsfield/.python') return { value: 'C:/Py312/python.exe\n' }
    throw new Error('ENOENT: ' + e.path)
  })
  on('process.run', async ($, e) => {
    runs.push(e.argv.join(' '))
    if (e.argv.includes('session-cap')) capSet = true
    return { value: { exitCode: 0, stderr: '',
      stdout: JSON.stringify({ ok: true, session_cap_set: capSet, session_cap: capSet ? 10 : 5, session_entries: [] }) } }
  })
  on('ui.invalidate', async () => ({ value: undefined }))
  on('ui.log', async () => ({ value: undefined }))
  on('ui.toast', async () => ({ value: undefined }))
  const notes: string[] = []
  on('session.append', async ($, e, next) => {
    if (e.door === 'note') notes.push(e.message.content.map((b: any) => b.text).join(''))
    return next(e)
  })
  on('tool.call', { tool: 'AskUserQuestion' }, async ($, e) => {
    asked++
    return { result: { questions: e.questions, answers: { [e.questions[0]!.question]: '$10' } } }
  })
  on('tool.call', { tool: 'Bash' }, async () => {
    reached = true
    return { result: { stdout: 'submitted', stderr: '', interrupted: false } }
  })

  const r = await $.tool.call({ tool: 'Bash', command: 'py "C:/p/scripts/hf_rest.py" submit z-image/turbo body.json' })

  expect(asked).toBe(1)
  expect(runs.some(a => a.endsWith('/scripts/ledger.py session-cap set sid-e1 10.00'))).toBe(true)
  expect(reached).toBe(true)
  expect(r.deny).toBeUndefined()
  expect(notes).toEqual(['Higgsfield session cap set to $10.00 by the client.'])   // the model is told
})
