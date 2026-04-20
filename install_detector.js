/**
 * Installation Detection System
 * 
 * Detects and validates all required dependencies for the PDF Cleaner app.
 * Works offline with pre-built packages, provides detailed status reports,
 * and suggests auto-repair actions where possible.
 */

import { spawn } from 'child_process';
import { promises as fs, existsSync } from 'fs';
import path from 'path';
import os from 'os';

const __dirname = process.cwd();
const VENV_DIR = path.join(__dirname, '.venv');

/**
 * Component registry - defines what needs to be checked for each dependency
 */
const COMPONENTS = {
  // Core Node.js dependencies
  'node-express': {
    type: 'npm',
    name: 'Express Web Server',
    package: 'express',
    required: true,
    fallback: null,
    description: 'Web server framework for the UI'
  },
  'node-multer': {
    type: 'npm',
    name: 'Multer File Upload',
    package: 'multer',
    required: true,
    fallback: null,
    description: 'PDF file upload handling'
  },
  'node-pdf-lib': {
    type: 'npm',
    name: 'PDF-Lib',
    package: 'pdf-lib',
    required: false,
    fallback: null,
    description: 'Pure JS PDF manipulation (optional)'
  },

  // Core Python dependencies
  'py-pikepdf': {
    type: 'python',
    name: 'PikePDF',
    package: 'pikepdf',
    required: true,
    fallback: null,
    description: 'PDF structure tree manipulation'
  },
  'py-pillow': {
    type: 'python',
    name: 'Pillow (Image Processing)',
    package: 'pillow',
    required: false,
    fallback: null,
    description: 'Image processing for alt text generation'
  },
  'py-requests': {
    type: 'python',
    name: 'Requests HTTP Client',
    package: 'requests',
    required: true,
    fallback: null,
    description: 'Adobe API HTTP client'
  },
  'py-win32': {
    type: 'python',
    name: 'PyWin32 (Windows COM)',
    package: 'pywin32',
    required: true,
    fallback: null,
    description: 'Acrobat COM automation (Windows only)'
  },

  // System tools
  'sys-python': {
    type: 'system',
    name: 'Python Interpreter',
    package: null,
    required: true,
    fallback: ['python3', 'python'],
    description: 'Python interpreter for PDF processing scripts'
  },
  'sys-node': {
    type: 'system',
    name: 'Node.js Runtime',
    package: null,
    required: true,
    fallback: ['node'],
    description: 'Node.js runtime environment'
  },
  'sys-npm': {
    type: 'system',
    name: 'NPM Package Manager',
    package: null,
    required: false,
    fallback: ['npm'],
    description: 'Node.js package manager (for dependency installation)'
  },

  // Optional system tools
  'sys-acrobat': {
    type: 'system',
    name: 'Adobe Acrobat Pro',
    package: null,
    required: false,
    fallback: ['acrobat.exe'],
    description: 'Local Adobe Acrobat for COM-based auto-tagging (Windows)'
  }
};

/**
 * Platform-specific detection logic
 */
const PLATFORM_CHECKS = {
  win32: {
    acrobatPaths: [
      'C:\\Program Files\\Adobe\\Acrobat DC\\Acrobat\\acrobat.exe',
      'C:\\Program Files (x86)\\Adobe\\Acrobat DC\\Acrobat\\acrobat.exe',
      'C:\\Program Files\\Adobe\\Acrobat\\Acrobat\\acrobat.exe'
    ],
    pythonPaths: [
      '.venv\\Scripts\\python.exe',
      'C:\\Python310\\python.exe',
      'C:\\Python311\\python.exe',
      'C:\\Python312\\python.exe'
    ]
  },
  darwin: {
    acrobatPaths: [
      '/Applications/Adobe Acrobat DC.app/Contents/MacOS/acrobat',
      '/Applications/Adobe Acrobat Pro.app/Contents/MacOS/acrobat'
    ],
    pythonPaths: [
      '.venv/bin/python',
      '/opt/homebrew/bin/python3',
      '/usr/local/bin/python3',
      'python3'
    ]
  }
};

/**
 * Main detection function - returns comprehensive status report
 */
