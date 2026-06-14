import io

css_to_add = """
/* Mobile Carousel Page Indicators */
@media (max-width: 768px) {
    .mobile-carousel-indicators {
        display: flex;
        gap: 6px;
        margin-top: 15px;
        margin-bottom: 5px;
        padding: 0 15px;
        justify-content: center;
        width: 100%;
        box-sizing: border-box;
    }
    .carousel-indicator-line {
        flex: 1;
        max-width: 40px;
        height: 4px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 2px;
        transition: background 0.3s ease, transform 0.3s ease;
    }
    .carousel-indicator-line.active {
        background: var(--accent, #00d2ff);
        transform: scaleY(1.2);
    }
}
@media (min-width: 769px) {
    .mobile-carousel-indicators {
        display: none !important;
    }
}
"""

js_to_add = """

// ---------------------------------------------
// MOBILE SWIPE & CAROUSEL INDICATORS LOGIC
// ---------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    
    // Initialize Page Indicators for Mobile Carousels
    function initCarouselIndicators() {
        document.querySelectorAll('.research-card').forEach(card => {
            const tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));
            if (!tabs.length) return;
            
            const tabsWrapper = card.querySelector('.analyst-tabs-wrapper');
            if (!tabsWrapper) return;
            
            let indicatorWrapper = card.querySelector('.mobile-carousel-indicators');
            if (!indicatorWrapper) {
                indicatorWrapper = document.createElement('div');
                indicatorWrapper.className = 'mobile-carousel-indicators';
                tabsWrapper.appendChild(indicatorWrapper);
            }
            
            indicatorWrapper.innerHTML = '';
            tabs.forEach((tab, i) => {
                const line = document.createElement('div');
                line.className = 'carousel-indicator-line';
                if (tab.classList.contains('active')) {
                    line.classList.add('active');
                }
                indicatorWrapper.appendChild(line);
            });
        });
    }
    
    initCarouselIndicators();

    // Update indicators on tab click
    document.querySelectorAll('.analyst-tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const card = this.closest('.research-card');
            if (!card) return;
            
            setTimeout(() => { 
                const tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));
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
    });

    // Add Swipe Support
    document.querySelectorAll('.analyst-content-area').forEach(area => {
        let touchStartX = 0;
        let touchEndX = 0;

        area.addEventListener('touchstart', e => {
            touchStartX = e.changedTouches[0].screenX;
        }, {passive: true});

        area.addEventListener('touchend', e => {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe(area);
        }, {passive: true});

        function handleSwipe(area) {
            const threshold = 50; 
            const diff = touchEndX - touchStartX;
            
            const card = area.closest('.research-card');
            if (!card) return;
            
            if (window.innerWidth > 768) return;

            if (diff > threshold) {
                if (window.cycleMobileCarousel) {
                    window.cycleMobileCarousel({ closest: () => card }, -1);
                }
            } else if (diff < -threshold) {
                if (window.cycleMobileCarousel) {
                    window.cycleMobileCarousel({ closest: () => card }, 1);
                }
            }
        }
    });
});
"""

with io.open('style.css', 'a', encoding='utf-8') as f:
    f.write(css_to_add)

with io.open('app.js', 'a', encoding='utf-8') as f:
    f.write(js_to_add)

print("Swipe and indicators added.")
