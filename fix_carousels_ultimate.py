import os

js_path = 'app.js'
with open(js_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start of the logic
start_marker = "// MOBILE SWIPE & CAROUSEL INDICATORS LOGIC"
end_marker = "/* =========================================================================="

if start_marker in content and end_marker in content:
    pre = content[:content.find(start_marker)]
    post = content[content.find(end_marker):]

    new_logic = """// MOBILE SWIPE & CAROUSEL INDICATORS LOGIC
// ---------------------------------------------

window.refreshCarousels = function() {
    document.querySelectorAll('.research-card, .company-profile-box').forEach(card => {
        let tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));
        if (!tabs.length) tabs = Array.from(card.querySelectorAll('.hist-tab'));
        if (!tabs.length) tabs = Array.from(card.querySelectorAll('.brief-tab'));
        if (!tabs.length) return;
        
        let tabsWrapper = card.querySelector('.analyst-tabs-wrapper');
        if (!tabsWrapper) tabsWrapper = card.querySelector('.hist-toggle-wrapper');
        if (!tabsWrapper) tabsWrapper = card.querySelector('.corporate-tabs-wrapper');
        if (!tabsWrapper) return;
        
        let indicatorWrapper = card.querySelector('.mobile-carousel-indicators');
        if (!indicatorWrapper) {
            indicatorWrapper = document.createElement('div');
            indicatorWrapper.className = 'mobile-carousel-indicators';
            const contentArea = card.querySelector('.analyst-content-area') || card.querySelector('.card-body-collapsible');
            if (contentArea) {
                contentArea.parentNode.insertBefore(indicatorWrapper, contentArea);
            } else {
                tabsWrapper.parentNode.insertBefore(indicatorWrapper, tabsWrapper.nextSibling);
            }
        }
        
        indicatorWrapper.innerHTML = '';
        tabs.forEach((tab, i) => {
            const line = document.createElement('div');
            line.className = 'carousel-indicator-line';
            if (tab.classList.contains('active')) {
                line.classList.add('active');
            }
            
            // Allow clicking the dashes to change tabs!
            line.addEventListener('click', () => {
                tab.click();
            });
            
            indicatorWrapper.appendChild(line);
        });
    });
};

document.addEventListener('DOMContentLoaded', () => {
    window.refreshCarousels();

    // Add Swipe Support
    document.querySelectorAll('.analyst-content-area, .historical-carousel-viewport, #profile-body').forEach(area => {
        let isDragging = false;
        let startX = 0;
        let endX = 0;

        // Touch
        area.addEventListener('touchstart', e => {
            startX = e.changedTouches[0].screenX;
        }, {passive: true});

        area.addEventListener('touchend', e => {
            endX = e.changedTouches[0].screenX;
            handleSwipe(area, e.target);
        }, {passive: true});

        // Mouse
        area.addEventListener('mousedown', e => {
            isDragging = true;
            startX = e.screenX;
        });

        area.addEventListener('mouseup', e => {
            if (!isDragging) return;
            isDragging = false;
            endX = e.screenX;
            handleSwipe(area, e.target);
        });

        area.addEventListener('mouseleave', e => {
            if (!isDragging) return;
            isDragging = false;
            endX = e.screenX;
            handleSwipe(area, e.target);
        });

        function handleSwipe(area, target) {
            const threshold = 50; 
            const diff = endX - startX;
            
            const card = area.closest('.research-card') || area.closest('.company-profile-box');
            if (!card) return;
            
            if (diff > threshold) {
                // Swipe Right (Prev)
                if (target.closest('.ai-audit-section') || target.closest('#kpi-carousel-wrapper')) {
                    const prevBtn = document.getElementById('kpi-prev-btn');
                    if (prevBtn) prevBtn.click();
                } else if (card.id === 'historical-anchors-card') {
                    const tabs = Array.from(card.querySelectorAll('.hist-tab'));
                    let activeIdx = tabs.findIndex(t => t.classList.contains('active'));
                    if (activeIdx > 0) tabs[activeIdx - 1].click();
                    else if (tabs.length) tabs[tabs.length - 1].click();
                } else if (card.classList.contains('company-profile-box')) {
                    const tabs = Array.from(card.querySelectorAll('.brief-tab'));
                    let activeIdx = tabs.findIndex(t => t.classList.contains('active'));
                    if (activeIdx > 0) tabs[activeIdx - 1].click();
                    else if (tabs.length) tabs[tabs.length - 1].click();
                } else {
                    if (window.cycleMobileCarousel) window.cycleMobileCarousel({ closest: () => card }, -1);
                }
            } else if (diff < -threshold) {
                // Swipe Left (Next)
                if (target.closest('.ai-audit-section') || target.closest('#kpi-carousel-wrapper')) {
                    const nextBtn = document.getElementById('kpi-next-btn');
                    if (nextBtn) nextBtn.click();
                } else if (card.id === 'historical-anchors-card') {
                    const tabs = Array.from(card.querySelectorAll('.hist-tab'));
                    let activeIdx = tabs.findIndex(t => t.classList.contains('active'));
                    if (activeIdx < tabs.length - 1) tabs[activeIdx + 1].click();
                    else if (tabs.length) tabs[0].click();
                } else if (card.classList.contains('company-profile-box')) {
                    const tabs = Array.from(card.querySelectorAll('.brief-tab'));
                    let activeIdx = tabs.findIndex(t => t.classList.contains('active'));
                    if (activeIdx < tabs.length - 1) tabs[activeIdx + 1].click();
                    else if (tabs.length) tabs[0].click();
                } else {
                    if (window.cycleMobileCarousel) window.cycleMobileCarousel({ closest: () => card }, 1);
                }
            }
        }
    });
});

// Event Delegation for tab clicks to update indicators
document.addEventListener('click', function(e) {
    const btn = e.target.closest('.analyst-tab-btn, .hist-tab, .brief-tab');
    if (!btn) return;
    const card = btn.closest('.research-card') || btn.closest('.company-profile-box');
    if (!card) return;
    
    setTimeout(() => { 
        let tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));
        if (!tabs.length) tabs = Array.from(card.querySelectorAll('.hist-tab'));
        if (!tabs.length) tabs = Array.from(card.querySelectorAll('.brief-tab'));
        
        const activeIdx = tabs.findIndex(t => t.classList.contains('active'));
        
        const indicatorLines = card.querySelectorAll('.carousel-indicator-line');
        indicatorLines.forEach((line, i) => {
            if (i === activeIdx) {
                line.classList.add('active');
            } else {
                line.classList.remove('active');
            }
        });
    }, 50);
});

"""
    
    # Also we need to inject `window.refreshCarousels();` after Corporate Summary renders.
    # Find `document.getElementById('profile-body').innerHTML = profileHtml;`
    injection_point = "document.getElementById('profile-body').innerHTML = profileHtml;"
    if injection_point in pre:
        pre = pre.replace(injection_point, injection_point + "\\n                setTimeout(() => { if(window.refreshCarousels) window.refreshCarousels(); }, 100);")
    
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(pre + new_logic + post)
    print("Successfully updated logic in app.js")
else:
    print("Could not find markers")
