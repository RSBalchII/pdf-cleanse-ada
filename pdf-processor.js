#!/usr/bin/env node
/**
 * PDF ADA Compliance Processor
 * 
 * Lightweight Node.js wrapper that orchestrates Python tools for:
 * - Accessibility assessment
 * - Auto-fixes for metadata
 * - AI vision-based alt text generation
 * 
 * Bundles Python subprocess calls with progress UI
 */

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { spawn } from 'child_process';
import fs from 'fs';
import chalk from 'chalk';
import { Command } from 'commander';
import ora from 'ora';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SCRIPT_DIR = __dirname;

// Python scripts
const PYTHON_SCRIPTS = {
  assess: 'compliance_checker.py',
  fix: 'ada_auto_fix.py',
  vision: 'vision_alt_text.py',
  process: 'ada_compliance_processor.py'
};

// Configuration
const CONFIG = {
  pythonCmd: process.platform === 'win32' ? 'python' : 'python3',
  venvPath: join(SCRIPT_DIR, '.venv'),
  modelsDir: join(SCRIPT_DIR, '..', 'models'),
  inputDir: join(SCRIPT_DIR, 'input_pdfs'),
  outputDir: join(SCRIPT_DIR, 'staged_compliance')
};

/**
 * Check if Python environment is ready
 */
async function checkPython() {
  const spinner = ora('Checking Python environment').start();
  
  return new Promise((resolve) => {
    const check = spawn(CONFIG.pythonCmd, ['--version']);
    
    check.on('error', (err) => {
      spinner.fail(chalk.red('Python not found. Please install Python 3.10+'));
      resolve(false);
    });
    
    check.on('close', (code) => {
      if (code === 0) {
        spinner.succeed(chalk.green('Python found'));
        resolve(true);
      } else {
        spinner.fail(chalk.red('Python check failed'));
        resolve(false);
      }
    });
  });
}

/**
 * Check if dependencies are installed
 */
async function checkDependencies() {
  const spinner = ora('Checking Python dependencies').start();
  
  return new Promise((resolve) => {
    const check = spawn(CONFIG.pythonCmd, ['-c', 'import pikepdf, PIL, requests']);
    
    check.on('error', () => {
      spinner.fail(chalk.red('Dependencies missing'));
      resolve(false);
    });
    
    check.on('close', (code) => {
      if (code === 0) {
        spinner.succeed(chalk.green('Dependencies OK'));
        resolve(true);
      } else {
        spinner.warn(chalk.yellow('Dependencies missing. Run: npm run setup'));
        resolve(false);
      }
    });
  });
}

/**
 * Run a Python script with arguments
 */
function runPythonScript(scriptName, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    const scriptPath = join(SCRIPT_DIR, PYTHON_SCRIPTS[scriptName]);
    
    if (!fs.existsSync(scriptPath)) {
      reject(new Error(`Script not found: ${scriptPath}`));
      return;
    }
    
    const pythonArgs = [scriptPath, ...args];
    const proc = spawn(CONFIG.pythonCmd, pythonArgs, {
      cwd: SCRIPT_DIR,
      stdio: 'inherit'
    });
    
    proc.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true });
      } else {
        reject(new Error(`Process exited with code ${code}`));
      }
    });
    
    proc.on('error', reject);
  });
}

/**
 * Assess PDFs for accessibility issues
 */
async function cmdAssess(options) {
  console.log(chalk.bold('\n📋 PDF Accessibility Assessment\n'));
  
  try {
    await runPythonScript('assess');
    console.log(chalk.green('\n✓ Assessment complete!\n'));
    console.log(chalk.cyan('Results:'));
    console.log(`  - CSV: ${join(SCRIPT_DIR, 'assessment_results', 'accessibility_assessment.csv')}`);
    console.log(`  - JSON: ${join(SCRIPT_DIR, 'assessment_results', 'detailed_report.json')}\n`);
  } catch (err) {
    console.error(chalk.red(`\n✗ Assessment failed: ${err.message}\n`));
    process.exit(1);
  }
}

/**
 * Apply auto-fixes to PDFs
 */
