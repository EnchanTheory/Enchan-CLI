#!/usr/bin/env node

const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const cliRoot = path.join(__dirname, '..');
const backendScript = path.join(cliRoot, 'backend', 'enchan_chat.py');

function resolvePython() {
    if (process.env.ENCHAN_PYTHON) {
        return process.env.ENCHAN_PYTHON;
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

function runUpdate() {
    if (!fs.existsSync(path.join(cliRoot, '.git'))) {
        console.error('[Enchan CLI] Cannot update: this install is not a Git checkout. Reinstall from EnchanTheory/Enchan-CLI once.');
        process.exit(1);
    }
    if (!commandExists('git')) {
        console.error('[Enchan CLI] Cannot update: git was not found on PATH.');
        process.exit(1);
    }

    console.log('[Enchan CLI] Updating source...');
    runChecked('git', ['pull', '--ff-only'], { cwd: cliRoot });

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

const args = process.argv.slice(2);
if (args[0] === 'update' || args[0] === 'self-update') {
    runUpdate();
    process.exit(0);
}

const pythonPath = resolvePython();
const backendArgs = [backendScript, ...args];

const child = spawn(pythonPath, backendArgs, {
    stdio: 'inherit',
    env: process.env
});

child.on('error', (err) => {
    console.error(`[Enchan CLI Error] Failed to start Python backend: ${err.message}`);
    console.error('Set ENCHAN_PYTHON to the Python executable for this install if auto-detection fails.');
});

child.on('exit', (code, signal) => {
    if (code !== 0) {
        console.error(`[Enchan CLI] Python backend exited with code ${code} (signal: ${signal})`);
    }
});
