'use strict';
let term, fit, bridge, promptMark = null, promptColumn = 0, atPrompt = false, promptCwd = '';
function promptLine() {
  const buffer = term.buffer.active;
  // A ConPTY resize redraw can dispose xterm markers. Locate the authenticated
  // prompt in the public buffer again instead of treating editable input as raw.
  let row = promptMark && !promptMark.isDisposed ? promptMark.line : -1;
  let column = promptColumn;
  for(let y=buffer.baseY+buffer.cursorY; y>=Math.max(0,buffer.baseY+buffer.cursorY-50); y--) {
    const text=buffer.getLine(y)?.translateToString(true) || '';
    const prefix=promptCwd+'>';
    const index=text.indexOf(prefix);
    if(index>=0) { row=y; column=index+prefix.length; if(text.startsWith('PS '))column++; break; }
  }
  if(row < 0) return null;
  let end = row;
  while (buffer.getLine(end + 1)?.isWrapped) end++;
  let result = '';
  for (let y = row; y <= end; y++) {
    const line = buffer.getLine(y);
    if (line) result += line.translateToString(y === end, y === row ? column : 0);
  }
  return result.trimEnd();
}
function feed(data) {
  // Bracketed/multiline paste is always raw: never reinterpret scripts through AI.
  if (data === '\r' && atPrompt) {
    const line = promptLine();
    atPrompt = false;
    if (line === null) bridge.input(data); else bridge.submit(line);
  } else {
    if (data.includes('\r') || data.includes('\n') || data.includes('\x03')) atPrompt = false;
    bridge.input(data);
  }
}
new QWebChannel(qt.webChannelTransport, channel => {
  bridge = channel.objects.bridge;
  if(!bridge) return;
  term = new Terminal({allowProposedApi:false,convertEol:false,fontFamily:'Cascadia Mono, Consolas, monospace',fontSize:14,cursorBlink:true,scrollback:10000,theme:{background:'#080d0b',foreground:'#d8ecdf',cursor:'#51fa8b',selectionBackground:'#286544',black:'#080d0b',green:'#51fa8b',brightGreen:'#82ffb0',red:'#e87979',yellow:'#e6c275'}});
  fit = new FitAddon.FitAddon();
  term.loadAddon(fit);
  // Links are rendered, but navigation stays inside Qt's explicit browser opening policy.
  term.loadAddon(new WebLinksAddon.WebLinksAddon((event,uri) => bridge.openLink(uri)));
  term.open(document.getElementById('terminal'));
  term.parser.registerOscHandler(0, value => {
    const match = /^Chameleon-([a-f0-9]{32});(.*)$/s.exec(value);
    if (match) {
      bridge.prompt(match[1], match[2], accepted => {
        if(!accepted) return;
        promptMark?.dispose();
        promptMark = term.registerMarker(0);
        promptColumn = term.buffer.active.cursorX;
        promptCwd = match[2];
        atPrompt = true;
      });
    }
    return true;
  });
  term.onData(feed);
  bridge.output.connect(data => term.write(data));
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
  window.terminalReady = true;
  bridge.ready();
  fit.fit(); term.focus();
});
