import io
import re

with io.open('app.js', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''window.cycleMobileCarousel = function(btnElement, direction, event) {
    if (event) event.stopPropagation();
    const card = btnElement.closest('.research-card');
    if (!card) return;
    const tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));
    if (!tabs.length) return;
    let activeIdx = tabs.findIndex(t => t.classList.contains('active'));
    if (activeIdx === -1) activeIdx = 0;
    let nextIdx = (activeIdx + direction) % tabs.length;
    if (nextIdx < 0) nextIdx = tabs.length - 1;
    tabs[nextIdx].click();
}'''

replace = '''window.cycleMobileCarousel = function(btnElement, direction, event) {
    if (event) event.stopPropagation();
    const card = btnElement.closest('.research-card');
    if (!card) return;
    
    // Add slide direction for animation
    const contentArea = card.querySelector('.analyst-content-area');
    if (contentArea) {
        contentArea.setAttribute('data-slide-dir', direction === 1 ? 'right' : 'left');
    }
    
    const tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));
    if (!tabs.length) return;
    let activeIdx = tabs.findIndex(t => t.classList.contains('active'));
    if (activeIdx === -1) activeIdx = 0;
    let nextIdx = (activeIdx + direction) % tabs.length;
    if (nextIdx < 0) nextIdx = tabs.length - 1;
    tabs[nextIdx].click();
    
    if (contentArea) {
        setTimeout(() => {
            contentArea.removeAttribute('data-slide-dir');
        }, 400); // Matches animation duration
    }
}'''

text = text.replace(target, replace)

with io.open('app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated app.js")
