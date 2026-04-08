/**
 * PDF ADA Compliance — Web Server
 *
 * Lightweight Express server that:
 * 1. Auto-installs deps on first start
 * 2. Serves the HTML UI
 * 3. Accepts PDF file uploads (drag-drop or browse)
 * 4. Runs the compliance pipeline via pdf-tools.js
 * 5. Streams terminal output to UI via SSE
 * 6. Returns downloadable results (fixed PDFs + CSV report)
 */

import express from 'express';
import multer from 'multer';
import { promises as fs, createReadStream, existsSync } from 'fs';
import { spawn, execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { EventEmitter } from 'events';

import { processPdf, generateCsvReport, ensureDirs, INPUT_DIR, DONE_DIR, NEEDS_REVIEW_DIR, RESULTS_DIR, AUTO_TAGGED_DIR } from './pdf-tools.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3456;

// SSE event emitter for streaming terminal output
const terminalEmitter = new EventEmitter();

function terminalLog(message, type = 'info') {
  const ts = new Date().toLocaleTimeString();
  const line = `[${ts}] ${message}`;
  terminalEmitter.emit('terminal', { message: line, type });
}

// ── Middleware ──────────────────────────────────────────────
app.use(express.static(__dirname));
app.use(express.json());

// Multer config: store uploads in input_pdfs/
const storage = multer.diskStorage({
  destination: async (req, file, cb) => {
    await ensureDirs();
    cb(null, INPUT_DIR);
  },
  filename: (req, file, cb) => {
    // Keep original filename
    cb(null, file.originalname);
  }
});
const upload = multer({ storage, fileFilter: (req, file, cb) => {
  if (file.mimetype === 'application/pdf' || file.originalname.endsWith('.pdf')) {
    cb(null, true);
  } else {
    cb(new Error('Only PDF files are allowed'));
  }
}});

// ── Routes ──────────────────────────────────────────────────

// GET / — Serve the UI
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// SSE endpoint: /terminal-stream
app.get('/terminal-stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  // Send initial message
  res.write(`data: ${JSON.stringify({ message: 'Terminal connected', type: 'info' })}\n\n`);

  const onTerminal = (data) => {
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  };

  terminalEmitter.on('terminal', onTerminal);

  req.on('close', () => {
    terminalEmitter.off('terminal', onTerminal);
  });
});

// POST /api/setup — Install dependencies
app.post('/api/setup', async (req, res) => {
  terminalLog('Starting dependency setup...', 'accent');

  try {
    // Install npm deps
    terminalLog('Installing npm packages...', 'info');
    await runCommand('npm', ['install'], __dirname);

    // Install Python deps (optional — only if Python is available)
    terminalLog('Checking Python environment...', 'info');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    try {
      await runCommand(pythonCmd, ['--version'], __dirname);
      terminalLog('Python found. Installing Python packages...', 'info');
      await runCommand(pythonCmd, ['-m', 'pip', 'install', '-r', 'requirements.txt'], __dirname);
    } catch {
      terminalLog('Python not found — skipping Python dependencies. Core features will still work.', 'warning');
    }

    // Ensure directories
    await ensureDirs();

    terminalLog('Setup complete! All dependencies installed.', 'success');
    res.json({ success: true, message: 'Setup complete' });
  } catch (err) {
    terminalLog(`Setup failed: ${err.message}`, 'error');
    res.status(500).json({ success: false, error: err.message });
  }
});

// POST /api/upload — Upload PDF files
app.post('/api/upload', upload.array('pdfs', 50), async (req, res) => {
  const files = req.files;
  if (!files || files.length === 0) {
    return res.status(400).json({ error: 'No PDF files uploaded' });
  }

  terminalLog(`Uploaded ${files.length} PDF(s):`, 'success');
  files.forEach(f => terminalLog(`  ✓ ${f.originalname} (${(f.size / 1024).toFixed(1)} KB)`, 'info'));

  res.json({ success: true, count: files.length, files: files.map(f => f.originalname) });
});

