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

  // Create venv if needed
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

  // Install Python deps
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
  } else {
    fail('pip not found in virtual environment.');
    process.exit(1);
  }

  // Create directories
  const dirs = [
    'input_pdfs', 'done', 'needs_review', 'adobe_tagged',
    'auto_fixed', 'adobe_fixed', 'adobe_reports',
    'assessment_results', 'pipeline_results', 'fix_logs',
    'staged_compliance'
  ];

  log('\n📁 Ensuring directories:');
  for (const dir of dirs) {
    const dirPath = join(SCRIPT_DIR, dir);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
      ok(`  ${dir}/`);
    } else {
      skip(`  ${dir}/ (exists)`);
    }
  }

  console.log('\n✅ Setup Complete!\n');
  console.log('Next steps:');
  console.log('  npm start          # Start the web UI');
  console.log('  node server.js     # Same as above\n');
}

main().catch((err) => {
  fail(`Setup failed: ${err.message}`);
  process.exit(1);
});
