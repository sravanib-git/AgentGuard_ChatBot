// Only in-memory state. Never use localStorage, sessionStorage or cookies.
export class ChatMemory {
  constructor() { this.version = 0; this.history = []; this.opened = true; this.pending = null; }
  begin() {
    if (!this.opened) throw new Error('Chat is closed.');
    this.pending?.abort();
    const controller = new AbortController();
    const request = {version: ++this.version, controller, history: this.history.map(m => ({...m}))};
    this.pending = controller;
    return request;
  }
  current(request) { return this.opened && request.version === this.version && !request.controller.signal.aborted; }
  remember(request, question, answer) {
    if (!this.current(request)) return false;
    this.history.push({role:'user', content:question}, {role:'assistant', content:answer.slice(0,6000)});
    while (this.history.length > 6 || this.history.reduce((n,m) => n+m.content.length,0) > 18000) this.history.splice(0,2);
    return true;
  }
  reset(open = true) {
    this.pending?.abort(); this.pending = null; this.version++; this.history = []; this.opened = open;
  }
}
