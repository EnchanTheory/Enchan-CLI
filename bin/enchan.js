#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const backendScript = path.join(__dirname, '..', 'backend', 'enchan_chat.py');

function resolvePython() {
    if (process.env.ENCHAN_PYTHON) {
        return process.env.ENCHAN_PYTHON;
    }

    return process.platform === 'win32' ? 'python' : 'python3';
}

const pythonPath = resolvePython();
const backendArgs = [backendScript, ...process.argv.slice(2)];

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


