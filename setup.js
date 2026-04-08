#!/usr/bin/env node
/**
 * Setup script - installs Python dependencies
 */

import { spawn } from 'child_process';
import chalk from 'chalk';
import ora from 'ora';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SCRIPT_DIR = __dirname;

const CONFIG = {
  pythonCmd: process.platform === 'win32' ? 'python' : 'python3',
  venvPath: join(SCRIPT_DIR, '.venv')
};

async function main() {
  console.log(chalk.bold('\n🔧 PDF ADA Processor - Setup\n'));
  
  // Check Python
  const pythonCheck = spawn(CONFIG.pythonCmd, ['--version']);
  
  await new Promise((resolve) => {
    pythonCheck.on('error', () => {
      console.log(chalk.red('✗ Python not found. Please install Python 3.10+'));
      process.exit(1);
    });
    pythonCheck.on('close', (code) => {
      if (code === 0) {
        console.log(chalk.green('✓ Python found'));
      } else {
        console.log(chalk.red('✗ Python check failed'));
        process.exit(1);
      }
      resolve();
    });
  });
  
  // Check if venv exists
  const hasVenv = fs.existsSync(join(SCRIPT_DIR, '.venv'));
  
  if (!hasVenv) {
    const spinner = ora('Creating virtual environment').start();
    
    await new Promise((resolve) => {
      const venv = spawn(CONFIG.pythonCmd, ['-m', 'venv', '.venv'], {
        cwd: SCRIPT_DIR,
        stdio: 'pipe'
      });
      
      venv.on('close', (code) => {
        if (code === 0) {
          spinner.succeed(chalk.green('Virtual environment created'));
          resolve(true);
        } else {
          spinner.fail(chalk.red('Failed to create venv'));
          resolve(false);
        }
      });
    });
  } else {
    console.log(chalk.green('✓ Virtual environment exists'));
  }
  
  // Install dependencies
  const spinner = ora('Installing Python dependencies').start();
  
  const pipCmd = process.platform === 'win32' 
    ? join(SCRIPT_DIR, '.venv', 'Scripts', 'pip')
    : join(SCRIPT_DIR, '.venv', 'bin', 'pip');
  
  await new Promise((resolve) => {
    const install = spawn(pipCmd, ['install', '-r', 'requirements.txt'], {
      cwd: SCRIPT_DIR,
      stdio: 'pipe'
    });
    
    let output = '';
    install.stdout.on('data', (data) => { output += data.toString(); });
    install.stderr.on('data', (data) => { output += data.toString(); });
    
    install.on('close', (code) => {
      if (code === 0) {
        spinner.succeed(chalk.green('Dependencies installed'));
        resolve(true);
      } else {
        spinner.fail(chalk.red('Installation failed'));
        console.error(output);
        resolve(false);
      }
    });
  });
  
  // Create directories
  const dirs = [
    'input_pdfs',
    'staged_compliance',
    'assessment_results',
    'vision_results',
    'auto_fixed',
    'fix_logs'
  ];
  
  console.log(chalk.cyan('\nCreating directories:'));
  for (const dir of dirs) {
    const dirPath = join(SCRIPT_DIR, dir);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
      console.log(chalk.green(`  ✓ ${dir}/`));
    } else {
      console.log(chalk.dim(`  - ${dir}/ (exists)`));
    }
  }
  
  console.log(chalk.bold.green('\n✅ Setup Complete!\n'));
  console.log(chalk.cyan('Usage:'));
  console.log('  npm run assess     # Run accessibility assessment');
  console.log('  npm run fix        # Apply auto-fixes');
  console.log('  npm run vision     # Generate AI alt text');
  console.log('  npm run process    # Process PDFs');
  console.log('  npm run pipeline   # Run full pipeline\n');
}

main().catch((err) => {
  console.error(chalk.red('Setup failed:'), err);
  process.exit(1);
});