async function cmdFix(options) {
  console.log(chalk.bold('\n🔧 Applying Auto-Fixes\n'));
  
  try {
    await runPythonScript('fix');
    console.log(chalk.green('\n✓ Auto-fix complete!\n'));
    console.log(chalk.cyan('Fixed PDFs:'));
    console.log(`  - ${join(SCRIPT_DIR, 'auto_fixed')}\n`);
  } catch (err) {
    console.error(chalk.red(`\n✗ Auto-fix failed: ${err.message}\n`));
    process.exit(1);
  }
}

/**
 * Generate AI alt text for images
 */
async function cmdVision(options) {
  console.log(chalk.bold('\n👁️  AI Vision Alt Text Generation\n'));
  
  const args = [];
  
  if (options.backend) {
    args.push('--backend', options.backend);
  }
  
  if (options.model) {
    args.push('--model', options.model);
  }
  
  if (options.azureKey) {
    args.push('--azure-key', options.azureKey);
  }
  
  if (options.azureEndpoint) {
    args.push('--azure-endpoint', options.azureEndpoint);
  }
  
  try {
    await runPythonScript('vision', args);
    console.log(chalk.green('\n✓ Vision processing complete!\n'));
    console.log(chalk.cyan('Results:'));
    console.log(`  - ${join(SCRIPT_DIR, 'vision_results')}\n`);
  } catch (err) {
    console.error(chalk.red(`\n✗ Vision processing failed: ${err.message}\n`));
    process.exit(1);
  }
}

/**
 * Process PDFs (metadata injection + triage)
 */
async function cmdProcess(options) {
  console.log(chalk.bold('\n📄 PDF Compliance Processing\n'));
  
  try {
    await runPythonScript('process');
    console.log(chalk.green('\n✓ Processing complete!\n'));
    console.log(chalk.cyan('Output:'));
    console.log(`  - ${join(SCRIPT_DIR, 'staged_compliance')}\n`);
  } catch (err) {
    console.error(chalk.red(`\n✗ Processing failed: ${err.message}\n`));
    process.exit(1);
  }
}

/**
 * Run the enhanced pipeline with looped verification and sorting
 */
async function cmdPipeline(options) {
  console.log(chalk.bold('\n🚀 Enhanced ADA Compliance Pipeline\n'));
  console.log(chalk.dim('Steps: assess → fix → re-assess → adobe auto → verify → sort → report\n'));

  const args = [];

  if (options.skipAdobe) {
    args.push('--skip-adobe');
  }

  if (options.skipVision) {
    args.push('--skip-vision');
  }

  if (options.file) {
    args.push('--file', options.file);
  }

  try {
    await runPythonScript('pipeline', args);
  } catch (err) {
    console.error(chalk.red(`\n✗ Pipeline failed: ${err.message}\n`));
    process.exit(1);
  }
}

/**
 * Full pipeline: assess → fix → vision → process (legacy)
 */
async function cmdPipelineLegacy(options) {
  console.log(chalk.bold('\n🚀 Full ADA Compliance Pipeline (Legacy)\n'));
  console.log(chalk.dim('This will: assess → auto-fix → generate alt text → process\n'));
  
  const steps = [
    { name: 'Assessment', fn: cmdAssess },
    { name: 'Auto-Fix', fn: cmdFix },
    { name: 'Vision (optional)', fn: options.vision ? cmdVision : null },
    { name: 'Processing', fn: cmdProcess }
  ];
  
  for (const step of steps) {
    if (!step.fn) continue;
    
    console.log(chalk.bold(`\n→ Step: ${step.name}`));
    console.log(chalk.dim('─'.repeat(50)));
    
    try {
      await step.fn(options);
    } catch (err) {
      console.error(chalk.red(`Step "${step.name}" failed: ${err.message}`));
      const cont = await askContinue();
      if (!cont) {
        console.log(chalk.yellow('\nPipeline stopped by user.\n'));
        process.exit(1);
      }
    }
  }
  
  console.log(chalk.bold.green('\n✅ Pipeline Complete!\n'));
  printSummary();
}

