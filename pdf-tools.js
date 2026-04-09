/**
 * PDF ADA Compliance Tools — Pure Node.js
 *
 * Uses pdf-lib for PDF manipulation and raw PDF parsing for low-level inspection.
 */

import pdfLib from 'pdf-lib';
const { PDFDocument, PDFName, PDFDict } = pdfLib;
import { promises as fs, existsSync } from 'fs';
import { join, dirname, basename } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SCRIPT_DIR = __dirname;

/**
 * Resolve the Python interpreter to use.
 * Prefers .venv/bin/python (macOS/Linux) or .venv\Scripts\python.exe (Windows)
 * when a virtual environment exists; otherwise falls back to system Python.
 */
function getPythonCmd() {
  const venvPython = process.platform === 'win32'
    ? join(SCRIPT_DIR, '.venv', 'Scripts', 'python.exe')
    : join(SCRIPT_DIR, '.venv', 'bin', 'python');
  if (existsSync(venvPython)) return venvPython;
  return process.platform === 'win32' ? 'python' : 'python3';
}

export const INPUT_DIR = join(SCRIPT_DIR, 'input_pdfs');
export const DONE_DIR = join(SCRIPT_DIR, 'done');
export const NEEDS_REVIEW_DIR = join(SCRIPT_DIR, 'needs_review');
export const RESULTS_DIR = join(SCRIPT_DIR, 'pipeline_results');
export const AUTO_TAGGED_DIR = join(SCRIPT_DIR, 'adobe_tagged');
export const ADOBE_FIXED_DIR = join(SCRIPT_DIR, 'adobe_fixed');
export const AUTO_FIXED_DIR = join(SCRIPT_DIR, 'auto_fixed');

/**
 * Scan raw PDF bytes for structural markers that pdf-lib can't access.
 */
function scanRawPdf(buffer) {
  const text = buffer.toString('binary');

  // Check for StructTreeRoot
  const isTagged = /\/StructTreeRoot/.test(text);

  // Check for ParentTree (reading order mapping)
  const hasParentTree = /\/ParentTree/.test(text);

  // Check for /MarkInfo /Marked true
  const hasMarkInfo = /\/MarkInfo[\s\S]{0,200}\/Marked\s*\/?true/.test(text);

  // Count images (XObject /Image)
  const imageCount = (text.match(/\/Subtype\s*\/Image/g) || []).length;

  // Count /Figure elements in structure tree
  const figureCount = (text.match(/\/S\s*\/Figure/g) || []).length;

  // Count /Figure elements WITH /Alt text
  // Pattern: /Figure ... /Alt (some text)
  const figureAltPattern = /\/S\s*\/Figure[\s\S]{0,500}\/Alt\s*\(/g;
  const figuresWithAlt = (text.match(figureAltPattern) || []).length;

  // Check for bookmarks/outline
  const hasBookmarks = /\/Outlines/.test(text);

  // Check for /Lang entry
  const langMatch = text.match(/\/Lang\s*\(([^)]+)\)/) || text.match(/\/Lang\s*\/([A-Za-z\-]+)/);
  let lang = null;
  if (langMatch) {
    lang = langMatch[1].replace(/[\x00-\x1f\x7f-\xff]/g, '').trim();
    if (lang.startsWith('þÿ') || lang.startsWith('ÿþ')) {
      lang = lang.substring(2);
    }
  }

  // Check for table headers (/TH elements)
  const thCount = (text.match(/\/S\s*\/TH/g) || []).length;

  // Check for /Table elements
  const tableCount = (text.match(/\/S\s*\/Table/g) || []).length;

  return {
    isTagged,
    hasParentTree,
    isMarked: hasMarkInfo,
    lang,
    imageCount,
    figureCount,
    figuresWithAlt,
    hasBookmarks,
    thCount,
    tableCount
  };
}

/**
 * Read PDF metadata using pdf-lib + raw scan.
 */
