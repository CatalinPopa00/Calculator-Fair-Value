# 🔧 API Debugging Guide

## Eroare: "Network response was not ok at analyze ticker"

### 📊 Status: Diagnosing Issue

Aceasta înseamnă că endpoint-ul `/api/valuation/{ticker}` returnează un status code care nu este 200-299.

---

## ✅ Pași de Debugging (FastAPI Backend)

### 1. **Verifică dacă backend-ul rulează**
```bash
# Pe Windows:
python api/index.py

# Pe macOS/Linux:
python3 api/index.py
```

Backend ar trebui să pornească pe `http://127.0.0.1:8000`

### 2. **Testează endpoint-ul direct în browser**
```
http://127.0.0.1:8000/api/valuation/AAPL
```

Ar trebui să primești JSON cu date despre Apple.

### 3. **Verifică logs-urile backend-ului**
Caută liniile care conțin:
- `VALUATION CRASH for [ticker]:`
- `DEBUG: Main scraper task failed`
- `DEBUG: Parallel peer fetch failed`

---

## 🛠️ Cauze Comune și Soluții

| Status | Problemă | Soluție |
|--------|----------|---------|
| **404** | Endpoint nu există | Verific route în `api/index.py` |
| **500** | Eroare server | Verific logs și exceptions |
| **503** | Serviciul indisponibil | Verific dacă backend rulează |
| **No response** | Frontend/Backend pe domenii diferite | Configureaza CORS |

---

## 🔍 Verificare Frontend

Deschide **DevTools** (F12):

```javascript
// Console Tab - executa:
fetch('/api/valuation/AAPL')
  .then(r => {
    console.log('Status:', r.status);
    console.log('OK:', r.ok);
    return r.json();
  })
  .then(data => console.log('Response:', data))
  .catch(err => console.error('Error:', err));
```

---

## ⚡ Soluție Rapidă (Redeployare)

### Vercel:
```bash
git push origin fix/api-error-handling
# Merge to main pe GitHub
# Vercel va redeploya automat
```

### Local (Development):
```bash
npm run dev
# sau
python api/index.py
```

---

## 📝 Note Importante

- **Endpoint URL**: `/api/valuation/{ticker}` (GET)
- **CORS**: Deja configurat în `api/index.py` (linia 87-93)
- **Cache**: TTL de 1 oră - clearează dacă vrei date fresh
- **Timeouts**: 12 secunde pentru peer data

---

**Status: Aștept feedback din frontend!** ✋
