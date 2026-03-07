#!/usr/bin/env node

/**
 * Post-install script for dejitech-mockup
 * 
 * Sets up Python virtual environment and installs dependencies.
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const packageRoot = path.join(__dirname, '..');
const venvPath = path.join(packageRoot, '.venv');
const requirementsPath = path.join(packageRoot, 'requirements.txt');

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
  dim: '\x1b[2m'
};

function log(msg, color = 'reset') {
  console.log(`${colors[color]}${msg}${colors.reset}`);
}

function logStep(msg) {
  console.log(`${colors.cyan}==>${colors.reset} ${colors.bright}${msg}${colors.reset}`);
}

// Find Python 3
function findPython() {
  const candidates = ['python3', 'python'];
  
  for (const cmd of candidates) {
    try {
      const version = execSync(`${cmd} --version 2>&1`, { encoding: 'utf8' });
      if (version.includes('Python 3')) {
        return cmd;
      }
    } catch (e) {
      continue;
    }
  }
  return null;
}

// Check if FFmpeg is installed
function checkFFmpeg() {
  try {
    execSync('ffmpeg -version', { stdio: 'ignore' });
    return true;
  } catch (e) {
    return false;
  }
}

async function main() {
  console.log('');
  log('╔══════════════════════════════════════════╗', 'cyan');
  log('║     DejiTech Mockup - Post Install       ║', 'cyan');
  log('╚══════════════════════════════════════════╝', 'cyan');
  console.log('');

  // Check Python
  logStep('Checking Python...');
  const pythonCmd = findPython();
  
  if (!pythonCmd) {
    log('Python 3 is required but not found!', 'red');
    log('Please install Python 3:', 'yellow');
    log('  Arch Linux: sudo pacman -S python', 'dim');
    log('  Ubuntu/Debian: sudo apt install python3', 'dim');
    log('  macOS: brew install python3', 'dim');
    process.exit(1);
  }
  
  log(`Found: ${pythonCmd}`, 'green');

  // Check FFmpeg
  logStep('Checking FFmpeg...');
  if (!checkFFmpeg()) {
    log('FFmpeg is required but not found!', 'red');
    log('Please install FFmpeg:', 'yellow');
    log('  Arch Linux: sudo pacman -S ffmpeg', 'dim');
    log('  Ubuntu/Debian: sudo apt install ffmpeg', 'dim');
    log('  macOS: brew install ffmpeg', 'dim');
    log('', 'reset');
    log('Continuing anyway - you can install FFmpeg later.', 'yellow');
  } else {
    log('Found FFmpeg', 'green');
  }

  // Create virtual environment
  logStep('Creating Python virtual environment...');
  
  if (fs.existsSync(venvPath)) {
    log('Virtual environment already exists', 'dim');
  } else {
    try {
      execSync(`${pythonCmd} -m venv "${venvPath}"`, { 
        cwd: packageRoot,
        stdio: 'inherit' 
      });
      log('Created .venv/', 'green');
    } catch (e) {
      log(`Warning: Could not create venv: ${e.message}`, 'yellow');
      log('Will use system Python instead', 'dim');
    }
  }

  // Install Python dependencies
  logStep('Installing Python dependencies...');
  
  const pipCmd = fs.existsSync(path.join(venvPath, 'bin', 'pip'))
    ? path.join(venvPath, 'bin', 'pip')
    : `${pythonCmd} -m pip`;

  try {
    if (fs.existsSync(requirementsPath)) {
      execSync(`${pipCmd} install -r "${requirementsPath}" --quiet`, {
        cwd: packageRoot,
        stdio: 'inherit'
      });
    } else {
      // Install core dependencies directly
      execSync(`${pipCmd} install typer rich ffmpeg-python --quiet`, {
        cwd: packageRoot,
        stdio: 'inherit'
      });
    }
    log('Dependencies installed', 'green');
  } catch (e) {
    log(`Warning: Could not install some dependencies: ${e.message}`, 'yellow');
    log('You may need to install them manually:', 'dim');
    log('  pip install typer rich ffmpeg-python', 'dim');
  }

  // Create assets directory
  logStep('Setting up assets directory...');
  const assetsPath = path.join(packageRoot, 'assets');
  if (!fs.existsSync(assetsPath)) {
    fs.mkdirSync(assetsPath, { recursive: true });
  }
  log(`Assets directory: ${assetsPath}`, 'dim');

  // Done
  console.log('');
  log('╔══════════════════════════════════════════╗', 'green');
  log('║         Installation Complete!           ║', 'green');
  log('╚══════════════════════════════════════════╝', 'green');
  console.log('');
  log('Next steps:', 'bright');
  log('  1. Add device frame images to:', 'reset');
  log(`     ${assetsPath}`, 'cyan');
  log('  2. Run: dejitech-mockup --help', 'reset');
  console.log('');
}

main().catch(err => {
  console.error(`${colors.red}Installation error: ${err.message}${colors.reset}`);
  process.exit(1);
});
