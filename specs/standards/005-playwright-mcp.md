# Standard 005: Playwright MCP for Browser Automation

**Date:** 2026-04-07
**Status:** DEFINITIVE
**Components Affected:** Qwen Code settings (`~/.qwen/settings.json`), `index.html`

## Pain Point

Manual browser testing of the web UI is slow and error-prone:
- Uploading PDFs via drag-drop manually
- Clicking buttons and waiting for terminal output
- Scrolling to find results tables
- Verifying compliance badges updated correctly
- Testing the Re-Assess flow end-to-end

Each test cycle takes 2-5 minutes of manual clicking and scrolling. Changes to the UI require full re-testing.

## Root Cause

The web UI is a complex single-page application with drag-drop, SSE streaming, dynamic result tables, and interactive buttons. Manual testing does not scale with iterative development.

## Fix Applied

Installed **Playwright MCP** server and configured in Qwen Code settings:

```json
"mcpServers": {
  "playwright": {
    "command": "npx",
    "args": ["-y", "playwright-mcp@latest", "--browser", "chromium", "--headless", "false"]
  }
}
```

**Installation:**
```bash
npm install -g playwright-mcp
npx playwright install chromium
```

This enables Qwen Code to:
- Navigate to any URL
- Click buttons and interact with elements
- Take screenshots for visual verification
- Extract text and data from the page
- Execute JavaScript in the browser context
- Get interactive element snapshots for UI automation

## Definitive Standard

**Rule 1:** Playwright MCP is the standard browser automation tool for this project.

**Rule 2:** Browser automation tests should be run through Qwen Code using the MCP tools:
- `mcp__playwright__init-browser` — Navigate to URL
- `mcp__playwright__get-screenshot` — Visual verification
- `mcp__playwright__get-text-snapshot` — Content extraction
- `mcp__playwright__get-interactive-snapshot` — Element discovery
- `mcp__playwright__execute-code` — Custom Playwright JS execution

**Rule 3:** The MCP server runs in headed mode (`--headless false`) so visual verification is possible during development. Headless mode can be used for CI.

**Rule 4:** Browser automation is used for:
- End-to-end pipeline testing
- UI regression verification
- Automated screenshot capture for documentation

## Related Standards

- Standard 001 (Node.js web server)
- Standard 003 (Adobe Cloud API web endpoint)

## References

- `~/.qwen/settings.json` — MCP server configuration
- [Playwright MCP npm package](https://www.npmjs.com/package/playwright-mcp)
