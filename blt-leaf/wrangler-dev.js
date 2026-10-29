// Helpers for starting and stopping `wrangler dev` from the Node test scripts.
// The command and kill logic take the platform as an argument, so the Windows
// branch can be unit tested on Linux CI without spawning a Windows process.

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const WRANGLER_NOT_FOUND = 'WRANGLER_NOT_FOUND';

function wranglerError(message) {
  const error = new Error(message);
  error.code = WRANGLER_NOT_FOUND;
  return error;
}

// Find the installed package folder. require.resolve follows Node's normal
// lookup from `cwd`, so a hoisted node_modules in a parent folder also works.
function findPackageDir(name, cwd) {
  try {
    const pkgJson = require.resolve(`${name}/package.json`, { paths: [cwd] });
    return path.dirname(pkgJson);
  } catch (error) {
    if (error.code === 'MODULE_NOT_FOUND') return null;
    if (error.code !== 'ERR_PACKAGE_PATH_NOT_EXPORTED') throw error;
  }
  // An "exports" map can hide package.json from require.resolve. Look for the
  // package folder in each node_modules from cwd upwards, as Node does.
  let dir = path.resolve(cwd);
  for (;;) {
    const candidate = path.join(dir, 'node_modules', name);
    if (fs.existsSync(path.join(candidate, 'package.json'))) return candidate;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

// Return the absolute path of the script behind the `wrangler` command, read
// from the installed package's "bin" field (the same entry npm links).
function resolveWranglerBin(cwd) {
  const pkgDir = findPackageDir('wrangler', cwd);
  if (!pkgDir) {
    throw wranglerError(
      `Wrangler is not installed (no "wrangler" package found from ${cwd}). ` +
        'Run "npm install" in blt-leaf, then rerun the tests.'
    );
  }

  const pkg = JSON.parse(fs.readFileSync(path.join(pkgDir, 'package.json'), 'utf8'));
  const bin = typeof pkg.bin === 'string' ? pkg.bin : pkg.bin && pkg.bin.wrangler;
  if (!bin) {
    throw wranglerError(
      `The wrangler package at ${pkgDir} (version ${pkg.version}) has no ` +
        '"wrangler" bin entry, so the test cannot start it.'
    );
  }

  const binPath = path.resolve(pkgDir, bin);
  if (!fs.existsSync(binPath)) {
    throw wranglerError(
      `Wrangler's executable is missing: ${binPath}. ` +
        'Reinstall dependencies with "npm ci" in blt-leaf, then rerun the tests.'
    );
  }
  return binPath;
}

// Build the spawn() arguments for `wrangler dev`.
// Windows: npx is npx.cmd, which Node cannot spawn without a shell (spawn
// EINVAL), so run Wrangler's bin script with Node directly.
// Other platforms: `npx wrangler ...`, unchanged.
function buildWranglerDevCommand({
  platform,
  nodePath,
  wranglerBin,
  cwd,
  port,
  env = process.env,
}) {
  const devArgs = [
    'dev',
    '--local',
    '--ip', '127.0.0.1',
    '--port', String(port),
    '--log-level', 'error',
  ];
  const options = {
    cwd,
    env: { ...env, BROWSER: 'none' },
    stdio: ['ignore', 'pipe', 'pipe'],
  };

  if (platform === 'win32') {
    if (!nodePath || !wranglerBin) {
      throw new TypeError('nodePath and wranglerBin are required on Windows');
    }
    return { cmd: nodePath, args: [wranglerBin, ...devArgs], options };
  }
  return { cmd: 'npx', args: ['wrangler', ...devArgs], options };
}

// Windows has no SIGTERM: child.kill() calls TerminateProcess on the direct
// child only, so Wrangler's signal forwarding never runs. taskkill /T ends the
// whole tree (node wrangler.js -> node cli.js -> workerd).
function buildTreeKillCommand(platform, pid) {
  if (platform !== 'win32') return null;
  return { cmd: 'taskkill', args: ['/pid', String(pid), '/T', '/F'] };
}

function runCommandSync(cmd, args) {
  const result = spawnSync(cmd, args, { stdio: 'ignore', windowsHide: true });
  return !result.error && result.status === 0;
}

// child.killed only means a signal was sent; exitCode/signalCode are set once
// the process has really exited.
function hasExited(child) {
  return child.exitCode !== null || child.signalCode !== null;
}

function waitForExit(child, timeoutMs) {
  if (hasExited(child)) return Promise.resolve(true);
  return new Promise((resolve) => {
    const onExit = () => {
      clearTimeout(timer);
      resolve(true);
    };
    const timer = setTimeout(() => {
      child.removeListener('exit', onExit);
      resolve(false);
    }, timeoutMs);
    child.once('exit', onExit);
  });
}

// Stop `wrangler dev` and wait until the direct child has exited, escalating
// to SIGKILL after graceMs. Resolves to { exited } so callers can warn.
async function stopWranglerDev(child, options = {}) {
  const {
    platform = process.platform,
    graceMs = 5000,
    runCommand = runCommandSync,
  } = options;

  // No pid means spawn failed, so there is no process to stop.
  if (!child || child.pid === undefined || hasExited(child)) {
    return { exited: true };
  }

  const exited = waitForExit(child, graceMs);
  const treeKill = buildTreeKillCommand(platform, child.pid);
  if (!treeKill || !runCommand(treeKill.cmd, treeKill.args)) {
    child.kill('SIGTERM');
  }
  if (await exited) return { exited: true };

  const killed = waitForExit(child, graceMs);
  child.kill('SIGKILL');
  return { exited: await killed };
}

module.exports = {
  WRANGLER_NOT_FOUND,
  buildTreeKillCommand,
  buildWranglerDevCommand,
  hasExited,
  resolveWranglerBin,
  stopWranglerDev,
};
