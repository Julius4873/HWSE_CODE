"""Reaktionsspiel, Teile A–E, für MicroPython auf einem klassischen ESP32.

BEISPIEL-PINS: Vor dem Start mit dem tatsächlichen Aufbau abgleichen!
LDR_SCHWELLE mit den eigenen Hell-/Dunkelwerten kalibrieren.
Alle Abläufe einschließlich Tönen und Melodie laufen ohne sleep().
"""
from machine import Pin, ADC, PWM
import time
import random

# ---- Zeiten (ms): unverändert aus der Vorlage ----
T_WARTEN_MIN   = 2000
T_WARTEN_MAX   = 5000
T_PIEP         = 150
T_TIMEOUT      = 2000
T_ERGEBNIS     = 3000
T_FEHLSTART    = 1500
T_BLINK        = 200
T_MIN_REAKTION = 100
T_MODUS        = 2000

# ---- Töne (Hz): unverändert aus der Vorlage ----
F_SIGNAL = 2000
F_FEHLER = 200
MELODIE  = [(523, 150), (659, 150), (784, 150), (1047, 400)]

# ---- LDR ----
LDR_SCHWELLE = 1500  # Am Board messen! Darunter gilt der LDR als abgedeckt.

# ---- ESP32-Beispielbelegung, an eigenes Board anpassen ----
# LED-/Taster-Pins aus den bisherigen Ampel-Dateien; Buzzer zusätzlich GP26.
# GPIO34 ist ADC1 und nur Eingang. Kein interner Pull-up am LDR nötig:
# Der externe Spannungsteiler definiert seinen Pegel.
PIN_LED_GRUEN = 25
PIN_LED_GELB  = 27
PIN_LED_ROT   = 12
PIN_BTN       = 4
PIN_BUZZER    = 26
PIN_LDR       = 34

led_gruen = None
led_gelb = None
led_rot = None
button = None
buzzer = None
ldr = None
letzter_ton = None

# ---- State Machine ----
BEREIT = 0
WARTEN = 1
SIGNAL = 2
ERGEBNIS = 3
FEHLSTART = 4


def ton(freq):
    """PWM nur bei einer Tonänderung anfassen; ton(0) = aus."""
    global letzter_ton
    if freq == letzter_ton:
        return
    if freq:
        buzzer.freq(freq)
        buzzer.duty_u16(32768)
    else:
        buzzer.duty_u16(0)
    letzter_ton = freq


