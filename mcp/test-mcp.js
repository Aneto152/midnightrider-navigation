#!/usr/bin/env node

/**
 * Test MCP Client for Astronomical Server
 * 
 * Tests the MCP server by sending requests
 */

const { spawn } = require('child_process');
const path = require('path');

// Start the MCP server
const server = spawn('node', [path.join(__dirname, 'astronomical-server.js')], {
  stdio: ['pipe', 'pipe', 'pipe']
});

let requestId = 1;

function sendRequest(method, params) {
  const request = {
    jsonrpc: '2.0',
    id: requestId++,
    method,
    params: params || {}
  };
  console.log(`\n→ Sending: ${method}`, params ? JSON.stringify(params) : '');
  server.stdin.write(JSON.stringify(request) + '\n');
}

let responseCount = 0;
const maxResponses = 5; // Expect 5 responses

server.stdout.on('data', (data) => {
  const lines = data.toString().split('\n').filter(l => l.trim());
  for (const line of lines) {
    try {
      const response = JSON.parse(line);
      console.log(`← Received:`, JSON.stringify(response, null, 2));
      
      responseCount++;
      if (responseCount >= maxResponses) {
        server.kill();
      }
    } catch (err) {
      console.error('Parse error:', err.message, 'Line:', line);
    }
  }
});

server.stderr.on('data', (data) => {
  console.error('Server error:', data.toString());
});

server.on('close', (code) => {
  console.log(`\nServer exited with code ${code}`);
  process.exit(code);
});

// Send test requests
setTimeout(() => {
  console.log('=== Testing Astronomical MCP Server ===\n');
  
  sendRequest('initialize');
  setTimeout(() => sendRequest('tools/list'), 500);
  
  const today = new Date().toISOString().split('T')[0];
  setTimeout(() => sendRequest('tools/call', { name: 'get_sun_data', arguments: { date: today } }), 1000);
  setTimeout(() => sendRequest('tools/call', { name: 'get_moon_data', arguments: { date: today } }), 1500);
  setTimeout(() => sendRequest('tools/call', { name: 'get_next_event' }), 2000);
}, 100);