// GET /api/files — List uploaded PDFs
app.get('/api/files', async (req, res) => {
  await ensureDirs();
  try {
    const files = await fs.readdir(INPUT_DIR);
    const pdfs = files.filter(f => f.endsWith('.pdf'));
    const stats = await Promise.all(pdfs.map(async (name) => {
      const stat = await fs.stat(path.join(INPUT_DIR, name));
      return { name, size: stat.size };
    }));
    res.json({ files: stats });
  } catch {
    res.json({ files: [] });
  }
});

// DELETE /api/files/:name — Delete an uploaded PDF
app.delete('/api/files/:name', async (req, res) => {
  const filePath = path.join(INPUT_DIR, req.params.name);
  try {
    await fs.unlink(filePath);
    terminalLog(`Deleted: ${req.params.name}`, 'warning');
    res.json({ success: true });
  } catch {
    res.status(404).json({ error: 'File not found' });
  }
});

// POST /api/process — Run the pipeline on uploaded PDFs
app.post('/api/process', async (req, res) => {
  const { fileNames } = req.body; // optional: specific files to process

  await ensureDirs();

  try {
    const allFiles = await fs.readdir(INPUT_DIR);
    const pdfs = fileNames
      ? allFiles.filter(f => fileNames.includes(f))
      : allFiles.filter(f => f.endsWith('.pdf'));

    if (pdfs.length === 0) {
      terminalLog('No PDF files to process. Upload files first.', 'warning');
      return res.json({ success: false, message: 'No PDFs found' });
    }

    terminalLog('━'.repeat(60), 'accent');
    terminalLog('Starting ADA Compliance Pipeline', 'bold');
    terminalLog('━'.repeat(60), 'accent');

    const results = [];

    for (const pdfName of pdfs) {
      const pdfPath = path.join(INPUT_DIR, pdfName);

      terminalLog(`\n[1/3] Reading: ${pdfName}`, 'info');
      const result = await processPdf(pdfPath, pdfName);

      terminalLog(`  Title: ${result.info.title || '(none)'}`, result.info.title ? 'success' : 'error');
      terminalLog(`  Language: ${result.info.lang || '(none)'}`, result.info.lang ? 'success' : 'warning');
      terminalLog(`  Tagged: ${result.info.isTagged}`, result.info.isTagged ? 'success' : 'error');
      terminalLog(`  Marked: ${result.info.isMarked}`, result.info.isMarked ? 'success' : 'warning');
      terminalLog(`  Pages: ${result.info.pageCount} | Images: ${result.info.imageCount}`, 'info');

      if (result.fixesApplied.length > 0) {
        terminalLog(`  Fixes applied:`, 'success');
        result.fixesApplied.forEach(f => terminalLog(`    ✓ ${f}`, 'success'));
      }

      terminalLog(`  Status: ${result.status === 'compliant' ? '✓ COMPLIANT → done/' : '⚠ NEEDS REVIEW → needs_review/'}`, result.status === 'compliant' ? 'success' : 'warning');

      if (result.remainingIssues.length > 0) {
        terminalLog(`  Remaining issues: ${result.remainingIssues.length}`, 'warning');
        result.remainingIssues.forEach(issue => {
          terminalLog(`    ✗ ${issue.name} (${issue.severity})`, 'error');
          if (issue.note) terminalLog(`      Note: ${issue.note}`, 'warning');
        });
      }

      results.push(result);
    }

    // Generate CSV report
    terminalLog('\nGenerating CSV report...', 'info');
    const csvContent = generateCsvReport(results);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const csvPath = path.join(RESULTS_DIR, `pipeline_report_${timestamp}.csv`);
    await fs.writeFile(csvPath, csvContent);

    // Summary
    terminalLog('\n' + '━'.repeat(60), 'accent');
    terminalLog('PIPELINE COMPLETE', 'bold');
    terminalLog('━'.repeat(60), 'accent');
    const compliant = results.filter(r => r.status === 'compliant').length;
    const needsReview = results.filter(r => r.status === 'needs_review').length;
    terminalLog(`  Total processed: ${results.length}`, 'info');
    terminalLog(`  ✓ Compliant (done/): ${compliant}`, 'success');
    terminalLog(`  ⚠ Needs review (needs_review/): ${needsReview}`, 'warning');
    terminalLog(`  Report: ${csvPath}`, 'info');

    res.json({
      success: true,
      results: results.map(r => ({
        fileName: r.fileName,
        status: r.status,
        issuesBefore: r.issuesBefore,
        issuesAfter: r.issuesAfter,
        fixesApplied: r.fixesApplied,
        remainingIssues: r.remainingIssues.map(i => i.name),
        info: r.info
      }))
    });
  } catch (err) {
    terminalLog(`Pipeline failed: ${err.message}`, 'error');
    res.status(500).json({ error: err.message });
  }
});

