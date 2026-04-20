module.exports = {
  // Specify which Node.js versions and architectures to build for
  targets: ['node18-win-x64', 'node18-win-arm64'],
  // Name of the output binary (without extension)
  outputName: 'pdf-ada-processor',
  // Where the binary will be placed
  outputPath: '.',
  // Entry point of the application
  main: 'server.js',
  // No extra arguments
  args: [],
  // Whether to compress the binary
  compress: true,
  // Keep logs minimal
  silent: true
};