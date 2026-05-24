import os

files = ['app.js', 'vercel_app.js', 'vercel_app_v234.js']

translations = {
    "🔴 PE Premium": "🔴 Premium PE",
    "🟢 PE Atractiv": "🟢 Attractive PE",
    "🟡 PE Moderat": "🟡 Moderate PE",
    "Câștig excepțional non-recurent ce depășește 100% din venituri.": "One-off exceptional gain exceeding 100% of revenue.",
    "⚠️ Profit Excepțional": "⚠️ Exceptional Profit",
    "💎 Marje Ridicate": "💎 High Margins",
    "⚠️ Marje Reduse": "⚠️ Low Margins",
    "📊 Marje Sănătoase": "📊 Healthy Margins",
    "🛡️ Grad Îndatorare Sigur": "🛡️ Safe Debt Level",
    "⚠️ Grad Îndatorare Ridicat": "⚠️ High Debt Level",
    "⚖️ Datorie Echilibrată": "⚖️ Balanced Debt",
    "Pipeline clinic, decizie FDA sau fază de testare detectată.": "Clinical pipeline, FDA decision, or testing phase detected.",
    "🧪 Catalyst Clinic": "🧪 Clinical Catalyst",
    "Activitate M&A, fuziuni sau costuri de integrare detectate.": "M&A activity, mergers, or integration costs detected.",
    "🤝 Tranzacție M&A": "🤝 M&A Transaction",
    "Analiză specifică pe segmente de activitate sau divizii.": "Specific analysis on business segments or divisions.",
    "📈 Focus pe Segmente": "📈 Segment Focus",
    "⏳ SE GENEREAZĂ ANALIZA AI...": "⏳ GENERATING AI ANALYSIS...",
    "✨ ANALIZĂ AI": "✨ AI ANALYSIS",
    "Rezumat Corporativ": "Corporate Summary",
    "Copiază rezumatul în clipboard": "Copy summary to clipboard",
    ">📋</span> <span id=\"copy-brief-text\">Copiază</span>": ">📋</span> <span id=\"copy-brief-text\">Copy</span>",
    "🏢 Prezentare Generală": "🏢 Overview",
    "⚖️ Analiză SWOT": "⚖️ SWOT Analysis",
    "📰 Informații de Piață": "📰 Market News",
    "${prof.name || 'Compania'} este clasificată în sectorul": "${prof.name || 'The company'} is classified in the",
    ", industria": " sector,",
    "</span>.": "</span> industry."
}

for file in files:
    filepath = os.path.join(r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value", file)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for ro, en in translations.items():
            content = content.replace(ro, en)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Translated {file}")
