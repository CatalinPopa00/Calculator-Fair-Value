const fs = require('fs');
let code = fs.readFileSync('app.js', 'utf8');

code = code.replace("    if (stickyPrice && !_simulating) {\\n        stickyPrice.classList.remove('price-flash-green', 'price-flash-red');", "    if (triggerFlash && stickyPrice && !_simulating) {\\n        stickyPrice.classList.remove('price-flash-green', 'price-flash-red');");

fs.writeFileSync('app.js', code);
