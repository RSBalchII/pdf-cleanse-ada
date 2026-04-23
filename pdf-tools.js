/**
 * PDF ADA Compliance - Node.js Bridge to Python Backend
 */

import { spawn, execSync } from 'child_process';
import fs from 'fs/promises';
import path from 'path';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const VENV_DIR = path.join(__dirname, '.venv');

/**
 * Python command resolution
 */
function getPythonCmd() {
  const venvPython = process.platform === 'win32'
    ? path.join(VENV_DIR, 'Scripts', 'python.exe')
    : path.join(VENV_DIR, 'bin', 'python');

  if (existsSync(venvPython)) return venvPython;

  try { execSync('command -v python3', { encoding: 'utf8' }); return 'python3'; } catch (_) {}
  try { execSync('command -v python', { encoding: 'utf8' }); return 'python'; } catch (_) {}

  const commonPaths = ['/opt/homebrew/bin/python3', '/usr/local/bin/python3', '/usr/bin/python3'];
  for (const p of commonPaths) { if (existsSync(p)) return p; }

  return 'python3';
}

/**
 * Directory constants
 */
export const INPUT_DIR = path.join(__dirname, 'input_pdfs');
export const DONE_DIR = path.join(__dirname, 'done');
export const NEEDS_REVIEW_DIR = path.join(__dirname, 'needs_review');
export const RESULTS_DIR = path.join(__dirname, 'results');
export const AUTO_TAGGED_DIR = path.join(__dirname, 'auto_tagged');
export const ADOBE_FIXED_DIR = path.join(__dirname, 'adobe_fixed');
export const AUTO_FIXED_DIR = path.join(__dirname, 'auto_fixed');

/**
 * Ensure all required directories exist
 */
export async function ensureDirs() {
  await fs.mkdir(INPUT_DIR, { recursive: true });
  await fs.mkdir(DONE_DIR, { recursive: true });
  await fs.mkdir(NEEDS_REVIEW_DIR, { recursive: true });
  await fs.mkdir(RESULTS_DIR, { recursive: true });
  await fs.mkdir(AUTO_TAGGED_DIR, { recursive: true });
  await fs.mkdir(ADOBE_FIXED_DIR, { recursive: true });
}

/**
 * Run Python script with graceful error handling
 */
function runPythonCmd(args) {
  const pythonCmd = getPythonCmd();
  return new Promise((resolve, reject) => {
    const proc = spawn(pythonCmd, [...args], { cwd: __dirname });
    let stdout = '', stderr = '';

    proc.stdout.on('data', (data) => { stdout += data.toString(); });
    proc.stderr.on('data', (data) => { stderr += data.toString(); });

    proc.on('close', (code) => {
      if (code === 0 || code === undefined) resolve(stdout);
      else reject(new Error('Python script exited with code ' + code));
    });

    proc.on('error', reject);
  });
}

/**
 * Process a single PDF file using the Python compliance checker
 */
export async function processPdf(pdfPath, fileName) {
  try {
    const result = await runPythonCmd(['compliance_checker.py', '-f', pdfPath.toString()]);
    if (result.trim()) return JSON.parse(result);
    throw new Error('Python returned empty output');
  } catch (err) {
    console.error('Error processing PDF: ' + pdfPath);
    console.error(err.message);
    return {
      fileName, path: pdfPath.toString(),
      info: { title: '(error)', lang: '(error)', isTagged: false, isMarked: false, pageCount: 0, imageCount: 0 },
      status: 'needs_review', issuesBefore: [], fixesApplied: [], remainingIssues: [{ name: 'processing_error', severity: 'error' }]
    };
  }
}

/**
 * Generate CSV report from compliance results
 */
export function generateCsvReport(results) {
  let csv = 'Filename,Title,Language,Tagged,Marked,Pages,Images,Status,Issues Before,Issues After\n';

  for (const result of results) {
    const issuesBeforeCount = result.issuesBefore.length;
    const issuesAfterCount = result.remainingIssues.length;

    csv += result.fileName + ',' + (result.info.title || '').replace(/"/g, '""') + ',';
    csv += '"' + (result.info.lang || '') + '",';
    csv += (result.info.isTagged ? 'true' : 'false');
    csv += ',' + (result.info.isMarked ? 'true' : 'false');
    csv += ',' + result.info.pageCount + ',' + result.info.imageCount;
    csv += ',' + '"' + result.status + '"';
    csv += ',' + issuesBeforeCount + ',' + issuesAfterCount + '\n';
  }

  return csv;
}
