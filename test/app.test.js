import test from 'node:test';
import assert from 'node:assert/strict';

// Run the actual UI module against its small DOM surface, without browser dependencies.
test('empty UI input never sends a search; topic text enables Search and resets clear it', async () => {
  const original = {document: globalThis.document, window: globalThis.window, fetch: globalThis.fetch};
  const nodes = new Map();
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {
      value: '', disabled: false, hidden: false, textContent: '', listeners: {}, children: [],
      addEventListener(name, callback) { this.listeners[name] = callback; },
      setAttribute() {}, focus() {}, replaceChildren() { this.children = []; },
    });
    return nodes.get(id);
  }
  const requests = [];
  globalThis.document = {getElementById: node};
  globalThis.window = {addEventListener() {}};
  globalThis.fetch = async (url) => {
    requests.push(url);
    assert.equal(url, '/api/status', 'blank input must not reach /api/chat');
    return {ok: true, json: async () => ({pages: 9, sections: 72})};
  };
  try {
    await import('../public/app.js');
    assert.equal(node('send').disabled, true);
    for (const value of ['', '   ', '\t\n']) {
      node('question').value = value;
      node('question').listeners.input();
      assert.equal(node('send').disabled, true);
      await node('form').listeners.submit({preventDefault() {}});
      node('question').listeners.keydown({key: 'Enter', shiftKey: false, isComposing: false, preventDefault() {}});
    }
    assert.deepEqual(requests, ['/api/status']);
    node('question').value = 'Python SDK setup';
    node('question').listeners.input();
    assert.equal(node('send').disabled, false);
    node('new').listeners.click();
    assert.equal(node('question').value, '');
    assert.equal(node('send').disabled, true);
    node('close').listeners.click();
    assert.equal(node('send').disabled, true);
    node('open').listeners.click();
    assert.equal(node('send').disabled, true);
  } finally {
    for (const [key, value] of Object.entries(original)) {
      if (value === undefined) delete globalThis[key]; else globalThis[key] = value;
    }
  }
});