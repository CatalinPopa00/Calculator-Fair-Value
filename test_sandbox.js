const fs = require('fs');

// Mock DOM
global.document = {
    getElementById: (id) => ({
        value: '10',
        addEventListener: () => {},
        dispatchEvent: () => {}
    })
};
global.window = {};

const code = fs.readFileSync('app.js', 'utf8');

// We just want to extract getDcfGrowthDefault and getDynamicRevGrowth
// Let's create a sandbox and run them.
const vm = require('vm');
const sandbox = {
    document: global.document,
    window: global.window,
    console: console,
    Math: Math,
    parseFloat: parseFloat,
    isNaN: isNaN,
    Array: Array,
    Event: class Event {}
};

// Remove DOM elements manipulation that might throw
let safeCode = code.replace(/document\.getElementById/g, "(() => ({value: '10'}))");

vm.createContext(sandbox);

// Provide mock global data
sandbox.globalData = {
    ticker: 'NVDA',
    company_profile: { revenue_growth: 0.813 },
    rev_estimates: [
        { period: "FY 2024", avg: 215.94, low: null, high: null, yearAgo: null, growth: null, status: "reported" },
        { period: "FY 2025", avg: 391.49, low: 357.21, high: 414.49, yearAgo: 215.94, growth: 0.81295, status: "estimate" },
        { period: "FY 2026", avg: 547.46, low: 416.40, high: 751.24, yearAgo: 391.49, growth: 0.39840, status: "estimate" }
    ]
};

const testScript = `
let _currentScenario = 'bear';
const fcfSource = 'revenue';
// Extract getDynamicRevGrowth from the code...
`;
