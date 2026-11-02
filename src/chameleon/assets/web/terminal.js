'use strict';
let term, fit, bridge, promptMark = null, promptColumn = 0, atPrompt = false, promptCwd = '';
// Recover a native prompt by its actual cells, including explicit ConPTY row
// moves and wide Unicode. String offsets are not terminal column offsets.
function locatePrompt(cwd) {
  const buffer = term.buffer.active;
  const bottom = buffer.baseY + buffer.cursorY;
  const expected = ['PS '+cwd+'> ', cwd+'>'];
  for(let first=bottom; first>=Math.max(0,bottom-50); first--) {
    const firstLine = buffer.getLine(first);
    if(!firstLine) continue;
    for(let origin=0; origin<term.cols; origin++) {
      const firstChars=firstLine.getCell(origin)?.getChars() || ' ';
      if(!expected.some(prefix=>prefix.startsWith(firstChars))) continue;
      let candidates=expected, text='';
      scan: for(let row=first; row<=bottom; row++) {
        const line=buffer.getLine(row);
        if(!line) break;
        for(let column=row===first ? origin : 0; column<term.cols; column++) {
          const cell=line.getCell(column);
          if(!cell || cell.getWidth()===0) continue;
          const chars=cell.getChars();
          // A wide character can leave the last cell empty before wrapping.
          if(!chars && column===term.cols-1 && buffer.getLine(row+1)?.getCell(0)?.getWidth()===2) continue;
          text += chars || ' ';
          candidates=candidates.filter(prefix=>prefix.startsWith(text));
          if(!candidates.length) break scan;
          if(candidates.includes(text)) return {row, column:column+cell.getWidth()};
        }
      }
    }
  }
  return null;
}
function promptLine() {
  const buffer = term.buffer.active;
  // A ConPTY resize redraw can dispose xterm markers. Locate the authenticated
  // prompt in the public buffer again instead of treating editable input as raw.
  let row = promptMark && !promptMark.isDisposed ? promptMark.line : -1;
  let column = promptColumn;
  if(row < 0) {
    const recovered=locatePrompt(promptCwd);
    if(recovered) { row=recovered.row; column=recovered.column; }
  }
  if(row < 0) return null;
  // ConPTY redraws wrapped input with explicit cursor moves, which can clear
  // xterm's isWrapped flag. Include every row through the editing cursor.
  let end = Math.max(row, buffer.baseY + buffer.cursorY);
  while (buffer.getLine(end + 1)?.isWrapped) end++;
  let result = '';
  for (let y = row; y <= end; y++) {
    const line = buffer.getLine(y);
    if (line) result += line.translateToString(y === end, y === row ? column : 0);
  }
  return result.trimEnd();
}
let submitPending = false, queuedInput = [], lastOutput = 0, writesPending = 0;
function submitEditableLine() {
  const started = performance.now();
  submitPending = true;
  function finish() {
    // Native line editors echo asynchronously. Wait for their last redraw,
    // otherwise Enter can capture a truncated filename or literal content.
    const now = performance.now();
    if(now-started < 300 || ((writesPending || now-lastOutput < 100) && now-started < 2000)) {
      setTimeout(finish, 25); return;
    }
    const line = promptLine();
    atPrompt = false;
    if(line === null) bridge.input('\r'); else bridge.submit(line);
    submitPending = false;
    const queued = queuedInput; queuedInput = [];
    queued.forEach(feed);
  }
  setTimeout(finish, 25);
}
function feed(data) {
  if(submitPending) { queuedInput.push(data); return; }
  // Bracketed/multiline paste is always raw: never reinterpret scripts through AI.
  // The native session decides whether this is a shell prompt or a running
  // program. Its acknowledgement can precede this WebChannel callback, e.g.
  // after exiting a REPL; a stale browser flag must not bypass natural input.
  if (data === '\r') {
    submitEditableLine();
  } else {
    if (data.includes('\r') || data.includes('\n') || data.includes('\x03')) atPrompt = false;
    bridge.input(data);
  }
}
new QWebChannel(qt.webChannelTransport, channel => {
  bridge = channel.objects.bridge;
  if(!bridge) return;
  term = new Terminal({allowProposedApi:false,convertEol:false,fontFamily:'Cascadia Mono, Consolas, monospace',fontSize:14,cursorBlink:true,scrollback:10000,theme:{background:'#0b100d',foreground:'#dce6d8',cursor:'#bad797',selectionBackground:'#344c35',black:'#111b14',green:'#96c28b',brightGreen:'#bfdf9c',red:'#e87979',yellow:'#e6c275'}});
  fit = new FitAddon.FitAddon();
  term.loadAddon(fit);
  // Links are rendered, but navigation stays inside Qt's explicit browser opening policy.
  term.loadAddon(new WebLinksAddon.WebLinksAddon((event,uri) => bridge.openLink(uri)));
  term.open(document.getElementById('terminal'));
  term.parser.registerOscHandler(0, value => {
    const match = /^Chameleon-([a-f0-9]{32});(.*)$/s.exec(value);
    if (match) {
      const buffer = term.buffer.active;
      const row = buffer.baseY + buffer.cursorY;
      // ConPTY can replay a title on focus/resize. Only a visible native
      // prompt ending at the cursor may acknowledge shell readiness.
      const observed=locatePrompt(match[2]);
      if(!observed || observed.row!==row || observed.column!==buffer.cursorX) return true;
      const marker = term.registerMarker(0);
      const column = buffer.cursorX;
      bridge.prompt(match[1], match[2], accepted => {
        if(!accepted) { marker?.dispose(); return; }
        promptMark?.dispose();
        promptMark = marker;
        promptColumn = column;
        promptCwd = match[2];
        atPrompt = true;
      });
    }
    return true;
  });
  term.onData(feed);
  bridge.output.connect(data => {
    lastOutput = performance.now(); writesPending++;
    term.write(data, () => { writesPending--; lastOutput = performance.now(); });
  });
  term.onResize(size => bridge.resize(size.rows,size.cols));
  new ResizeObserver(() => fit.fit()).observe(document.getElementById('terminal'));
  term.attachCustomKeyEventHandler(event => {
    if (event.type !== 'keydown') return true;
    if (event.ctrlKey && event.shiftKey && event.code === 'KeyC') { bridge.copyClipboard(term.getSelection()); return false; }
    if (event.ctrlKey && event.shiftKey && event.code === 'KeyV') { bridge.pasteClipboard(text => term.paste(text)); return false; }
    if (event.ctrlKey && (event.key === '+' || event.key === '=' || event.key === '-')) { term.options.fontSize = Math.min(40,Math.max(8,term.options.fontSize+(event.key === '-'?-1:1))); fit.fit(); return false; }
    if (event.ctrlKey && event.code === 'Pause') { bridge.ctrlBreak(); return false; }
    return true;
  });
  window.configureTerminal = config => { Object.assign(term.options,config); fit.fit(); };
  window.focusTerminal = () => term.focus();
  window.terminalReady = true;
  bridge.ready();
  fit.fit(); term.focus();
});
