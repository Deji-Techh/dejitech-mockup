#!/usr/bin/env node

/**
 * DejiTech Mockup CLI Wrapper
 * 
 * This script wraps the Python CLI and passes all arguments through.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Get the package root directory
const packageRoot = path.join(__dirname, '..');

// Path to the Python source
const pythonSrc = path.join(packageRoot, 'src');
const mainModule = 'dejitech_mockup.main';

// Find Python executable
function findPython() {
  const candidates = ['python3', 'python'];
  
  for (const cmd of candidates) {
    try {
      const { execSync } = require('child_process');
      execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch (e) {
      continue;
    }
  }
  
  return null;
}

// Check if virtual environment exists
const venvPath = path.join(packageRoot, '.venv');
const venvPython = path.join(venvPath, 'bin', 'python');

let pythonCmd;
if (fs.existsSync(venvPython)) {
  pythonCmd = venvPython;
} else {
  pythonCmd = findPython();
}

if (!pythonCmd) {
  console.error('\x1b[31mError: Python 3 is required but not found.\x1b[0m');
  console.error('Please install Python 3:');
  console.error('  Arch Linux: sudo pacman -S python');
  console.error('  Ubuntu/Debian: sudo apt install python3');
  console.error('  macOS: brew install python3');
  process.exit(1);
}

// Build the command
const args = process.argv.slice(2);

// Set PYTHONPATH to include our source
const env = {
  ...process.env,
  PYTHONPATH: pythonSrc + (process.env.PYTHONPATH ? `:${process.env.PYTHONPATH}` : '')
};

// Spawn Python process
const proc = spawn(pythonCmd, ['-m', mainModule, ...args], {
  env,
  stdio: 'inherit',
  cwd: process.cwd()
});

proc.on('error', (err) => {
  console.error(`\x1b[31mFailed to start Python process: ${err.message}\x1b[0m`);
  process.exit(1);
});

proc.on('close', (code) => {
  process.exit(code || 0);
});
