const fs = require('fs');
const acorn = require('acorn');

const code = fs.readFileSync('app.js', 'utf-8');
try {
    acorn.parse(code, { ecmaVersion: 2020 });
    console.log("Syntax is OK");
} catch (e) {
    console.log("Syntax error at", e.loc);
    const lines = code.split('\n');
    const start = Math.max(0, e.loc.line - 5);
    const end = Math.min(lines.length, e.loc.line + 5);
    for (let i = start; i < end; i++) {
        console.log(`${i + 1}: ${lines[i]}`);
    }
}
