import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

PDF_PATH = "C:/Users/Faruk/.gemini/antigravity/scratch/wow-forever-dashboard/WoW_Forever_Dashboard_Projekt_Dokumentacija.pdf"

def generate_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#b8860b'),
        alignment=1,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#555555'),
        alignment=1,
        spaceAfter=25
    )

    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1a237e'),
        spaceBefore=15,
        spaceAfter=8
    )

    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#283593'),
        spaceBefore=10,
        spaceAfter=5
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#222222'),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        leftIndent=15,
        textColor=colors.HexColor('#333333'),
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1b5e20'),
        backColor=colors.HexColor('#f1f8e9'),
        spaceAfter=6
    )

    story = []

    # Title & Header
    story.append(Paragraph("🐉 WoW Forever Dashboard & Automation", title_style))
    story.append(Paragraph("Kompletna Arhitektura, Specifikacija i Pregled Projekta<br/>Autori: Faruk & Mirza | Launch: 04.11.2026", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#b8860b'), spaceAfter=15))

    # 1. Summary
    story.append(Paragraph("1. Sažetak Projekta (Project Summary)", h1_style))
    story.append(Paragraph(
        "Ovaj projekat je automatizovani sistem i moderan web dashboard namijenjen za praćenje izlaska i igranja novog servera "
        "<b>World of Warcraft: Forever (Blizzard, izlazak 04.11.2026. u 23:00 UTC)</b>. Sistem je potpuno samoodrživ na besplatnoj infrastrukturi "
        "(GitHub Pages + GitHub Actions) i služi za svakodnevni brifing dvojici igrača (Alijansa).", body_style))

    story.append(Spacer(1, 8))

    # Key specs table
    data_summary = [
        [Paragraph("<b>Parametar</b>", body_style), Paragraph("<b>Vrijednost / Opis</b>", body_style)],
        [Paragraph("Frakcija", body_style), Paragraph("Allianz (Alliance)", body_style)],
        [Paragraph("Ciljne Klase", body_style), Paragraph("Hunter (Glavna), Shaman, Priest, Rogue", body_style)],
        [Paragraph("Frontend URL", body_style), Paragraph("https://faruk-salkic.github.io/wow-forever-dashboard/", body_style)],
        [Paragraph("GitHub Repo", body_style), Paragraph("https://github.com/Faruk-Salkic/wow-forever-dashboard (Public)", body_style)],
        [Paragraph("Zaštita / Auth", body_style), Paragraph("Klijentska lozinka (SessionStorage: 'wowforever')", body_style)],
        [Paragraph("Jezik Sadržaja", body_style), Paragraph("Njemački (Deutsch) za sve analize, sažetke i UI", body_style)],
        [Paragraph("Automatizacija", body_style), Paragraph("GitHub Actions Cron job svakog dana u 09:00 CET", body_style)]
    ]
    t_summary = Table(data_summary, colWidths=[140, 390])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f5f5f5')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_summary)

    story.append(Spacer(1, 15))

    # 2. Arhitektura
    story.append(Paragraph("2. Tehnička Arhitektura i Tehnologije", h1_style))
    story.append(Paragraph("Projekat se sastoji od tri ključna stuba:", body_style))
    story.append(Paragraph("• <b>Scraper Engine (Python 3.11):</b> Smješten u <code>scraper/scrape.py</code>. Vuče RSS feedove sa vodećih njemačkih i globalnih portala (Buffed.de, GameStar, Wowhead, MMO-Champion, Icy Veins, Blue Tracker) te Reddit postove sa subreddita <code>r/wow, r/classicwow, r/wowforever</code> putem <b>PullPush.io API-ja</b> (potpuno zaobilaženje potrebe za Reddit nalogom ili API tokenima).", bullet_style))
    story.append(Paragraph("• <b>AI Summarizer & Filter:</b> Uključuje Google Gemini AI API podršku koja duge tekstove i vodiče automatski sumira u 3 strukturirana paragrafa na njemačkom: <i>Was ist passiert?</i>, <i>Was bedeutet das für unsere Klassen?</i> i <i>Was sollten wir tun?</i>.", bullet_style))
    story.append(Paragraph("• <b>Strogi Game-Filter & Blacklist:</b> Isključuje sve ostale igre (npr. RDR2), promocije iz Store-a, mountove, kozmetiku i irelevantne ekspanzije (Midnight, The War Within, Dragonflight itd.). Fokusira se isključivo na: <b>WoW Forever + Talente, Buildove, Buff/Nerf promjene, Exploite i BiS iteme</b>.", bullet_style))
    story.append(Paragraph("• <b>Frontend Dashboard (Glassmorphism Single Page App):</b> Čisti HTML5/CSS3/JavaScript bez teških frameworka. Posjeduje 3D rotirajući WoW amblem, zvjezdano nebo, countdown sat do launcha, in-app modalni čitač članaka i brze filtere.", bullet_style))

    story.append(Spacer(1, 15))

    # 3. Struktura Fajlova
    story.append(Paragraph("3. Struktura Fajlova u Repozitoriju", h1_style))
    files_data = [
        [Paragraph("<b>Putanja</b>", body_style), Paragraph("<b>Svrha i Funkcionalnost</b>", body_style)],
        [Paragraph("<code>index.html</code>", code_style), Paragraph("Kompletan UI dashboard (login, countdown, filteri, modal reader, tabovi za BiS, Petove, Leveling, Gold).", body_style)],
        [Paragraph("<code>scraper/scrape.py</code>", code_style), Paragraph("Python scraper koji pretražuje RSS i Reddit, filtrira neželjene teme i puni bazu.", body_style)],
        [Paragraph("<code>scraper/requirements.txt</code>", code_style), Paragraph("Python paketi: requests, feedparser, beautifulsoup4, google-generativeai.", body_style)],
        [Paragraph("<code>data/news.json</code>", code_style), Paragraph("Glavna baza sačuvanih pročišćenih vijesti koje dashboard prikazuje.", body_style)],
        [Paragraph("<code>data/bis.json</code>", code_style), Paragraph("Best-in-Slot tabele po slotovima za Hunter, Shaman, Priest i Rogue.", body_style)],
        [Paragraph("<code>data/guides.json</code>", code_style), Paragraph("Baza podataka za Hunter petove, leveling rute, tamnice i gold pravila.", body_style)],
        [Paragraph("<code>data/seen_ids.json</code>", code_style), Paragraph("Hash memorija viđenih vijesti radi sprečavanja duplikata.", body_style)],
        [Paragraph("<code>.github/workflows/scrape.yml</code>", code_style), Paragraph("GitHub Actions skripta koja svakog jutra automatski pokreće scraper i radi git commit & push.", body_style)],
    ]
    t_files = Table(files_data, colWidths=[160, 370])
    t_files.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f5f5f5')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_files)

    story.append(PageBreak())

    # 4. Moduli u Dashboardu
    story.append(Paragraph("4. Detaljan Pregled Modula u Dashboardu", h1_style))
    
    story.append(Paragraph("A. ⏳ Live Countdown do Launcha", h2_style))
    story.append(Paragraph("Automatski brojač u realnom vremenu koji preračunava dane, sate, minute i sekunde do zvaničnog starta (04.11.2026. u 23:00 UTC).", body_style))

    story.append(Paragraph("B. 🚨 Exploit & High Priority Radar", h2_style))
    story.append(Paragraph("Crveni pulsirajući alert na vrhu novosti koji se aktivira čim se u bazi detektuje riječ exploit/bug/glitch/abuse kako bi igrači iskoristili mehanike prije Blizzardovog hotfixa.", body_style))

    story.append(Paragraph("C. 📖 In-App Modal Reader", h2_style))
    story.append(Paragraph("Korisnik ne mora napuštati dashboard i odlaziti na eksterne sajtove. Klikom na bilo koju karticu otvara se pop-up prozor sa detaljnim sažetkom na njemačkom jeziku.", body_style))

    story.append(Paragraph("D. 🏆 BiS-Items Tab (Best in Slot)", h2_style))
    story.append(Paragraph("Poseban tab sa tabelarnim prikazom opreme (Glava, Vrat, Ramena, Oružje, Trinketi) i preporukama talenata za 4 klase (Hunter Beast Mastery, Shaman Enhancement/Ele, Priest Shadow/Holy, Rogue Sub/Assa).", body_style))

    story.append(Paragraph("E. 🐾 Jäger-Pets Modul (Hunter Pet Cheat-Sheet)", h2_style))
    story.append(Paragraph("Specijalizovan vodič za Huntera sa kategorizacijom petova: Mačke (Leveling/DPS), Svinje (Charge/Tank), Vukovi (Furious Howl party buff) i Petovi sa attack brzinom 1.0 - 1.2s za PvP prekidanje castera. Uključuje hranu i lokacije.", body_style))

    story.append(Paragraph("F. 🗺️ Allianz Leveling & Dungeon Checklist", h2_style))
    story.append(Paragraph("Vodič kroz zone od nivoa 1 do 60 (Westfall, Redridge, Duskwood, STV, Tanaris itd.) te spisak svih ključnih tamnica (Deadmines, Stockades, SM, ZF, BRD) i plavog loota.", body_style))

    story.append(Paragraph("G. 💰 Gold-Making & Berufe Leitfaden", h2_style))
    story.append(Paragraph("Preporuke profesija za brzi gold od Levela 1 (Skinning + Mining/Herbalism) i 3 zlatna pravila štednje za Level 40 mounta.", body_style))

    story.append(Spacer(1, 15))

    # 5. Prijedlozi za Drugi AI Model
    story.append(Paragraph("5. Pitanja i Prijedlozi za Eksterni AI Pregled (Peer Review)", h1_style))
    story.append(Paragraph(
        "Kada ovaj PDF učitate u drugi napredni AI model (npr. GPT-4, Claude 3.5 Sonnet ili Gemini Pro), možete postaviti sljedeća pitanja kako biste dobili dodatne ideje za poboljšanje:", body_style))
    
    ideas = [
        "1. <b>Dodatni izvori podataka:</b> Da li postoje specifični Discord webhookovi ili WoW Classic baze (npr. ClassicDB, Twinhead) koje bismo mogli direktno indeksirati?",
        "2. <b>Discord / Webhook Integracija:</b> Kako najjednostavnije dodati automatizovano slanje obavještenja na Discord kanal kad god se pronađe 'Exploit' tag?",
        "3. <b>Interaktivni Talent Kalkulator:</b> Da li bi se u dashboard mogao ugraditi interaktivni 1.12 / Forever talent kalkulator direktno u klijentski JS?",
        "4. <b>Offline / PWA Podrška:</b> Da li je korisno dodati Service Worker kako bi dashboard radio na mobilnom telefonu kao nativna ikonica bez ponovnog učitavanja?",
        "5. <b>Auction House Tracking:</b> Da li postoji javni API ili addon dump za cijene sirovina na novom serveru?"
    ]
    for idea in ideas:
        story.append(Paragraph(idea, bullet_style))

    doc.build(story)
    print("PDF uspješno kreiran:", PDF_PATH)

if __name__ == "__main__":
    generate_pdf()