export async function readPdfInfo(pdfBuffer) {
  const pdf = await PDFDocument.load(pdfBuffer, { ignoreEncryption: true });

  // pdf-lib for title (reliable)
  const title = pdf.getTitle() || null;
  const pageCount = pdf.getPageCount();

  // Raw scan for things pdf-lib doesn't expose
  const raw = scanRawPdf(Buffer.from(pdfBuffer));

  return {
    title,
    lang: raw.lang || null,
    isMarked: raw.isMarked,
    isTagged: raw.isTagged,
    hasParentTree: raw.hasParentTree,
    pageCount,
    imageCount: raw.imageCount,
    figureCount: raw.figureCount,
    figuresWithAlt: raw.figuresWithAlt,
    figuresMissingAlt: Math.max(0, raw.figureCount - raw.figuresWithAlt),
    hasBookmarks: raw.hasBookmarks,
    thCount: raw.thCount,
    tableCount: raw.tableCount
  };
}

/**
 * Check PDF for ADA compliance issues.
 */
export function checkCompliance(info) {
  const issues = [];

  if (!info.title) {
    issues.push({
      id: 'META-001',
      name: 'Missing Document Title',
      severity: 'CRITICAL',
      fixable: true,
      standard: 'WCAG 2.4.2, PDF/UA §7.1'
    });
  }

  if (!info.lang) {
    issues.push({
      id: 'META-002',
      name: 'Missing Document Language',
      severity: 'CRITICAL',
      fixable: true,
      standard: 'WCAG 3.1.1, PDF/UA §7.2'
    });
  }

  if (!info.isMarked) {
    issues.push({
      id: 'META-003',
      name: 'MarkInfo.Marked not set',
      severity: 'CRITICAL',
      fixable: true,
      standard: 'PDF/UA §5.3'
    });
  }

  if (!info.isTagged) {
    issues.push({
      id: 'STRUCT-001',
      name: 'Document is not tagged (no StructTreeRoot)',
      severity: 'CRITICAL',
      fixable: false,
      standard: 'WCAG 1.3.1, PDF/UA §5',
      note: 'Requires Adobe Acrobat: Tools > Accessibility > Auto-Tag Document'
    });
  }

  // Reading order check
  if (info.isTagged && !info.hasParentTree) {
    issues.push({
      id: 'READ-001',
      name: 'Missing ParentTree (reading order may be incorrect)',
      severity: 'IMPORTANT',
      fixable: false,
      standard: 'WCAG 1.3.2, PDF/UA §5.3',
      note: 'Manual check: verify reading order in Acrobat'
    });
  }

  // Figure alt text check
  if (info.isTagged && info.figureCount > 0 && info.figuresMissingAlt > 0) {
    issues.push({
      id: 'FIG-001',
      name: `${info.figuresMissingAlt} of ${info.figureCount} figures missing alt text`,
      severity: 'CRITICAL',
      fixable: false,
      standard: 'WCAG 1.1.1, PDF/UA §5.6',
      note: 'Add alt text in Acrobat: right-click image > Set Alternate Text'
    });
  }

  // Table headers check
  if (info.isTagged && info.tableCount > 0 && info.thCount === 0) {
    issues.push({
      id: 'TAB-001',
      name: `${info.tableCount} table(s) found with no header cells (/TH)`,
      severity: 'CRITICAL',
      fixable: false,
      standard: 'WCAG 1.3.1, PDF/UA §5.7',
      note: 'Mark table headers in Acrobat: Table Editor > mark as header'
    });
  }

  // Bookmarks for large documents
  if (info.pageCount >= 21 && !info.hasBookmarks) {
    issues.push({
      id: 'NAV-001',
      name: 'Large document without bookmarks',
      severity: 'ADVISORY',
      fixable: false,
      standard: 'WCAG 2.4.5 (Level AA)',
      note: 'Consider adding bookmarks for navigation'
    });
  }

  return issues;
}

/**
 * Fix PDF metadata using Python/pikepdf via stdin/stdout.
 * Reads PDF from stdin, writes fixed PDF to stdout, fixes as JSON on stderr.
 */
