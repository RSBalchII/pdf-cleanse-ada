#!/usr/bin/env node
/**
 * PDF ADA Processor - Launcher
 * 
 * This launcher ensures dependencies are installed and starts the server.
 * Non-tech users just double-click this file - everything else is automatic!
 */

import { spawn } from 'child_process';
import { existsSync } from 'fs';
import { join } from 'path';
import chalk from 'chalk';

const PROJECT_DIR = process.cwd();

async function ensureDependencies() {
  // Check if node_modules exists
  const hasNodeModules = existsSync(join(PROJECT_DIR, 'node_modules'));
  
  if (!hasNodeModules) {
    console.log(chalk.yellow('⚠️  Dependencies not found. Installing...\n'));
    
    return new Promise((resolve, reject) => {
      const npm = spawn('npm', ['install'], { 
        cwd: PROJECT_DIR,
        shell: true
      });
      
      npm.stdout.on('data', (data) => {
        process.stdout.write(data);
      });
      
      npm.stderr.on('data', (data) => {
        process.stdout.write(data);
      });
      
      npm.on('close', (code) => {
        if (code === 0) {
          console.log(chalk.green('✓ Dependencies installed!\n'));
          resolve();
        } else {
          reject(new Error(`npm install failed with code ${code}`));
        }
      });
    });
  }
}

async function main() {
  try {
    await ensureDependencies();
    
    console.log(chalk.bold('\n📄 Starting PDF ADA Compliance Processor...\n'));
    
    // Start the server
    const server = spawn('node', ['server.js'], {
      cwd: PROJECT_DIR,
      stdio: 'inherit'
    });
    
  } catch (err) {
    console.error(chalk.red(`❌ ${err.message}\n`));
    process.exit(1);
  }
}

main();
