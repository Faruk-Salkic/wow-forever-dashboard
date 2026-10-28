# Faruk & Mirza — WoW Forever Dashboard 🐉

Privatni daily-news dashboard za WoW Forever (04.11.2026).  
Prati vijesti za **Hunter 🏹 · Shaman 🔵 · Priest ✨ · Rogue 🗡️** — Alliance.

## 🚀 Setup (5 minuta)

### 1. Napravi GitHub repo
- Idi na [github.com](https://github.com) → **New repository**
- Ime: `wow-forever` (ili što hoćeš)
- Visibility: **Private** ✅ (ne treba biti public!)
- Klikni **Create repository**

### 2. Upload fajlova
- Uploadaj sve fajlove iz ovog foldera na GitHub
- Ili koristi Git:
```bash
git init
git add .
git commit -m "🐉 WoW Forever Dashboard init"
git remote add origin https://github.com/TVOJE_IME/wow-forever.git
git push -u origin main
```

### 3. Uključi GitHub Pages
- Idi na **Settings** → **Pages**
- Source: **Deploy from a branch** → `main` → `/ (root)`
- Sačuvaj → stranica će biti na: `https://TVOJE_IME.github.io/wow-forever`

### 4. Promijeni lozinku!
Otvori `index.html` i nađi ovu liniju:
```js
const PASSWORDS = ["wowforever", "farukimirza", "wow2026"];
```
Promijeni na svoju lozinku i pushai izmjenu.

### 5. GitHub Actions — automatski scraper
- Idi na **Settings** → **Actions** → **General**
- Pod "Workflow permissions" → odaberi **Read and write permissions** → Sačuvaj
- Scraper će se pokrenuti automatski svaki dan u 09:00 CET

### 6. Ručno pokretanje prvog puta
- Idi na tab **Actions** u svom repou
- Klikni na `WoW Forever Daily News Scraper`
- Klikni **Run workflow** → Run
- Za 1-2 minute news.json će biti ažuriran!

---

## 🔗 Custom link opcije

| Opcija | Link | Cijena |
|--------|------|--------|
| GitHub Pages (default) | `faruk.github.io/wow-forever` | Besplatno |
| Netlify deploy | `wow-novosti.netlify.app` | Besplatno |
| Custom domena | `wow.faruk.ba` ili sl. | ~\$10/god |

Za Netlify: drag & drop folder na [netlify.com/drop](https://netlify.com/drop) — gotovo!

---

## 📋 Struktura projekta

```
wow-forever-dashboard/
├── index.html              ← Dashboard (glassmorphism UI)
├── data/
│   └── news.json           ← Scraped vijesti (auto-update)
├── scraper/
│   ├── scrape.py           ← Python scraper
│   └── requirements.txt
└── .github/
    └── workflows/
        └── scrape.yml      ← GitHub Actions job
```