export async function fixPdf(pdfBuffer, info, stem = '') {
  const { spawn } = await import('child_process');

  const pythonCmd = getPythonCmd();
  const scriptPath = join(SCRIPT_DIR, 'pdf_fix_single.py');

  return new Promise((resolve, reject) => {
    const proc = spawn(pythonCmd, [scriptPath, stem], {
      cwd: SCRIPT_DIR,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stdout = Buffer.alloc(0);
    let stderr = '';

    proc.stdout.on('data', (d) => { stdout = Buffer.concat([stdout, d]); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });

    proc.on('close', (code) => {
      if (code === 0 && stdout.length > 0) {
        try {
          const fixes = JSON.parse(stderr.trim().split('\n').pop());
          resolve({ fixedBuffer: stdout, fixes });
        } catch {
          resolve({ fixedBuffer: stdout, fixes: [] });
        }
      } else {
        // Fallback: return original buffer
        resolve({ fixedBuffer: pdfBuffer, fixes: [] });
      }
    });

    proc.on('error', () => {
      resolve({ fixedBuffer: pdfBuffer, fixes: [] });
    });

    // Send PDF to stdin
    proc.stdin.write(pdfBuffer);
    proc.stdin.end();
  });
}

/**
 * Process a single PDF: read → check → fix → save.
 */
export async function processPdf(pdfPath) {
  const fileName = basename(pdfPath);
  const stem = fileName.replace(/\.pdf$/i, '');

  const buffer = await fs.readFile(pdfPath);
  const info = await readPdfInfo(buffer);

  // Run compliance check before fixes
  const issuesBefore = checkCompliance(info);

  // Apply all auto-fixes
  const { fixedBuffer, fixes: fixesApplied } = await fixPdf(buffer, info, stem);

  // Re-read info from the fixed PDF
  const fixedInfo = await readPdfInfo(fixedBuffer);
  const issuesAfter = checkCompliance(fixedInfo);

  // Determine destination based on remaining auto-fixable issues
  const autoFixable = issuesAfter.filter(i => i.fixable).length;
  const needsReview = autoFixable > 0;
  const destDir = needsReview ? NEEDS_REVIEW_DIR : DONE_DIR;
  const status = needsReview ? 'needs_review' : 'compliant';

  // Ensure dirs exist
  await fs.mkdir(destDir, { recursive: true });
  await fs.mkdir(RESULTS_DIR, { recursive: true });

  // Save the FIXED PDF (not the original)
  const destPath = join(destDir, fileName);
  await fs.writeFile(destPath, fixedBuffer);

  return {
    fileName,
    status,
    info: {
      title: fixedInfo.title,
      lang: fixedInfo.lang,
      isTagged: fixedInfo.isTagged,
      isMarked: fixedInfo.isMarked,
      pageCount: fixedInfo.pageCount,
      imageCount: fixedInfo.imageCount
    },
    issuesBefore: issuesBefore.length,
    issuesAfter: issuesAfter.length,
    remainingIssues: issuesAfter,
    fixesApplied,
    destPath
  };
}

/**
 * Generate a CSV report from results.
 */
export function generateCsvReport(results) {
  const headers = [
    'Filename', 'Status', 'Title', 'Language', 'Is_Tagged', 'Is_Marked',
    'Pages', 'Images', 'Issues_Before', 'Issues_After', 'Fixes_Applied'
  ];

  const rows = results.map(r => [
    r.fileName,
    r.status,
    r.info.title || '',
    r.info.lang || '',
    r.info.isTagged,
    r.info.isMarked,
    r.info.pageCount,
    r.info.imageCount,
    r.issuesBefore,
    r.issuesAfter,
    (r.fixesApplied || []).join('; ')
  ]);

  const escape = v => {
    const s = String(v);
    return `"${s.replace(/"/g, '""')}"`;
  };

  return [headers.map(escape), ...rows.map(r => r.map(escape).join(','))].join('\n');
}

/**
 * Ensure all required directories exist.
 */
export async function ensureDirs() {
  const dirs = [INPUT_DIR, DONE_DIR, NEEDS_REVIEW_DIR, RESULTS_DIR, AUTO_TAGGED_DIR];
  for (const dir of dirs) {
    await fs.mkdir(dir, { recursive: true });
  }
}
