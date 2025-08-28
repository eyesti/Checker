import os
import requests
import re
import time
import threading
from datetime import datetime
from flask import Flask

# === KONFIGURATION ===
EVENT_URL = "https://www.airsoft-verzeichnis.de/index.php?status=event&eventnummer=024906"

# Aus Umgebungsvariablen laden (auf Render setzen!)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

CHECK_INTERVAL = 60 * 3  # alle 3 Minuten prüfen
MAX_TEILNEHMER = 45      # aktuelle Grenze
LOGFILE = "teilnehmer_log.txt"

# Fake Browser-Header
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0 Safari/537.36"
    )
}

# Flask Web-App (für Render / UptimeRobot)
app = Flask(__name__)

@app.route("/")
def home():
    return "Airsoft Checker läuft ✅"


def send_telegram_message(message: str):
    """Nachricht per Telegram senden"""
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ BOT_TOKEN oder CHAT_ID fehlt! Bitte in Render als Environment Variable setzen.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Fehler beim Senden der Nachricht:", e)


def get_teilnehmerzahl():
    """Teilnehmerzahl per Regex suchen – nimmt die größte gefundene Zahl"""
    try:
        response = requests.get(EVENT_URL, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            html = response.text
            matches = re.findall(r"Teilnehmer[^0-9]*([0-9]+)", html)
            if matches:
                zahlen = [int(x) for x in matches]
                return max(zahlen)
    except Exception as e:
        print("Fehler beim Prüfen der Seite:", e)
    return None


def log_teilnehmerzahl(zahl):
    """Teilnehmerzahl mit Zeitstempel in Logdatei schreiben"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - Teilnehmer: {zahl}\n")


def background_checker():
    """Prüfung im Hintergrund alle X Minuten"""
    letzte_teilnehmerzahl = None
    while True:
        teilnehmer = get_teilnehmerzahl()

        if teilnehmer is not None:
            print(f"Aktuell eingetragene Teilnehmer: {teilnehmer}")
            log_teilnehmerzahl(teilnehmer)

            if teilnehmer < MAX_TEILNEHMER and teilnehmer != letzte_teilnehmerzahl:
                send_telegram_message(
                    f"🎯 Ein Platz ist frei geworden! Aktuell {teilnehmer}/{MAX_TEILNEHMER} Teilnehmer.\n{EVENT_URL}"
                )

            letzte_teilnehmerzahl = teilnehmer
        else:
            print("Konnte Teilnehmerzahl nicht auslesen.")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    print("Starte Teilnehmer-Überwachung...")

    # Start-Benachrichtigung
    send_telegram_message("✅ Airsoft Checker gestartet und überwacht jetzt die Teilnehmerzahl.")

    # Hintergrundthread starten
    t = threading.Thread(target=background_checker, daemon=True)
    t.start()

    # Flask Webserver starten (für Render Ping)
    app.run(host="0.0.0.0", port=8080)
