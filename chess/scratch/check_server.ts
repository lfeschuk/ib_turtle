import http from 'http';

const req = http.request({
  hostname: 'localhost',
  port: 3000,
  path: '/',
  method: 'GET'
}, (res) => {
  console.log(`Server responded with status: ${res.statusCode}`);
  process.exit(0);
});

req.on('error', (e) => {
  console.log(`Server not running: ${e.message}`);
  process.exit(1);
});

req.end();
