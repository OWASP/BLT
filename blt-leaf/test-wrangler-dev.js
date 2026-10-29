#!/usr/bin/env node
// Unit tests for wrangler-dev.js. Nothing here spawns Wrangler: the Windows
// command and cleanup paths are checked by passing platform 'win32', so they
// run on Linux CI too. Package lookup uses throwaway folders in the temp dir.
const assert = require('assert');
const { EventEmitter } = require('events');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');

const {
  WRANGLER_NOT_FOUND,
  buildTreeKillCommand,
  buildWranglerDevCommand,
  resolveWranglerBin,
  stopWranglerDev,
} = require('./wrangler-dev');

const DEV_ARGS = [
  'dev',
  '--local',
  '--ip', '127.0.0.1',
  '--port', '8788',
  '--log-level', 'error',
];

// --- command construction ---------------------------------------------------

for (const platform of ['linux', 'darwin']) {
  test(`${platform}: runs npx wrangler, as before`, () => {
    const { cmd, args, options } = buildWranglerDevCommand({
      platform,
      nodePath: '/usr/bin/node',
      wranglerBin: '/ignored/wrangler.js',
      cwd: '/repo/blt-leaf',
      port: 8788,
      env: { PATH: '/usr/bin' },
    });
    assert.strictEqual(cmd, 'npx');
    assert.strictEqual(args[0], 'wrangler');
    assert.deepStrictEqual(args, ['wrangler', ...DEV_ARGS]);
    assert.deepStrictEqual(options, {
      cwd: '/repo/blt-leaf',
      env: { PATH: '/usr/bin', BROWSER: 'none' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  });
}

test('win32: runs the wrangler bin script with node, without npx or a shell', () => {
  const nodePath = 'C:\\Program Files\\nodejs\\node.exe';
  const wranglerBin = 'C:\\repo\\node_modules\\wrangler\\bin\\wrangler.js';
  const { cmd, args, options } = buildWranglerDevCommand({
    platform: 'win32',
    nodePath,
    wranglerBin,
    cwd: 'C:\\repo\\blt-leaf',
    port: 8788,
    env: { Path: 'C:\\Windows' },
  });
  assert.strictEqual(cmd, nodePath);
  assert.deepStrictEqual(args, [wranglerBin, ...DEV_ARGS]);
  assert.ok(!args.includes('npx') && !args.includes('npx.cmd'));
  assert.strictEqual(options.cwd, 'C:\\repo\\blt-leaf');
  assert.strictEqual(options.shell, undefined);
  assert.deepStrictEqual(options.env, { Path: 'C:\\Windows', BROWSER: 'none' });
  assert.deepStrictEqual(options.stdio, ['ignore', 'pipe', 'pipe']);
});

test('win32: requires the node and wrangler paths', () => {
  const base = { platform: 'win32', cwd: '.', port: 1 };
  assert.throws(() => buildWranglerDevCommand({ ...base, nodePath: 'node.exe' }), TypeError);
  assert.throws(() => buildWranglerDevCommand({ ...base, wranglerBin: 'w.js' }), TypeError);
});

test('does not change the env object it is given', () => {
  const env = { BROWSER: 'firefox' };
  const { options } = buildWranglerDevCommand({ platform: 'linux', cwd: '.', port: 1, env });
  assert.deepStrictEqual(env, { BROWSER: 'firefox' });
  assert.strictEqual(options.env.BROWSER, 'none');
});

// --- resolving the wrangler bin -----------------------------------------------

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'blt-leaf-wrangler-'));
test.after(() => fs.rmSync(tmpRoot, { recursive: true, force: true }));

let fixtureCount = 0;
function fixture() {
  const dir = path.join(tmpRoot, String(fixtureCount++));
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

// Write node_modules/wrangler under `root`, with the bin script at `binFile`
// (relative to the package) unless writeBin is false.
function installFakeWrangler(root, pkg, { binFile = 'bin/wrangler.js', writeBin = true } = {}) {
  const pkgDir = path.join(root, 'node_modules', 'wrangler');
  fs.mkdirSync(pkgDir, { recursive: true });
  const pkgJson = JSON.stringify({ name: 'wrangler', ...pkg });
  fs.writeFileSync(path.join(pkgDir, 'package.json'), pkgJson);
  if (writeBin) {
    fs.mkdirSync(path.dirname(path.join(pkgDir, binFile)), { recursive: true });
    fs.writeFileSync(path.join(pkgDir, binFile), '');
  }
  return pkgDir;
}

function assertSamePath(actual, expected) {
  assert.strictEqual(fs.realpathSync(actual), fs.realpathSync(expected));
}

function assertNotFound(fn, pattern) {
  assert.throws(fn, (error) => {
    assert.strictEqual(error.code, WRANGLER_NOT_FOUND);
    assert.match(error.message, pattern);
    return true;
  });
}

test('resolves the bin from the package\'s own "bin" field', () => {
  const root = fixture();
  const pkgDir = installFakeWrangler(
    root,
    { version: '9.0.0', bin: { wrangler: './cli/run.js' } },
    { binFile: 'cli/run.js' }
  );
  assertSamePath(resolveWranglerBin(root), path.join(pkgDir, 'cli', 'run.js'));
});

test('supports a string "bin" field', () => {
  const root = fixture();
  const pkgDir = installFakeWrangler(root, { bin: './bin/wrangler.js' });
  assertSamePath(resolveWranglerBin(root), path.join(pkgDir, 'bin', 'wrangler.js'));
});

test('finds wrangler hoisted to a parent node_modules', () => {
  const root = fixture();
  const pkgDir = installFakeWrangler(root, { bin: { wrangler: './bin/wrangler.js' } });
  const project = path.join(root, 'packages', 'blt-leaf');
  fs.mkdirSync(project, { recursive: true });
  assertSamePath(resolveWranglerBin(project), path.join(pkgDir, 'bin', 'wrangler.js'));
});

test('still finds the package when an "exports" map hides package.json', () => {
  const root = fixture();
  const pkgDir = installFakeWrangler(root, {
    bin: { wrangler: './bin/wrangler.js' },
    exports: { '.': './index.js' },
  });
  const project = path.join(root, 'app');
  fs.mkdirSync(project);
  assertSamePath(resolveWranglerBin(project), path.join(pkgDir, 'bin', 'wrangler.js'));
});

test('missing wrangler gives an actionable error', () => {
  assertNotFound(() => resolveWranglerBin(fixture()), /not installed.*npm install/);
});

test('a package without a wrangler bin entry gives a clear error', () => {
  const root = fixture();
  installFakeWrangler(root, { version: '9.0.0', bin: { other: './x.js' } }, { writeBin: false });
  assertNotFound(() => resolveWranglerBin(root), /no "wrangler" bin entry/);
});

test('a missing bin file asks for a reinstall', () => {
  const root = fixture();
  installFakeWrangler(root, { bin: { wrangler: './bin/wrangler.js' } }, { writeBin: false });
  assertNotFound(() => resolveWranglerBin(root), /executable is missing.*npm ci/);
});

const installedPkg = path.join(__dirname, 'node_modules', 'wrangler', 'package.json');
test(
  'resolves the installed wrangler',
  { skip: !fs.existsSync(installedPkg) && 'wrangler is not installed' },
  () => {
    const pkg = JSON.parse(fs.readFileSync(installedPkg, 'utf8'));
    const bin = typeof pkg.bin === 'string' ? pkg.bin : pkg.bin.wrangler;
    assertSamePath(resolveWranglerBin(__dirname), path.join(path.dirname(installedPkg), bin));
  }
);

// --- stopping wrangler dev -----------------------------------------------------

test('win32 kills the whole process tree with taskkill', () => {
  assert.deepStrictEqual(buildTreeKillCommand('win32', 4321), {
    cmd: 'taskkill',
    args: ['/pid', '4321', '/T', '/F'],
  });
  assert.strictEqual(buildTreeKillCommand('linux', 4321), null);
  assert.strictEqual(buildTreeKillCommand('darwin', 4321), null);
});

// Like a ChildProcess: kill() sets `killed` at once, but exitCode/signalCode
// and the 'exit' event only change when the process has really exited.
class FakeChild extends EventEmitter {
  constructor({ pid = 4321, exitsOn = ['SIGTERM', 'SIGKILL'] } = {}) {
    super();
    this.pid = pid;
    this.exitCode = null;
    this.signalCode = null;
    this.killed = false;
    this.signals = [];
    this.exitsOn = exitsOn;
  }

  kill(signal) {
    this.signals.push(signal);
    this.killed = true;
    if (this.exitsOn.includes(signal)) setImmediate(() => this.exit(null, signal));
    return true;
  }

  exit(code, signal) {
    this.exitCode = code;
    this.signalCode = signal;
    this.emit('exit', code, signal);
  }
}

const noCommand = () => assert.fail('no external command expected');

test('stop: does nothing if the process already exited', async () => {
  const child = new FakeChild();
  child.exitCode = 0;
  const result = await stopWranglerDev(child, { platform: 'linux', runCommand: noCommand });
  assert.deepStrictEqual(result, { exited: true });
  assert.deepStrictEqual(child.signals, []);
});

test('stop: does nothing if spawn failed (no pid)', async () => {
  const child = new FakeChild();
  child.pid = undefined;
  const result = await stopWranglerDev(child, { platform: 'win32', runCommand: noCommand });
  assert.deepStrictEqual(result, { exited: true });
  assert.deepStrictEqual(child.signals, []);
});

test('stop (linux): sends SIGTERM and waits for the exit event', async () => {
  const child = new FakeChild();
  const result = await stopWranglerDev(child, {
    platform: 'linux',
    graceMs: 5000,
    runCommand: noCommand,
  });
  assert.deepStrictEqual(result, { exited: true });
  assert.deepStrictEqual(child.signals, ['SIGTERM']);
  assert.strictEqual(child.signalCode, 'SIGTERM');
});

test('stop (linux): escalates to SIGKILL when SIGTERM is ignored', async () => {
  const child = new FakeChild({ exitsOn: ['SIGKILL'] });
  const result = await stopWranglerDev(child, { platform: 'linux', graceMs: 10 });
  assert.deepStrictEqual(result, { exited: true });
  assert.deepStrictEqual(child.signals, ['SIGTERM', 'SIGKILL']);
});

test('stop: reports a process that never exits', async () => {
  const child = new FakeChild({ exitsOn: [] });
  const result = await stopWranglerDev(child, { platform: 'linux', graceMs: 10 });
  assert.deepStrictEqual(result, { exited: false });
  assert.ok(child.killed, 'killed is true even though the process is still running');
});

test('stop (win32): runs taskkill on the tree and waits for the exit event', async () => {
  const child = new FakeChild();
  const commands = [];
  const result = await stopWranglerDev(child, {
    platform: 'win32',
    graceMs: 5000,
    runCommand: (cmd, args) => {
      commands.push([cmd, ...args]);
      setImmediate(() => child.exit(1, null));
      return true;
    },
  });
  assert.deepStrictEqual(result, { exited: true });
  assert.deepStrictEqual(commands, [['taskkill', '/pid', '4321', '/T', '/F']]);
  assert.deepStrictEqual(child.signals, []);
});

test('stop (win32): falls back to child.kill() if taskkill fails', async () => {
  const child = new FakeChild();
  const result = await stopWranglerDev(child, {
    platform: 'win32',
    graceMs: 5000,
    runCommand: () => false,
  });
  assert.deepStrictEqual(result, { exited: true });
  assert.deepStrictEqual(child.signals, ['SIGTERM']);
});
