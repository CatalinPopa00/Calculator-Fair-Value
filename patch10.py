import sys

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove endsWith('y')
    content = content.replace(" && e.period && e.period.endsWith('y')", "")

    # 2. Fix generatePeersTable dynFwdEps
    bad_peers = """            const eList = globalData.eps_estimates || [];
            const eEsts = eList.filter(e => e && e.status !== 'reported');
            if (eEsts.length > 0) {
                dynFwdEps = window._currentScenario === 'bear' ? eEsts[0].low : eEsts[0].high;
            }"""
    good_peers = """            const eList = globalData.eps_estimates || [];
            const eEsts = eList.filter(e => e && e.status !== 'reported');
            if (eEsts.length >= 2) {
                if (window._currentScenario === 'bear') dynFwdEps = (eEsts[0].low + eEsts[1].low) / 2.0;
                else if (window._currentScenario === 'bull') dynFwdEps = (eEsts[0].high + eEsts[1].high) / 2.0;
                else dynFwdEps = (eEsts[0].avg + eEsts[1].avg) / 2.0;
            } else if (eEsts.length === 1) {
                if (window._currentScenario === 'bear') dynFwdEps = eEsts[0].low;
                else if (window._currentScenario === 'bull') dynFwdEps = eEsts[0].high;
                else dynFwdEps = eEsts[0].avg;
            }"""

    # 3. Fix renderCompanyData dynFwdEps & dynFwdRev
    bad_company = """                                    if (globalData.eps_estimates && globalData.eps_estimates.length >= 2) {
                                        const fwdEst = globalData.eps_estimates[1]; // FY1
                                        if (_currentScenario === 'bear' && fwdEst.low) dynFwdEps = fwdEst.low;
                                        if (_currentScenario === 'bull' && fwdEst.high) dynFwdEps = fwdEst.high;
                                    }
                                    if (globalData.rev_estimates && globalData.rev_estimates.length >= 2) {
                                        const fwdEstRev = globalData.rev_estimates[1]; // FY1
                                        if (_currentScenario === 'bear' && fwdEstRev.low) dynFwdRev = fwdEstRev.low;
                                        if (_currentScenario === 'bull' && fwdEstRev.high) dynFwdRev = fwdEstRev.high;
                                    }"""
    good_company = """                                    if (globalData.eps_estimates && globalData.eps_estimates.length >= 2) {
                                        const eEsts = globalData.eps_estimates.filter(e => e && e.status !== 'reported');
                                        if (eEsts.length >= 2) {
                                            if (_currentScenario === 'bear') dynFwdEps = (eEsts[0].low + eEsts[1].low) / 2.0;
                                            else if (_currentScenario === 'bull') dynFwdEps = (eEsts[0].high + eEsts[1].high) / 2.0;
                                            else dynFwdEps = (eEsts[0].avg + eEsts[1].avg) / 2.0;
                                        } else if (eEsts.length === 1) {
                                            if (_currentScenario === 'bear') dynFwdEps = eEsts[0].low;
                                            else if (_currentScenario === 'bull') dynFwdEps = eEsts[0].high;
                                            else dynFwdEps = eEsts[0].avg;
                                        }
                                    }
                                    if (globalData.rev_estimates && globalData.rev_estimates.length >= 2) {
                                        const rEsts = globalData.rev_estimates.filter(e => e && e.status !== 'reported');
                                        if (rEsts.length >= 2) {
                                            if (_currentScenario === 'bear') dynFwdRev = (rEsts[0].low + rEsts[1].low) / 2.0;
                                            else if (_currentScenario === 'bull') dynFwdRev = (rEsts[0].high + rEsts[1].high) / 2.0;
                                            else dynFwdRev = (rEsts[0].avg + rEsts[1].avg) / 2.0;
                                        } else if (rEsts.length === 1) {
                                            if (_currentScenario === 'bear') dynFwdRev = rEsts[0].low;
                                            else if (_currentScenario === 'bull') dynFwdRev = rEsts[0].high;
                                            else dynFwdRev = rEsts[0].avg;
                                        }
                                    }"""

    replacements = [
        (bad_peers, good_peers),
        (bad_company, good_company)
    ]

    for b, g in replacements:
        if b in content:
            content = content.replace(b, g)
            print("Successfully replaced a block.")
        else:
            print(f"Failed to find block:\n{b[:100]}...")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Success")

if __name__ == '__main__':
    main()
