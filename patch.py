import sys
import re

with open('app.js', 'r', encoding='utf-8') as f:
    content = f.read()

helper = '''// Helper: Robust Fetch that retries on background timeout or network drop
async function robustFetch(url, options = {}, maxRetries = 2) {
    let retryCount = 0;
    while (retryCount <= maxRetries) {
        try {
            const res = await fetch(url, options);
            if (!res.ok) {
                if (res.status === 504 && document.visibilityState === 'hidden') {
                    throw new Error('Timeout due to background');
                }
                return res; // let caller handle other HTTP errors
            }
            return res;
        } catch (err) {
            if (retryCount < maxRetries && (document.visibilityState === 'hidden' || err.message.includes('fetch') || err.message.includes('NetworkError') || err.message.includes('Timeout'))) {
                console.warn('Network error or backgrounded in robustFetch. Retrying...', err);
                retryCount++;
                if (document.visibilityState === 'hidden') {
                    await new Promise(resolve => {
                        const onVis = () => {
                            if (document.visibilityState === 'visible') {
                                document.removeEventListener('visibilitychange', onVis);
                                resolve();
                            }
                        };
                        document.addEventListener('visibilitychange', onVis);
                    });
                }
                await new Promise(r => setTimeout(r, 2000));
                continue;
            }
            throw err;
        }
    }
}
'''

if 'robustFetch(' not in content:
    content = helper + '\n' + content

content = content.replace("fetch('/api/batch-valuation', {", "robustFetch('/api/batch-valuation', {")
content = re.sub(r'fetch\(`/api/analyst/(.*?)`\)', r'robustFetch(`/api/analyst/\1`)', content)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('robustFetch added and implemented for batch-valuation and analyst.')
