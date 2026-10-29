import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

PDF_PATH = "C:/Users/Faruk/.gemini/antigravity/scratch/wow-forever-dashboard/WoW_Forever_Dashboard_Projekt_Dokumentacija.pdf"

def generate_pdf_v2():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#b8860b'),
        alignment=1,
        spaceAfter=8
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#444444'),
        alignment=1,
        spaceAfter=20
    )

    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1a237e'),
        spaceBefore=14,
        spaceAfter=8
    )

    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#283593'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#222222'),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        leftIndent=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=3
    )

    story = []

    # Title
    story.append(Paragraph("WoW Forever Dashboard &amp; Intelligence Hub", title_style))
    story.append(Paragraph("Tehnicka Specifikacija, Arhitektura i Audit Sistemi (Verzija 2.0)<br/>Autori: Faruk &amp; Mirza | Launch: 05.11.2026. u 00:00 CET (Wien / BiH)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#b8860b'), spaceAfter=12))

    # 1. Status Implementacije
    story.append(Paragraph("1. Status Implementacije i Roadmap", h1_style))
    status_table_data = [
        [Paragraph("<b>Modul / Funkcionalnost</b>", body_style), Paragraph("<b>Status</b>", body_style), Paragraph("<b>Napomena &amp; Izvor</b>", body_style)],
        [Paragraph("WoW Forever Sistemi (Camping &amp; Legacy)", body_style), Paragraph("<font color='#2e7d32'><b>Implementirano</b></font>", body_style), Paragraph("Baza u data/guides.json sa zvanicnim Blizzard mehanikama.", body_style)],
        [Paragraph("Hunter Pet Skaliranje &amp; Cheat-Sheet", body_style), Paragraph("<font color='#2e7d32'><b>Implementirano</b></font>", body_style), Paragraph("Uvazene Forever promjene (skaliranje sa opremom lovca).", body_style)],
        [Paragraph("Faruk / Mirza Profili &amp; 'Heute fur uns'", body_style), Paragraph("<font color='#2e7d32'><b>Implementirano</b></font>", body_style), Paragraph("Prebacivanje profila sa prilagodjenim prioritetima dana.", body_style)],
        [Paragraph("Lokalni Countdown (CET Vrijeme)", body_style), Paragraph("<font color='#2e7d32'><b>Implementirano</b></font>", body_style), Paragraph("Tacno vezan za 05.11.2026 u 00:00 CET (Wien / Sarajevo).", body_style)],
        [Paragraph("Pametni Radar (Potvrdjeno / Fixed / Bug)", body_style), Paragraph("<font color='#2e7d32'><b>Implementirano</b></font>", body_style), Paragraph("Razlikuje 'fixed' (nema alarma) od aktivnih exploita.", body_style)],
        [Paragraph("Google-GenAI Klijent &amp; Zastita od Halucinacija", body_style), Paragraph("<font color='#2e7d32'><b>Implementirano</b></font>", body_style), Paragraph("Prelazak na moderni paket + fallback ako nema dovoljno detalja.", body_style)],
        [Paragraph("Auction House &amp; Interaktivni Kalkulator", body_style), Paragraph("<font color='#ef6c00'><b>Planirano</b></font>", body_style), Paragraph("Ostavljeno za fazu nakon starta kada se uspostave API-ji.", body_style)]
    ]
    t_status = Table(status_table_data, colWidths=[180, 100, 250])
    t_status.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f5f5f5')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_status)

    story.append(Spacer(1, 10))

    # 2. WoW Forever Specificnosti
    story.append(Paragraph("2. Zvanicne WoW Forever Mehanike (Blizzard Potvrdjeno)", h1_style))
    story.append(Paragraph("Za razliku od starog Vanilla 1.12 koda, WoW Forever uvodi fundamentalne novine koje ovaj dashboard prati:", body_style))
    story.append(Paragraph("• <b>Allianz Duo Sinergija (Faruk &amp; Mirza):</b> Mirza igra 100% Jäger (Kürschnerei &amp; Kräuterkunde) dok Faruk igra Schamana (Bergbau &amp; Engineering). Mirza prikuplja travke za kamping svijecu (+Intelligenz za Faruka) i kozu, dok Faruk rudari za inzenjerske bombe, target dummies (spasavanje od wipe-a u tamnicama) i podrsku totemima (Stoneskin, Windfury, Heals).", bullet_style))
    story.append(Paragraph("• <b>Camping Sistem:</b> Obicna vatra za kuvanje postaje mobilni kamp. 1 minut boravka daje Rested XP status na terenu. Profesije dodaju objekte: Kovaci (Sharpening Wheel: +AP), Krojaci (Faction Banner: +Spirit), Travari (Incense Candle: +Int), Alhemicari (Mobile Alchemielabor: craftovanje eliksira bez odlaska u Scholomance).", bullet_style))
    story.append(Paragraph("• <b>Hunter Pet Skaliranje:</b> Petovi vise ne kaskaju za likom u end-game fazi; njihova snaga, oklop i health direktno skaliraju sa agilnoscu i opremom Huntera.", bullet_style))
    story.append(Paragraph("• <b>Legacy Sistem:</b> Nalog-siroka progresija koja ubrzava razvoj alternativnih likova (twinkova) i istrazivanje novih Forever zona.", bullet_style))

    story.append(Spacer(1, 10))

    # 3. Zastita Podataka i Sigurnost
    story.append(Paragraph("3. Arhitektura Pouzdanosti (Fail-Safe &amp; Sigurnost)", h1_style))
    story.append(Paragraph("• <b>Otpornost Scrapera:</b> Pad jednog izvora (npr. PullPush timeout) ne zaustavlja ostale. Baza se nikada ne prepisuje praznim rezultatom (atomic save uz data/news_backup.json).", bullet_style))
    story.append(Paragraph("• <b>Kontrola AI Sadrzaja:</b> Prompt nalaze AI modelu da ako ulazni clanak nema konkretne detalje, eksplicitno ispise: <i>'Nema dovoljno informacija za preporuku'</i>, cime se eliminise izmisljanje laznih buildova.", bullet_style))
    story.append(Paragraph("• <b>Oznake Verifikacije:</b> Svaka kartica i clanak nose bedz: <i>'Blizzard-Bestatigt'</i>, <i>'Guide / Analyse'</i>, ili <i>'Community-Diskussion'</i>.", bullet_style))
    story.append(Paragraph("• <b>Pojasnjenje Lozinke:</b> Klijentska lozinka (SessionStorage) sluzi za privatni komfor prikaza. GitHub repozitorijum je javan za potrebe besplatnog GitHub Pages hostinga, a tajni API kljucevi su osigurani unutar GitHub Actions Secrets.", bullet_style))

    story.append(PageBreak())

    # 4. Moduli u Dashboardu
    story.append(Paragraph("4. Pregled Korisnickog Interfejsa (Dashboard Moduli)", h1_style))
    story.append(Paragraph("Dashboard (dostupan na https://faruk-salkic.github.io/wow-forever-dashboard/) sadrzi:", body_style))
    story.append(Paragraph("1. <b>Profil Switcher (Faruk: Schamane / Mirza: Jäger 100%):</b> Dinamicki prilagodjava sekciju 'Heute fur uns' prema ulogama: Faruk (Bergbau &amp; Engineering) i Mirza (Kürschnerei &amp; Kräuterkunde).", bullet_style))
    story.append(Paragraph("2. <b>Lokalni Countdown:</b> Odbrojava tacno do ponoci 05.11.2026. (CET).", bullet_style))
    story.append(Paragraph("3. <b>In-App Modal Reader:</b> Prikaz kompletnih sazetaka na njemackom jeziku unutar elegantnog pop-up prozora.", bullet_style))
    story.append(Paragraph("4. <b>Tab 'Camping &amp; Legacy':</b> Detaljan pregled svih profesijskih predmeta i bonusa u kampu.", bullet_style))
    story.append(Paragraph("5. <b>Tab 'Jager-Pets':</b> Pregled petova (Katze, Eber, Wolf) sa lokacijama za Alijansu i ulogama u grupi.", bullet_style))
    story.append(Paragraph("6. <b>Tab 'Leveling &amp; Dungeons':</b> Vodic za Farukov patuljacki start (Dun Morogh) uz cekanje na Mirzinu 100% potvrdu rase, zona ruta (1-60), te interaktivna checklista svih tamnickih questova (Deadmines, Stockades, Gnomeregan, SM, ZF, ST, BRD) sa lokacijama NPC-eva i pametnim pamtjenjem u browseru.", bullet_style))
    story.append(Paragraph("7. <b>Tab 'Gold &amp; Berufe':</b> Strategija profesija za prvi dan servera.", bullet_style))

    story.append(Spacer(1, 15))

    # 5. Peer Review Pitanja
    story.append(Paragraph("5. Smjernice za Dalje Unapredjenje (Za Eksterni AI Pregled)", h1_style))
    story.append(Paragraph("Prilikom pregleda ove specifikacije sa drugim AI modelom, fokusirajte se na:", body_style))
    story.append(Paragraph("• Da li je u kasnijoj fazi opravdano dodati Discord Webhook samo za 'confirmed exploit' statuse?", bullet_style))
    story.append(Paragraph("• Koji je najjednostavniji nacin za offline PWA cache kako bi dashboard radio bez interneta na mobitelu tokom igranja?", bullet_style))

    doc.build(story)
    print("V2 PDF uspješno generisan:", PDF_PATH)

if __name__ == "__main__":
    generate_pdf_v2()
