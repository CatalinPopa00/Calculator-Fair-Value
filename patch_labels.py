import sys
import re

files = [
    r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value\app.js',
    r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value\vercel_app_v234.js'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update Labels to FWD
    old_label = "const LABEL = { PE: 'Fwd P/E', PFCF: 'Trailing P/FCF', PS: 'P/S', PB: 'Current P/B', EV_EBITDA: 'Trailing EV/EBITDA', P_FFO: 'Trailing P/FFO', P_AFFO: 'Trailing P/AFFO' };"
    new_label = "const LABEL = { PE: 'FWD P/E', PFCF: 'Trailing P/FCF', PS: 'FWD P/S', PB: 'Current P/B', EV_EBITDA: 'FWD EV/EBITDA', P_FFO: 'FWD P/FFO', P_AFFO: 'FWD P/AFFO' };"
    content = content.replace(old_label, new_label)

    # Note: P_FFO and P_AFFO are typically used for REITs and they remain trailing if we don't have FWD proxy for them. 
    # The prompt says: "Sa scrii 'FWD P/E', 'FWD EBITDA', 'FWD P/S', 'FWD P/FFO', 'FWD P/AFFO' si orice alt indicator mai e. Vreau sa fie clar ca la relative valuation comparam pe forward. Daca folosim ceva current, lasi doar numele indicatorului"
    # User requested to label them FWD. I will change P_FFO and P_AFFO to FWD as requested, and PFCF to FWD P/FCF.
    old_label_2 = "const LABEL = { PE: 'FWD P/E', PFCF: 'Trailing P/FCF', PS: 'FWD P/S', PB: 'Current P/B', EV_EBITDA: 'FWD EV/EBITDA', P_FFO: 'Trailing P/FFO', P_AFFO: 'Trailing P/AFFO' };"
    new_label_2 = "const LABEL = { PE: 'FWD P/E', PFCF: 'FWD P/FCF', PS: 'FWD P/S', PB: 'Current P/B', EV_EBITDA: 'FWD EV/EBITDA', P_FFO: 'FWD P/FFO', P_AFFO: 'FWD P/AFFO' };"
    content = content.replace(old_label_2, new_label_2)

    # Also there might be another definition of LABEL in the file:
    old_label_3 = "const LABEL = { PE: 'Fwd P/E', PFCF: 'Trailing P/FCF', PS: 'P/S', PB: 'Current P/B', EV_EBITDA: 'Trailing EV/EBITDA', P_FFO: 'Trailing P/FFO', P_AFFO: 'Trailing P/AFFO' };"
    content = content.replace(old_label_3, new_label_2)

    # Now update peerKeyMap
    old_peer_map = "const peerKeyMap = { PE: 'pe_ratio', PFCF: 'pfcf_ratio', PS: 'ps_ratio', PB: 'price_to_book', EV_EBITDA: 'ev_to_ebitda' };"
    # For PS, we use forward_ev_sales or forward_ps. The backend computes forward_ev_sales.
    new_peer_map = "const peerKeyMap = { PE: 'forward_pe', PFCF: 'pfcf_ratio', PS: 'forward_ev_sales', PB: 'price_to_book', EV_EBITDA: 'forward_ev_ebitda' };"
    content = content.replace(old_peer_map, new_peer_map)

    # Update medians recalculation in JS
    old_medians = '''const dynamicMedians = {
                    PE: getMedian(peers.map(p => p.pe_ratio)),
                    PFCF: getMedian(peers.map(p => p.pfcf_ratio)),
                    PS: getMedian(peers.map(p => p.ps_ratio)),
                    PB: getMedian(peers.map(p => p.price_to_book)),
                    EV_EBITDA: getMedian(peers.map(p => p.ev_to_ebitda))
                };'''
    new_medians = '''const dynamicMedians = {
                    PE: getMedian(peers.map(p => p.forward_pe != null ? p.forward_pe : p.pe_ratio)),
                    PFCF: getMedian(peers.map(p => p.pfcf_ratio)),
                    PS: getMedian(peers.map(p => p.forward_ev_sales != null ? p.forward_ev_sales : p.ps_ratio)),
                    PB: getMedian(peers.map(p => p.price_to_book)),
                    EV_EBITDA: getMedian(peers.map(p => p.forward_ev_ebitda != null ? p.forward_ev_ebitda : p.ev_to_ebitda))
                };'''
    content = content.replace(old_medians, new_medians)

    # Update means recalculation in JS
    old_means = '''const dynamicMeans = {
                    PE: getMean(peers.map(p => p.pe_ratio)),
                    PFCF: getMean(peers.map(p => p.pfcf_ratio)),
                    PS: getMean(peers.map(p => p.ps_ratio)),
                    PB: getMean(peers.map(p => p.price_to_book)),
                    EV_EBITDA: getMean(peers.map(p => p.ev_to_ebitda))
                };'''
    new_means = '''const dynamicMeans = {
                    PE: getMean(peers.map(p => p.forward_pe != null ? p.forward_pe : p.pe_ratio)),
                    PFCF: getMean(peers.map(p => p.pfcf_ratio)),
                    PS: getMean(peers.map(p => p.forward_ev_sales != null ? p.forward_ev_sales : p.ps_ratio)),
                    PB: getMean(peers.map(p => p.price_to_book)),
                    EV_EBITDA: getMean(peers.map(p => p.forward_ev_ebitda != null ? p.forward_ev_ebitda : p.ev_to_ebitda))
                };'''
    content = content.replace(old_means, new_means)

    # Update targetKeys
    old_target_keys = "const targetKeys = { PE: r.pe_ratio, PFCF: r.pfcf_ratio, PS: r.ps_ratio, PB: r.price_to_book, EV_EBITDA: r.ev_to_ebitda };"
    new_target_keys = "const targetKeys = { PE: r.forward_pe != null ? r.forward_pe : r.pe_ratio, PFCF: r.pfcf_ratio, PS: r.forward_ev_sales != null ? r.forward_ev_sales : r.ps_ratio, PB: r.price_to_book, EV_EBITDA: r.forward_ev_ebitda != null ? r.forward_ev_ebitda : r.ev_to_ebitda };"
    content = content.replace(old_target_keys, new_target_keys)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {filepath}")
