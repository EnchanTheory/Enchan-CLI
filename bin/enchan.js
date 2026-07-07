#!/usr/bin/env node

const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const cliRoot = path.join(__dirname, '..');
const backendScript = path.join(cliRoot, 'backend', 'enchan_chat.py');
const updateNoticePath = path.join(cliRoot, '.enchan-update-available');

function resolvePython() {
    if (process.env.ENCHAN_PYTHON) {
        return process.env.ENCHAN_PYTHON;
    }

    const venvPython = process.platform === 'win32'
        ? path.join(cliRoot, '.venv', 'Scripts', 'python.exe')
        : path.join(cliRoot, '.venv', 'bin', 'python');
    if (fs.existsSync(venvPython)) {
        return venvPython;
    }

    return process.platform === 'win32' ? 'python' : 'python3';
}

function commandExists(command) {
    const checker = process.platform === 'win32' ? 'where.exe' : 'command';
    const args = process.platform === 'win32' ? [command] : ['-v', command];
    const result = spawnSync(checker, args, { stdio: 'ignore', shell: process.platform !== 'win32' });
    return result.status === 0;
}

function runChecked(command, args, options = {}) {
    const result = spawnSync(command, args, {
        cwd: options.cwd || cliRoot,
        stdio: 'inherit',
        shell: false,
        env: process.env
    });
    if (result.error) {
        console.error(`[Enchan CLI] Failed to run ${command}: ${result.error.message}`);
        process.exit(1);
    }
    if (result.status !== 0) {
        process.exit(result.status || 1);
    }
}

function runInstaller() {
    console.log('[Enchan CLI] Refreshing install...');
    if (process.platform === 'win32') {
        const installScript = path.join(cliRoot, 'install.ps1');
        const shell = commandExists('pwsh') ? 'pwsh' : 'powershell.exe';
        runChecked(shell, ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', installScript], { cwd: cliRoot });
    } else {
        const installScript = path.join(cliRoot, 'install.sh');
        runChecked('bash', [installScript], { cwd: cliRoot });
    }
}

function runUpdate(updateArgs = []) {
    if (!fs.existsSync(path.join(cliRoot, '.git'))) {
        console.error('[Enchan CLI] Cannot update: this install is not a Git checkout. Reinstall from EnchanTheory/Enchan-CLI once.');
        process.exit(1);
    }
    if (!commandExists('git')) {
        console.error('[Enchan CLI] Cannot update: git was not found on PATH.');
        process.exit(1);
    }

    const repair = updateArgs.includes('--repair');
    const before = gitOutput(['rev-parse', 'HEAD']);
    console.log('[Enchan CLI] Updating source...');
    runChecked('git', ['pull', '--ff-only'], { cwd: cliRoot });
    const after = gitOutput(['rev-parse', 'HEAD']);
    clearUpdateNotice();

    if (!repair && before && after && before === after) {
        console.log('[Enchan CLI] Already up to date.');
        return;
    }

    runInstaller();
}

function gitResult(args, options = {}) {
    return spawnSync('git', args, {
        cwd: cliRoot,
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
        shell: false,
        env: process.env,
        timeout: options.timeoutMs || undefined
    });
}

function gitOutput(args, options = {}) {
    const result = gitResult(args, options);
    if (result.status !== 0) {
        return '';
    }
    return String(result.stdout || '').trim();
}

function upstreamRef() {
    return gitOutput(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}']);
}

function upstreamRemote(upstream) {
    return upstream ? upstream.split('/')[0] : '';
}

function clearUpdateNotice() {
    try { fs.rmSync(updateNoticePath, { force: true }); } catch (_) {}
}

function writeUpdateNotice() {
    try { fs.writeFileSync(updateNoticePath, '1', 'utf8'); } catch (_) {}
}

function isFastForwardUpdateAvailable(upstream) {
    const local = gitOutput(['rev-parse', 'HEAD']);
    const remote = gitOutput(['rev-parse', upstream]);
    if (!local || !remote || local === remote) {
        return false;
    }
    const result = gitResult(['merge-base', '--is-ancestor', 'HEAD', upstream]);
    return result.status === 0;
}

function refreshUpdateNotice({ timeoutMs } = {}) {
    if (!fs.existsSync(path.join(cliRoot, '.git')) || !commandExists('git')) {
        return;
    }

    const upstream = upstreamRef();
    const remote = upstreamRemote(upstream);
    if (!upstream || !remote) {
        return;
    }

    const fetch = gitResult(['fetch', '--quiet', remote], { timeoutMs });
    if (fetch.status !== 0) {
        return;
    }

    if (isFastForwardUpdateAvailable(upstream)) {
        writeUpdateNotice();
    } else {
        clearUpdateNotice();
    }
}

function notifyUpdateAvailableAsync() {
    setTimeout(() => refreshUpdateNotice({ timeoutMs: 5000 }), 0).unref();
}

const args = process.argv.slice(2);
if (args[0] === 'update' || args[0] === 'self-update') {
    runUpdate(args.slice(1));
    process.exit(0);
}

// Keep normal startup responsive. The update check may perform network I/O, so it must
// never block the Python chat backend from starting.
notifyUpdateAvailableAsync();

const pythonPath = resolvePython();
const backendArgs = [backendScript, ...args];

const child = spawn(pythonPath, backendArgs, {
    stdio: 'inherit',
    env: {
        ...process.env,
        PYTHONPATH: [cliRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter)
    }
});

child.on('error', (err) => {
    console.error(`[Enchan CLI Error] Failed to start Python backend: ${err.message}`);
    console.error('Set ENCHAN_PYTHON to the Python executable for this install if auto-detection fails.');
});

child.on('exit', (code, signal) => {
    if (code !== 0 && signal !== 'SIGINT') {
        console.error(`[Enchan CLI] Python backend exited with code ${code} (signal: ${signal})`);
    }
    process.exit(code !== null ? code : 0);
});
