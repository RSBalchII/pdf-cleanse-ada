#!/usr/bin/env node
/**
 * Setup script — installs Python dependencies into a .venv virtual environment.
 * Zero external dependencies (uses only Node.js built-ins).
 */

import { spawn, spawnSync } from 'child_process';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SCRIPT_DIR = __dirname;

const VENV_DIR = join(SCRIPT_DIR, '.venv');
const isWin = process.platform === 'win32';
const PY_BASE = isWin ? 'python' : 'python3';

function log(msg, prefix = ' ') {
  console.log(`${prefix} ${msg}`);
}
function ok(msg) { log(msg, '✅'); }
function fail(msg) { log(msg, '❌'); }
function info(msg) { log(msg, '🔧'); }
function skip(msg) { log(msg, '⏭️'); }

function run(cmd, args, cwd) {
  return new Promise((resolve) => {
    const proc = spawn(cmd, args, { cwd, stdio: 'pipe' });
    let out = '';
    let err = '';
    proc.stdout.on('data', (d) => { out += d.toString(); process.stdout.write(d); });
    proc.stderr.on('data', (d) => { err += d.toString(); process.stderr.write(d); });
    proc.on('close', (code) => resolve({ code, out, err }));
    proc.on('error', (e) => resolve({ code: 1, out: '', err: e.message }));
  });
}

async function main() {
  console.log('\n🔧 PDF ADA Processor — Setup\n');

  // Check Python
  info('Checking Python...');
  const pyCheck = spawnSync(PY_BASE, ['--version'], { shell: isWin });
  if (pyCheck.status !== 0) {
    fail('Python not found. Please install Python 3.10+ from https://www.python.org/downloads/');
    process.exit(1);
  }
  ok(`Python found: ${(pyCheck.stdout || pyCheck.stderr || '').toString().trim()}`);

  // Create venv if needed (PEP 668 on macOS/Linux blocks pip install into system Python)
  const venvExists = fs.existsSync(VENV_DIR);
  if (!venvExists) {
    info('Creating virtual environment (.venv)...');
    const venv = await run(PY_BASE, ['-m', 'venv', VENV_DIR], SCRIPT_DIR);
    if (venv.code !== 0) {
      fail('Failed to create virtual environment.');
      process.exit(1);
    }
    ok('Virtual environment created.');
  } else {
    ok('Virtual environment exists (.venv).');
  }

  // Install Python deps using venv pip
  const pipCmd = isWin
    ? join(VENV_DIR, 'Scripts', 'pip.exe')
    : join(VENV_DIR, 'bin', 'pip');

  if (fs.existsSync(pipCmd)) {
    info('Installing Python dependencies...');
    const install = await run(pipCmd, ['install', '-r', 'requirements.txt'], SCRIPT_DIR);
    if (install.code !== 0) {
      fail('Python dependency installation failed.');
      process.exit(1);
    }
    ok('Python dependencies installed.');

    // Upgrade pip in venv
    info('Upgrading pip...');
    const upgrade = await run(pipCmd, ['install', '--upgrade', 'pip'], SCRIPT_DIR);
    if (upgrade.code !== 0) {
      fail(`Failed to upgrade pip: ${upgrade.err}`);
      process.exit(1);
    }
    ok('pip upgraded.');

    // Install PyInstaller for building the executable
    info('Installing PyInstaller...');
    const pyinstInstall = await run(pipCmd, ['install', 'PyInstaller'], SCRIPT_DIR);
    if (pyinstInstall.code !== 0) {
      fail(`Failed to install PyInstaller: ${pyinstInstall.err}`);
      process.exit(1);
    }
    ok('PyInstaller installed.');

    // Install Playwright for browser automation
    info('Installing Playwright...');
    const playwrightInstall = await run(pipCmd, ['install', 'playwright'], SCRIPT_DIR);
    if (playwrightInstall.code !== 0) {
      fail(`Failed to install Playwright: ${playwrightInstall.err}`);
      process.exit(1);
    }
    ok('Playwright installed.');

    // Install browser binaries (platform-specific)
    const platform = isWin ? 'win32' : (process.platform === 'darwin' ? 'linux-x86_64' : 'linux-x86_64');
    info(`Downloading Playwright browsers for ${platform}...`);
    const browserInstall = await run(pipCmd, ['install', '-r', 'PlaywrightRequirements.txt'], SCRIPT_DIR);
    if (browserInstall.code !== 0) {
      fail(`Failed to install Playwright browsers: ${browserInstall.err}`);
      process.exit(1);
    }
    ok('Playwright browsers installed.');

    // Install PyPDFium2 for PDF processing
    info('Installing PyPDFium2...');
    const pdfiumInstall = await run(pipCmd, ['install', 'PyPDFium2'], SCRIPT_DIR);
    if (pdfiumInstall.code !== 0) {
      fail(`Failed to install PyPDFium2: ${pdfiumInstall.err}`);
      process.exit(1);
    }
    ok('PyPDFium2 installed.');

    // Install PyPDF for PDF manipulation
    info('Installing PyPDF...');
    const pypdfInstall = await run(pipCmd, ['install', 'PyPDF'], SCRIPT_DIR);
    if (pypdfInstall.code !== 0) {
      fail(`Failed to install PyPDF: ${pypdfInstall.err}`);
      process.exit(1);
    }
    ok('PyPDF installed.');

  } else {
    fail('pip not found in virtual environment. Try creating the venv first.');
    process.exit(1);
  }

  // Verify installations
  info('\nVerifying installations...');
  
  try {
    const pyPdfCheck = spawnSync(PY_BASE, ['-c', 'import pypdfium2; print("PyPDFium2: OK")'], { shell: isWin });
    if (pyPdfCheck.status === 0 && pyPdfCheck.stdout.includes('OK')) ok('✓ PyPDFium2'); else fail('✗ PyPDFium2 missing');
    
    const pyPpdfCheck = spawnSync(PY_BASE, ['-c', 'import pypdf; print("PyPDF: OK")'], { shell: isWin });
    if (pyPpdfCheck.status === 0 && pyPpdfCheck.stdout.includes('OK')) ok('✓ PyPDF'); else fail('✗ PyPDF missing');
    
    const pyinstCheck = spawnSync(PY_BASE, ['-c', 'import PyInstaller; print("PyInstaller: OK")'], { shell: isWin });
    if (pyinstCheck.status === 0 && pyinstCheck.stdout.includes('OK')) ok('✓ PyInstaller'); else fail('✗ PyInstaller missing');
    
    const playwrightCheck = spawnSync(PY_BASE, ['-c', 'import playwright; print("Playwright: OK")'], { shell: isWin });
    if (playwrightCheck.status === 0 && playwrightCheck.stdout.includes('OK')) ok('✓ Playwright'); else fail('✗ Playwright missing');

  } catch (err) {
    fail(`Verification error: ${err.message}`);
  }

  console.log('\n🎉 Setup complete!');
  console.log('   Run "npm run start" to start the server.');
  console.log('   Or build with "npm run build" for PyInstaller package.\n');
}

main().catch(err => {
  fail(`Setup failed: ${err.message}`);
  process.exit(1);
});