export async function detectInstallation() {
  const report = {
    ready: false,
    timestamp: new Date().toISOString(),
    platform: os.platform(),
    components: {},
    warnings: [],
    errors: [],
    suggestions: []
  };

  // Phase 1: Check system tools
  const sysPython = await checkSystemTool('sys-python', 'python3');
  const sysNode = await checkSystemTool('sys-node', 'node');
  const sysNpm = await checkSystemTool('sys-npm', 'npm');
  
  // Phase 2: Check npm dependencies
  for (const key of ['node-express', 'node-multer', 'node-pdf-lib']) {
    report.components[key] = await checkNpmDependency(COMPONENTS[key]);
  }
  
  // Phase 3: Check Python dependencies
  for (const key of ['py-requests', 'py-pikepdf', 'py-pillow']) {
    report.components[key] = await checkPythonDependency(COMPONENTS[key], sysPython.path);
  }
  
  if (os.platform() === 'win32') {
    const pyWin32 = await checkPythonDependency(COMPONENTS['py-win32'], sysPython.path);
    report.components['py-win32'] = pyWin32;
    if (!pyWin32.ok) {
      report.warnings.push('PyWin32 not found - some Windows-specific features may be limited');
    }
  }

  // Phase 4: Check Adobe Acrobat (if available) - graceful, non-blocking check
  const acrobatCheck = async () => {
    try {
      // Check if acrobat.exe exists by attempting to spawn it with a timeout
      return new Promise((resolve) => {
        let resolved = false;
        
        const child = spawn('acrobat.exe', ['--version'], { windowsHide: true });
        
        const timeout = setTimeout(() => {
          if (!resolved) resolve({ ok: false, found: false, error: 'timeout' });
        }, 2000);
        
        child.on('error', (err) => {
          if (!resolved && err.code === 'ENOENT') {
            clearTimeout(timeout);
            resolve({ ok: false, found: false, error: 'not installed' });
            resolved = true;
          }
        });
        
        child.on('close', (code) => {
          clearTimeout(timeout);
          if (!resolved) resolve(code === 0 || code === undefined ? { ok: true, found: true } : { ok: false, found: false, error: `exit ${code}` });
          resolved = true;
        });
      });
    } catch (err) {
      return { ok: false, found: false, error: 'spawn failed' };
    }
  };

  const acrobat = await acrobatCheck();
  report.components['sys-acrobat'] = acrobat;

  // Phase 5: Determine overall readiness
  const requiredOk = Object.entries(report.components)
    .filter(([key, comp]) => COMPONENTS[key].required === true && key.startsWith('py-') || 
                              key.startsWith('node-') && !COMPONENTS[key].package?.includes('pdf-lib'))
    .every(([, comp]) => comp.ok);
  
  report.ready = requiredOk;
  report.hasErrors = report.errors.length > 0;
  report.hasWarnings = report.warnings.length > 0;

  // Add suggestions based on findings
  if (report.components['node-express'].ok === false) {
    report.suggestions.push({
      type: 'info',
      message: 'Run `npm install` to install core Node.js dependencies'
    });
  }
  
  if (report.components['py-pikepdf'].ok === false) {
    report.suggestions.push({
      type: 'warning',
      message: 'Python virtual environment may need setup. Run `pip install -r requirements.txt`'
    });
  }

  return report;
}

/**
 * Check a system-level tool (python, node, npm, etc.)
 */
async function checkSystemTool(key, cmd) {
  const component = COMPONENTS[key];
  
  try {
    // Try the primary command first
    let path = null;
    if (process.platform === 'win32') {
      try {
        await runCommand(cmd, ['--version']);
        path = cmd;
      } catch {}
    } else {
      try {
        await runCommand(cmd, ['--version']);
        path = cmd;
      } catch {}
    }

    if (!path && component.fallback) {
      // Try fallback paths
      for (const fallback of component.fallback) {
        try {
          await runCommand(fallback, ['--version']);
          path = fallback;
          break;
        } catch {}
      }
    }

    if (!path) {
      return {
        ...component,
        ok: false,
        found: false,
        version: null,
        location: null
      };
    }

    const version = await getVersion(path);

    return {
      ...component,
      ok: true,
      found: true,
      path,
      version,
      detectedAt: new Date().toISOString()
    };
  } catch (err) {
    return {
      ...component,
      ok: false,
      found: false,
      error: err.message
    };
  }
}

/**
 * Check an npm package dependency
 */
async function checkNpmDependency(component) {
  try {
    // Try to find the package in node_modules
    const pkgPath = path.join(__dirname, 'node_modules', component.package, 'package.json');
    if (existsSync(pkgPath)) {
      const pkgJson = JSON.parse(await fs.readFile(pkgPath, 'utf-8'));
      return {
        ...component,
        ok: true,
        found: true,
        version: pkgJson.version || 'unknown',
        location: pkgPath
      };
    }

    // Try to get version via npm list (requires internet for first-time check)
    try {
      const output = await runCommand('npm', ['list', component.package, '--depth=0'], __dirname);
      const match = output.match(/[^@]+@(\d+\.\d+\.\d+)/);
      return {
        ...component,
        ok: true,
        found: true,
        version: match ? match[1] : 'unknown',
        location: null
      };
    } catch {}

    // Package not installed
    return {
      ...component,
      ok: false,
      found: false,
      error: `${component.package} not found in node_modules`
    };
  } catch (err) {
    return {
      ...component,
      ok: false,
      found: false,
      error: err.message
    };
  }
}