class Reaktionsspiel:
    """Ein update() entspricht einem kurzen, nicht-blockierenden Durchlauf.

    Taster und LDR werden auch in ignorierten Zuständen weiter beobachtet.
    Daher zählt ein dort begonnener/gehaltener Druck später nicht erneut.
    Die Bestzeit bleibt bis zum Neustart im RAM erhalten.
    """

    def __init__(self, jetzt, tasterwert, ldrwert):
        self.state = BEREIT
        self.state_start = jetzt
        self.letzter_taster = tasterwert
        self.letzter_ldr = ldrwert < LDR_SCHWELLE
        self.wartezeit = T_WARTEN_MIN
        self.bestzeit = None
        self.neue_bestzeit = False
        self.duell = False
        self.modus_start = None
        self.modus_gesperrt = False
        self.bestaetigung_start = None
        self.bestaetigung_anzahl = 0

    def wechsel(self, neu, jetzt):
        self.state = neu
        self.state_start = jetzt
        # Modus-Haltezeit zählt ausschließlich während BEREIT.
        self.modus_start = None
        if neu != BEREIT:
            self.bestaetigung_start = None
        if neu == WARTEN:
            self.wartezeit = random.randint(T_WARTEN_MIN, T_WARTEN_MAX)
            self.neue_bestzeit = False

    def modus_pruefen(self, jetzt, abgedeckt):
        """Pro durchgehendem Abdecken nur einmal umschalten."""
        if not abgedeckt:
            self.modus_start = None
            self.modus_gesperrt = False
        elif not self.modus_gesperrt:
            if self.modus_start is None:
                self.modus_start = jetzt
            elif time.ticks_diff(jetzt, self.modus_start) >= T_MODUS:
                self.duell = not self.duell
                self.modus_gesperrt = True
                self.bestaetigung_start = jetzt
                self.bestaetigung_anzahl = 2 if self.duell else 1
                print("Modus:", "Duell" if self.duell else "Einzel")
                return True
        return False

    def fehlstart(self, jetzt, druck, ldr_flanke):
        print("Fehlstart!")
        if self.duell:
            if druck and ldr_flanke:
                print("Unentschieden! Beide haben einen Fehlstart gemacht.")
            else:
                # Taster = Spieler 1, LDR = Spieler 2.
                print("Spieler", 2 if druck else 1, "gewinnt")
        self.wechsel(FEHLSTART, jetzt)

    def ergebnis(self, jetzt, reaktionszeit, druck, ldr_flanke):
        print("Reaktionszeit:", reaktionszeit, "ms")
        if self.duell:
            if druck and ldr_flanke:
                print("Unentschieden! Gleichzeitige Reaktion.")
            else:
                print("Spieler", 1 if druck else 2, "gewinnt")
        self.neue_bestzeit = (self.bestzeit is None
                              or reaktionszeit < self.bestzeit)
        if self.neue_bestzeit:
            self.bestzeit = reaktionszeit
            print("Neue Bestzeit!")
        print("Bestzeit:", self.bestzeit, "ms")
        self.wechsel(ERGEBNIS, jetzt)

    def update(self, jetzt, tasterwert, ldrwert):
        druck = self.letzter_taster == 1 and tasterwert == 0
        abgedeckt = ldrwert < LDR_SCHWELLE
        ldr_flanke = not self.letzter_ldr and abgedeckt
        self.letzter_taster = tasterwert
        self.letzter_ldr = abgedeckt
        # Außerhalb BEREIT kann Freigeben eine spätere Modusgeste neu erlauben.
        if not abgedeckt:
            self.modus_gesperrt = False
        vergangen = time.ticks_diff(jetzt, self.state_start)

        if self.state == BEREIT:
            modus_gewechselt = self.modus_pruefen(jetzt, abgedeckt)
            # Moduswechsel hat bei Gleichzeitigkeit Vorrang vor dem Rundenstart.
            if druck and not modus_gewechselt:
                self.wechsel(WARTEN, jetzt)
        elif self.state == WARTEN:
            # Eingabe im letzten WARTEN-Durchlauf ist noch ein Fehlstart.
            if druck or ldr_flanke:
                self.fehlstart(jetzt, druck, ldr_flanke)
            elif vergangen >= self.wartezeit:
                self.wechsel(SIGNAL, jetzt)
        elif self.state == SIGNAL:
            # Exakt am Timeout ist das Zeitfenster bereits geschlossen.
            if vergangen >= T_TIMEOUT:
                print("Zu langsam!")
                self.wechsel(BEREIT, jetzt)
            elif druck or ldr_flanke:
                if vergangen < T_MIN_REAKTION:
                    self.fehlstart(jetzt, druck, ldr_flanke)
                else:
                    self.ergebnis(jetzt, vergangen, druck, ldr_flanke)
        elif self.state == ERGEBNIS:
            if vergangen >= T_ERGEBNIS:
                self.wechsel(BEREIT, jetzt)
        elif self.state == FEHLSTART:
            if vergangen >= T_FEHLSTART:
                self.wechsel(BEREIT, jetzt)

        return self.ausgaenge(jetzt)

    def melodie_ton(self, vergangen):
        """Notenposition aus Gesamtzeit: keine blockierenden Warteschleifen."""
        ende = 0
        for frequenz, dauer in MELODIE:
            ende += dauer
            if vergangen < ende:
                return frequenz, True
        return 0, False

    def ausgaenge(self, jetzt):
        """Rückgabe: Grün, Gelb, Rot, gewünschte Tonfrequenz."""
        vergangen = time.ticks_diff(jetzt, self.state_start)
        if self.state == BEREIT:
            frequenz = 0
            if self.bestaetigung_start is not None:
                dauer = time.ticks_diff(jetzt, self.bestaetigung_start)
                abschnitt = dauer // T_PIEP
                # Piepton, Pause, ggf. zweiter Piepton. Alles mit T_PIEP.
                if abschnitt < self.bestaetigung_anzahl * 2 - 1:
                    frequenz = F_SIGNAL if abschnitt % 2 == 0 else 0
                else:
                    self.bestaetigung_start = None
            return 1, 0, 0, frequenz
        if self.state == WARTEN:
            return 0, 1, 0, 0
        if self.state == SIGNAL:
            return 0, 0, 1, F_SIGNAL if vergangen < T_PIEP else 0
        if self.state == ERGEBNIS:
            frequenz, melodie_aktiv = (self.melodie_ton(vergangen)
                                       if self.neue_bestzeit else (0, False))
            gruen = (int((vergangen // T_BLINK) % 2 == 0)
                     if melodie_aktiv else 1)
            return gruen, 1, 0, frequenz
        if self.state == FEHLSTART:
            return 0, 0, int((vergangen // T_BLINK) % 2 == 0), F_FEHLER
        return 0, 0, 0, 0


def main():
    global led_gruen, led_gelb, led_rot, button, buzzer, ldr, letzter_ton
    led_gruen = Pin(PIN_LED_GRUEN, Pin.OUT, value=0)
    led_gelb = Pin(PIN_LED_GELB, Pin.OUT, value=0)
    led_rot = Pin(PIN_LED_ROT, Pin.OUT, value=0)
    button = Pin(PIN_BTN, Pin.IN, Pin.PULL_UP)
    buzzer = PWM(Pin(PIN_BUZZER), freq=F_SIGNAL, duty_u16=0)
    letzter_ton = None
    try:
        ldr = ADC(Pin(PIN_LDR))
        ldr.atten(ADC.ATTN_11DB)
        # read() wird für die vorgegebene Schwelle auf 0..4095 normiert.
        ldr.width(ADC.WIDTH_12BIT)
        spiel = Reaktionsspiel(time.ticks_ms(), button.value(), ldr.read())
        led_gruen.value(1)
        ton(0)
        print("Modus: Einzel – bereit")
        while True:
            jetzt = time.ticks_ms()
            gruen, gelb, rot, frequenz = spiel.update(
                jetzt, button.value(), ldr.read()
            )
            led_gruen.value(gruen)
            led_gelb.value(gelb)
            led_rot.value(rot)
            ton(frequenz)
    finally:
        ton(0)
        buzzer.deinit()
        led_gruen.value(0)
        led_gelb.value(0)
        led_rot.value(0)


if __name__ == "__main__":
    main()
