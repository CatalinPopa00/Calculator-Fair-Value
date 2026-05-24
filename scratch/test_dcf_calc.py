def calc_dcf(fcf, growth, wacc, perp, shares, cash, debt, exit_mult=10.0, method='perpetual'):
    final_wacc = max(0.07, min(wacc, 0.105))
    pv = 0.0
    f = fcf
    for i in range(1, 11):
        g = growth[i-1] if isinstance(growth, list) else growth
        f *= (1.0 + g)
        pv += f / ((1.0 + final_wacc) ** i)
    
    if method == 'perpetual':
        tv = (f * (1.0 + perp)) / (final_wacc - perp)
    else:
        tv = f * exit_mult
        
    pv_tv = tv / ((1.0 + final_wacc) ** 10)
    ev = pv + pv_tv
    eq_val = ev + cash - debt
    return eq_val / shares

fcf = 9087000000.0
shares = 774878436
cash = 16024000512.0
debt = 18413000000.0
wacc = 0.09
perp = 0.025

# 1. Custom growth array with 13.4%
g_134 = [0.134, 0.134, 0.134, 0.114, 0.114, 0.114, 0.094, 0.094, 0.074, 0.074]
val_134 = calc_dcf(fcf, g_134, wacc, perp, shares, cash, debt)
print(f"13.4% value: {val_134}")

# 2. Let's test with growth array from Rev. G.r. (average of FY26 and FY27 = 9.2%)
# But wait! What if Rev. G.r. actually uses 13.4% in the frontend?
g_92 = [0.092, 0.092, 0.092, 0.072, 0.072, 0.072, 0.052, 0.052, 0.032, 0.032]
val_92 = calc_dcf(fcf, g_92, wacc, perp, shares, cash, debt)
print(f"9.2% value: {val_92}")