/**
 * Check a Python package dependency
 */
async function checkPythonDependency(component, pythonPath) {
  try {
    // Try import via python -c "import module"
    const result = await runCommand(pythonPath, ['-m', 'pip', 'show', component.package], __dirname);
    
    if (result.includes('Name:')) {
      const match = result.match(/Version:\s+(.+)/);
      const version = match ? match[1].trim() : 'unknown';
      return {
        ...component,
        ok: true,
        found: true,
        version,
        pythonPath
      };
    }

    // Try direct import as fallback
    await runCommand(pythonPath, ['-c', `import ${component.package}`], __dirname);
    return {
      ...component,
      ok: true,
      found: true,
      version: 'unknown',
      pythonPath
    };
  } catch (err) {
    // Package not found - check if it's in requirements.txt
    try {
      const reqContent = await fs.readFile(path.join(__dirname, 'requirements.txt'), 'utf-8');
      const inRequirements = reqContent.includes(component.package);
      return {
        ...component,
        ok: false,
        found: false,
        error: `${component.package} not installed`,
        inRequirements
      };
    } catch {}

    return {
      ...component,
      ok: false,
      found: false,
      error: err.message
    };
  }
}

/**
 * Run a command and get its output (graceful error handling)
 */
async function runCommand(cmd, args = [], cwd = __dirname) {
  return new Promise((resolve, reject) => {
    const proc = spawn(cmd, args, {
      cwd,
      shell: process.platform === 'win32' && cmd === 'npm',
      stdio: ['pipe', 'pipe', 'ignore'] // Ignore stderr to avoid errors for optional tools
    });

    let output = '';
    proc.stdout.on('data', (data) => {
      output += data.toString();
    });

    proc.stderr.on('data', (data) => {
      output += data.toString();
    });

    proc.on('close', (code) => {
      if (code === 0 || code === undefined) resolve(output); // undefined = success even without explicit exit code
      else reject(new Error(`${cmd} ${args.join(' ')} exited with code ${code}`));
    });

    proc.on('error', reject);
  });
}

/**
 * Get version string from a command (graceful error handling)
 */
async function getVersion(cmd, args = ['--version']) {
  try {
    const output = await runCommand(cmd, args);
    return output.trim().split('\n')[0];
  } catch (err) {
    // Command not found or failed - return 'unknown' instead of throwing
    return 'unknown';
  }
}

/**
 * Export simplified status for UI consumption (JSON endpoint)
 */
export async function getStatus() {
  const report = await detectInstallation();
  
  // Simplified view for quick UI display
  return {
    ready: report.ready,
    components: Object.entries(report.components).map(([key, comp]) => ({
      key,
      name: comp.name,
      ok: comp.ok,
      found: comp.found,
      version: comp.version || 'unknown',
      required: COMPONENTS[key].required
    })),
    warnings: report.warnings,
    errors: report.errors,
    suggestions: report.suggestions
  };
}

/**
 * Helper to install missing dependencies (used by /api/setup endpoint)
 */
export async function autoInstallDependencies() {
  const results = {
    npm: { success: false, packages: [] },
    python: { success: false, packages: [], error: null }
  };

  // Install npm dependencies
  try {
    await runCommand('npm', ['install'], __dirname);
    results.npm.success = true;
    results.npm.packages = ['express', 'multer', 'pdf-lib'];
  } catch (err) {
    results.npm.error = err.message;
  }

  // Install Python dependencies
  try {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    
    // Check if venv exists, create if not
    const venvPython = path.join(__dirname, '.venv', 'Scripts', 'python.exe');
    const exists = existsSync(venvPython);
    
    if (!exists) {
      await runCommand(pythonCmd, ['-m', 'venv', '.venv'], __dirname);
    }

    // Install from requirements.txt
    const pipCmd = path.join(__dirname, '.venv', 'Scripts', 'pip.exe');
    const existsPip = existsSync(pipCmd) || process.platform !== 'win32';
    
    await runCommand(
      process.platform === 'win32' ? pipCmd : pythonCmd,
      ['-m', 'pip', 'install', '-r', 'requirements.txt'],
      __dirname
    );
    results.python.success = true;
  } catch (err) {
    results.python.error = err.message;
  }

  return results;
}
