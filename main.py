from machine import Pin, ADC, PWM
import time
import random

# ---- Zeiten (ms) ----
T_WARTEN_MIN   = 2000   # Teil A: kürzeste zufällige Wartezeit
T_WARTEN_MAX   = 5000   # Teil A: längste zufällige Wartezeit
T_PIEP         = 150    # Teil A: Länge des Startsignal-Pieps
T_TIMEOUT      = 2000   # Teil A: so lange hat man Zeit zu reagieren
T_ERGEBNIS     = 3000   # Teil A: Anzeigedauer des Ergebnisses
T_FEHLSTART    = 1500   # Teil B: Dauer der Fehlstart-Anzeige
T_BLINK        = 200    # Teil B/D: halbe Blinkperiode
T_MIN_REAKTION = 100    # Teil B: schneller = geraten = Fehlstart
T_MODUS        = 2000   # Teil E: so lange LDR abdecken für Moduswechsel

# ---- Töne (Hz) ----
F_SIGNAL = 2000                                                # Teil A: Startsignal
F_FEHLER = 200                                                 # Teil B: Fehlstart
MELODIE  = [(523, 150), (659, 150), (784, 150), (1047, 400)]   # Teil D: (Frequenz in Hz, Dauer in ms)

# ---- LDR ----
LDR_SCHWELLE = 1500     # TODO (ab Teil C): eigenen Wert messen – darunter gilt der LDR als abgedeckt

# ---- Pins (an eigenes Board anpassen) ----
PIN_LED_GRUEN = 0   # TODO
PIN_LED_GELB  = 0   # TODO
PIN_LED_ROT   = 0   # TODO
PIN_BTN       = 0   # TODO
PIN_BUZZER    = 0   # TODO
PIN_LDR       = 0   # TODO (ab Teil C) – ADC1-Pin verwenden (32–39)

led_gruen = None    # TODO
led_gelb  = None    # TODO
led_rot   = None    # TODO
button    = None    # TODO
buzzer    = None    # TODO (PWM)
ldr       = None    # TODO (ab Teil C, ADC mit ATTN_11DB)

# ---- State Machine - Zustände ----
BEREIT    = 0
WARTEN    = 1
SIGNAL    = 2
ERGEBNIS  = 3
FEHLSTART = 4   # Teil B
state = BEREIT


def ton(freq):
    """Buzzer: Dauerton mit freq Hz, ton(0) = aus."""
    if freq:
        buzzer.freq(freq)
        buzzer.duty_u16(32768)
    else:
        buzzer.duty_u16(0)


# ---- Anfangswerte ----
# TODO


while True:
    # TODO: Eingänge lesen

    # TODO: Zustandsmaschine (Übergänge)

    # TODO: Ausgänge setzen (LEDs, Buzzer)
    pass