// GET /api/results/:type/:name — Download a result PDF
app.get('/api/results/:type/:name', async (req, res) => {
  const { type, name } = req.params;
  const dir = type === 'done' ? DONE_DIR : NEEDS_REVIEW_DIR;
  const filePath = path.join(dir, name);

  try {
    const stat = await fs.stat(filePath);
    res.setHeader('Content-Length', stat.size);
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename="${name}"`);
    const stream = createReadStream(filePath);
    stream.pipe(res);
  } catch {
    res.status(404).json({ error: 'File not found' });
  }
});

// GET /api/report/latest — Download latest CSV report
app.get('/api/report/latest', async (req, res) => {
  try {
    terminalLog(`Looking for reports in: ${RESULTS_DIR}`, 'dim');
    const files = await fs.readdir(RESULTS_DIR);
    terminalLog(`Found files: ${JSON.stringify(files)}`, 'dim');
    const csvs = files.filter(f => f.endsWith('.csv')).sort().reverse();
    if (csvs.length === 0) {
      return res.status(404).json({ error: 'No reports found' });
    }
    const latest = path.join(RESULTS_DIR, csvs[0]);
    terminalLog(`Serving: ${latest}`, 'success');
    res.setHeader('Content-Disposition', `attachment; filename="${csvs[0]}"`);
    res.setHeader('Content-Type', 'text/csv');
    const stream = createReadStream(latest);
    stream.pipe(res);
  } catch (err) {
    terminalLog(`Report download error: ${err.message}`, 'error');
    res.status(404).json({ error: 'No reports found: ' + err.message });
  }
});

// POST /api/deep-scan — Run Python compliance checker on all PDFs
app.post('/api/deep-scan', async (req, res) => {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  try {
    terminalLog('Running deep scan (Python compliance checker)...', 'accent');

    const proc = spawn(pythonCmd, [path.join(__dirname, 'deep_scan.py'), INPUT_DIR], {
      cwd: __dirname,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    proc.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(stdout);
          terminalLog(`Deep scan complete: ${result.scanned} PDFs scanned.`, 'success');
          res.json(result);
        } catch (e) {
          terminalLog(`Failed to parse deep scan output: ${e.message}`, 'error');
          terminalLog(stdout.slice(-500), 'dim');
          res.status(500).json({ error: 'Failed to parse results' });
        }
      } else {
        terminalLog(`Deep scan failed (exit code ${code}): ${stderr}`, 'error');
        res.status(500).json({ error: stderr || 'Deep scan failed' });
      }
    });

    proc.on('error', (err) => {
      terminalLog(`Deep scan error: ${err.message}`, 'error');
      res.status(500).json({ error: err.message });
    });
  } catch (err) {
    terminalLog(`Deep scan setup failed: ${err.message}`, 'error');
    res.status(500).json({ error: err.message });
  }
});
// POST /api/auto-tag — Open a PDF in Acrobat and prompt user to auto-tag
app.post('/api/auto-tag', async (req, res) => {
  const { fileName } = req.body;

  // Search for the PDF in all possible directories
  const searchDirs = [INPUT_DIR, DONE_DIR, NEEDS_REVIEW_DIR, ADOBE_FIXED_DIR, AUTO_FIXED_DIR];
  let pdfPath = null;

  for (const dir of searchDirs) {
    const candidate = path.join(dir, fileName);
    if (existsSync(candidate)) {
      pdfPath = candidate;
      break;
    }

    // Also try URL-decoded version
    try {
      const decoded = decodeURIComponent(fileName);
      if (decoded !== fileName) {
        const candidate2 = path.join(dir, decoded);
        if (existsSync(candidate2)) {
          pdfPath = candidate2;
          break;
        }
      }
    } catch {}
  }

  if (!pdfPath) {
    return res.status(404).json({ error: `PDF not found: ${fileName}` });
  }

  try {
    execSync(`start "" "${pdfPath}"`, { shell: true });
    terminalLog(`Opened ${fileName} in Acrobat.`, 'success');
    terminalLog('  → In Acrobat: Tools > Accessibility > Auto-Tag Document', 'accent');
    terminalLog('  → Save the tagged PDF, then click "Re-Assess" to verify.', 'accent');
    res.json({ success: true, message: 'PDF opened in Acrobat for tagging' });
  } catch (err) {
    terminalLog(`Could not open Acrobat: ${err.message}`, 'error');
    res.status(500).json({ error: err.message });
  }
});

// POST /api/adobe-autotag — Run Adobe Cloud API auto-tag on all PDFs
app.post('/api/adobe-autotag', async (req, res) => {
  const { fileNames } = req.body;
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  try {
    terminalLog('Starting Adobe Cloud Auto-Tag...', 'accent');
    terminalLog('This will upload PDFs to Adobe API, auto-tag them, and download tagged versions.', 'info');

    // Pass file names as JSON to Python script
    const proc = spawn(pythonCmd, [
      '-c',
      `
import sys, json, os
sys.path.insert(0, '.')

# Override input to auto-confirm if file names provided
file_names = json.loads(r'${JSON.stringify(fileNames || []).replace(/'/g, "\\'")}')

# Mock input for auto-confirm
import builtins
original_input = builtins.input
def mock_input(prompt=""):
    if "Process" in prompt or "y/n" in prompt:
        return "y"
    return original_input(prompt)
builtins.input = mock_input

# Run auto-tag
from adobe_autotag_api import main as run_autotag
try:
    run_autotag()
except SystemExit:
    pass
`
    ], { cwd: __dirname, stdio: ['ignore', 'pipe', 'pipe'] });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      const text = data.toString();
      stdout += text;
      text.split('\n').filter(l => l.trim()).forEach(line => {
        if (line.includes('✅') || line.includes('COMPLETE')) terminalLog(line, 'success');
        else if (line.includes('❌') || line.includes('Error') || line.includes('failed')) terminalLog(line, 'error');
        else if (line.includes('⏳') || line.includes('Uploading') || line.includes('Polling')) terminalLog(line, 'accent');
        else if (line.includes('🔑') || line.includes('📤') || line.includes('📥') || line.includes('🏷️')) terminalLog(line, 'info');
        else terminalLog(line, 'dim');
      });
    });

    proc.stderr.on('data', (data) => {
      const text = data.toString();
      stderr += text;
      terminalLog(text.trim(), 'error');
    });

    proc.on('close', (code) => {
      if (code === 0 || stdout.includes('BATCH AUTO-TAG COMPLETE')) {
        terminalLog('Adobe Cloud Auto-Tag complete!', 'success');
        res.json({ success: true, output: stdout });
      } else {
        terminalLog(`Adobe Auto-Tag failed (exit ${code})`, 'error');
        res.status(500).json({ error: stderr || stdout });
      }
    });

    proc.on('error', (err) => {
      terminalLog(`Adobe Auto-Tag error: ${err.message}`, 'error');
      res.status(500).json({ error: err.message });
    });
  } catch (err) {
    terminalLog(`Adobe Auto-Tag setup failed: ${err.message}`, 'error');
    res.status(500).json({ error: err.message });
  }
});

// POST /api/re-assess — Re-run compliance check on a specific PDF
app.post('/api/re-assess', async (req, res) => {
  const { fileName } = req.body;
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  // Find the PDF
  const searchDirs = [INPUT_DIR, DONE_DIR, NEEDS_REVIEW_DIR, ADOBE_FIXED_DIR, AUTO_FIXED_DIR, AUTO_TAGGED_DIR];
  let pdfPath = null;
  let foundIn = '';

  for (const dir of searchDirs) {
    const candidate = path.join(dir, fileName);
    if (existsSync(candidate)) {
      pdfPath = candidate;
      foundIn = path.basename(dir);
      break;
    }
    try {
      const decoded = decodeURIComponent(fileName);
      if (decoded !== fileName) {
        const candidate2 = path.join(dir, decoded);
        if (existsSync(candidate2)) {
          pdfPath = candidate2;
          foundIn = path.basename(dir);
          break;
        }
      }
    } catch {}
  }

  if (!pdfPath) {
    return res.status(404).json({ error: `PDF not found: ${fileName}` });
  }

  terminalLog(`Re-assessing: ${fileName} (found in ${foundIn}/)...`, 'accent');

  // Run Python compliance checker on just this one file
  const proc = spawn(pythonCmd, [
    '-c',
    `
import sys, json
sys.path.insert(0, '.')
from compliance_checker import run_compliance_check, generate_compliance_summary
from pathlib import Path
report = run_compliance_check(Path(r'${pdfPath.replace(/\\/g, '\\\\')}'))
print(json.dumps({
    'filename': report.filename,
    'wcag_level_a_pass': report.wcag_level_a_pass,
    'pdfua_compliant': report.pdfua_compliant,
    'section508_compliant': report.section508_compliant,
    'passed': report.passed,
    'failed': report.failed,
    'warnings': report.warnings,
    'manual_checks': report.manual_checks,
    'checks': report.checks
}, indent=2))
`
  ], { cwd: __dirname, stdio: ['ignore', 'pipe', 'pipe'] });

  let stdout = '';
  let stderr = '';

  proc.stdout.on('data', (data) => { stdout += data.toString(); });
  proc.stderr.on('data', (data) => { stderr += data.toString(); });

  proc.on('close', (code) => {
    if (code === 0) {
      try {
        const result = JSON.parse(stdout);
        terminalLog(`Re-assess complete: ${result.filename} — ${result.passed} passed, ${result.failed} failed`, 'success');
        res.json({ success: true, result });
      } catch (e) {
        terminalLog(`Failed to parse re-assess output: ${e.message}`, 'error');
        res.status(500).json({ error: 'Failed to parse results' });
      }
    } else {
      terminalLog(`Re-assess failed (exit ${code}): ${stderr}`, 'error');
      res.status(500).json({ error: stderr || 'Re-assess failed' });
    }
  });

  proc.on('error', (err) => {
    terminalLog(`Re-assess error: ${err.message}`, 'error');
    res.status(500).json({ error: err.message });
  });
});

// ── Helper: run a shell command ─────────────────────────────
function runCommand(cmd, args, cwd) {
  return new Promise((resolve, reject) => {
    const proc = spawn(cmd, args, { cwd, shell: process.platform === 'win32' });
    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      const text = data.toString().trim();
      if (text) terminalLog(text, 'dim');
      stdout += text;
    });

    proc.stderr.on('data', (data) => {
      const text = data.toString().trim();
      if (text) terminalLog(text, 'warning');
      stderr += text;
    });

    proc.on('close', (code) => {
      if (code === 0) resolve(stdout);
      else reject(new Error(`${cmd} exited with code ${code}: ${stderr}`));
    });

    proc.on('error', reject);
  });
}

// ── Start Server ────────────────────────────────────────────
async function start() {
  await ensureDirs();

  app.listen(PORT, () => {
    const url = `http://localhost:${PORT}`;
    console.log(`\n  📄 PDF ADA Compliance Processor`);
    console.log(`  ─────────────────────────────────`);
    console.log(`  Server running at: ${url}`);
    console.log(`  Open in your browser to get started!\n`);

    // Try to open browser automatically
    if (process.platform === 'win32') {
      spawn('cmd', ['/c', 'start', url], { detached: true, stdio: 'ignore' });
    } else if (process.platform === 'darwin') {
      spawn('open', [url], { detached: true, stdio: 'ignore' });
    }
  });
}

start();