/**
 * Ask user if they want to continue after error
 */
async function askContinue() {
  return new Promise((resolve) => {
    console.log(chalk.yellow('\nContinue anyway? [y/N] '));
    process.stdin.once('data', (data) => {
      resolve(data.toString().trim().toLowerCase() === 'y');
    });
  });
}

/**
 * Print summary of outputs
 */
function printSummary() {
  console.log(chalk.bold('📊 Summary of Outputs\n'));
  console.log(chalk.cyan('Directory Structure:'));
  console.log(`
  pdf-cleanse-ada/
  ├── input_pdfs/           # Drop PDFs here
  ├── staged_compliance/    # Processed PDFs
  ├── auto_fixed/           # Auto-corrected PDFs
  ├── assessment_results/   # Accessibility reports
  ├── vision_results/       # AI alt text results
  └── fix_logs/             # Change logs
  `);
  
  console.log(chalk.cyan('Quick Commands:'));
  console.log(`
  npm run assess           # Run accessibility assessment
  npm run fix              # Apply auto-fixes
  npm run vision           # Generate AI alt text
  npm run process          # Process PDFs
  npm start                # Show help
  `);
}

/**
 * Setup command
 */
async function cmdSetup() {
  console.log(chalk.bold('\n🔧 Setting up PDF ADA Processor\n'));
  
  // Check Python
  const hasPython = await checkPython();
  if (!hasPython) {
    console.log(chalk.yellow('\nInstall Python 3.10+ from https://python.org\n'));
    process.exit(1);
  }
  
  // Install dependencies
  const spinner = ora('Installing Python dependencies').start();
  
  await new Promise((resolve) => {
    const install = spawn(CONFIG.pythonCmd, ['-m', 'pip', 'install', '-r', 'requirements.txt'], {
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
  const dirs = ['input_pdfs', 'staged_compliance', 'assessment_results', 'vision_results', 'auto_fixed', 'fix_logs'];
  
  for (const dir of dirs) {
    const dirPath = join(SCRIPT_DIR, dir);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
      console.log(chalk.green(`  ✓ Created: ${dir}/`));
    }
  }
  
  console.log(chalk.bold.green('\n✅ Setup Complete!\n'));
  console.log(chalk.cyan('Next steps:'));
  console.log('  1. Drop PDFs into input_pdfs/');
  console.log('  2. Run: npm run assess\n');
}

/**
 * Main CLI
 */
const program = new Command();

program
  .name('pdf-ada')
  .description('PDF ADA Compliance Processor')
  .version('1.0.0');

program
  .command('assess')
  .description('Run accessibility assessment on PDFs')
  .action(cmdAssess);

program
  .command('fix')
  .description('Apply auto-fixes to PDFs')
  .action(cmdFix);

program
  .command('vision')
  .description('Generate AI alt text for images')
  .option('-b, --backend <type>', 'Vision backend: ollama, azure, tesseract', 'ollama')
  .option('-m, --model <name>', 'Model name for ollama', 'llava')
  .option('--azure-key <key>', 'Azure subscription key')
  .option('--azure-endpoint <url>', 'Azure endpoint URL')
  .action(cmdVision);

program
  .command('process')
  .description('Process PDFs (metadata + triage)')
  .action(cmdProcess);

program
  .command('pipeline')
  .description('Run enhanced pipeline: assess → fix → re-assess → adobe → verify → sort')
  .option('--file <path>', 'Process specific PDF file')
  .option('--skip-adobe', 'Skip Adobe Acrobat Pro automation')
  .option('--skip-vision', 'Skip AI alt text generation')
  .action(cmdPipeline);

program
  .command('pipeline:legacy')
  .description('Run legacy pipeline: assess → fix → vision → process')
  .option('--vision', 'Include vision processing in pipeline')
  .action(cmdPipelineLegacy);

program
  .command('setup')
  .description('Setup Python environment and dependencies')
  .action(cmdSetup);

program
  .command('summary')
  .description('Show output summary')
  .action(printSummary);

// Default help
if (!process.argv.slice(2).length) {
  program.help();
}

program.parse();
