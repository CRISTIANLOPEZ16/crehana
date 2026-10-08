const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const collection = JSON.parse(fs.readFileSync(
  path.join(__dirname, '../../docs/task-manager.postman_collection.json'), 'utf8'
));
const setupRequests = collection.item[0].item;
const preRequest = collection.event.find(event => event.listen === 'prerequest').script.exec.join('\n');

function requestContext(auth, storedToken) {
  const stored = { owner_token: storedToken };
  const active = { owner_token: 'stale-environment-value' };
  let skipped = false;
  const pm = {
    collectionVariables: {
      toObject: () => stored,
      set: (key, value) => { stored[key] = value; },
    },
    variables: {
      get: key => active[key],
      set: (key, value) => { active[key] = value; },
    },
    request: { toJSON: () => ({ auth }) },
    execution: { skipRequest: () => { skipped = true; } },
    test: () => {},
  };
  return { pm, stored, active, wasSkipped: () => skipped };
}

const ownerAuth = setupRequests.find(item => item.name === 'Current owner profile').request.auth;

for (const token of ['', 'eyJ.header...', '{{owner_token}}']) {
  test(`blocks an incomplete token (${token || 'empty'}) without exposing it`, () => {
    const context = requestContext(ownerAuth, token);
    assert.throws(() => vm.runInNewContext(preRequest, context), /Run Login owner/);
    assert.equal(context.wasSkipped(), true);
  });
}

test('uses the full saved token despite a conflicting environment value', () => {
  const token = 'example_header.example_payload.example_signature';
  const context = requestContext(ownerAuth, token);
  vm.runInNewContext(preRequest, context);
  assert.equal(context.active.owner_token, token);
  assert.equal(context.wasSkipped(), false);
});

for (const name of ['Login owner', 'Missing token rejected', 'Invalid token rejected']) {
  test(`does not block ${name}`, () => {
    const auth = setupRequests.find(item => item.name === name).request.auth;
    const context = requestContext(auth, '');
    vm.runInNewContext(preRequest, context);
    assert.equal(context.wasSkipped(), false);
  });
}

for (const role of ['owner', 'member', 'outsider']) {
  test(`Login ${role} saves the full response token in both scopes`, () => {
    const login = setupRequests.find(item => item.name === `Login ${role}`);
    const context = requestContext(login.request.auth, 'old-token');
    const token = `example_header.${'payload'.repeat(100)}.example_signature`;
    context.pm.response = { code: 200, json: () => ({ access_token: token }) };
    const script = login.event.find(event => event.listen === 'test').script.exec.join('\n');
    vm.runInNewContext(script, context);
    assert.equal(context.stored[`${role}_token`], token);
    assert.equal(context.active[`${role}_token`], token);
  });
}
