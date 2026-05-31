#!/usr/bin/env node

const fs = require('fs');

const sourcePath = process.argv[2] || 'js/hackathons-config.js';
const outputPath = process.argv[3] || '/tmp/hackathons-config-parsed.json';
const source = fs.readFileSync(sourcePath, 'utf8');
const config = eval(`${source}\nHACKATHONS_CONFIG`);

config.hackathons.forEach(hackathon => {
    if (hackathon.github) hackathon.github.token = '';
    if (hackathon.gitlab) hackathon.gitlab.token = '';
});

fs.writeFileSync(outputPath, JSON.stringify(config));
console.log(`Parsed ${config.hackathons.length} hackathon(s) to ${outputPath}`);
