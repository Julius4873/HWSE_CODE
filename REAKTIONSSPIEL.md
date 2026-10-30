# Reaktionsspiel – main.py

Implementiert die Teile A–E der Vorlage: Zustandsmaschine, zufällige Wartezeit,
Tasterflanken, Fehlstarts, LDR-Flanken, Bestzeit, nicht-blockierende Melodie mit
Blinken und Duell-Modus. Alle vorgegebenen Zeit- und Tonkonstanten bleiben erhalten.
Die Bestzeit gilt gemeinsam für gültige Reaktionen beider Eingabearten/Modi und
bleibt bis zum Neustart im RAM erhalten. Gleich gute Zeiten sind keine neue Bestzeit.

## Hardware vorbereiten

Die Vorlage enthielt ausschließlich Pin-Platzhalter. `main.py` enthält deshalb
folgende **ESP32-Beispielbelegung**, keine verifizierte Verdrahtung:

| Signal | GPIO |
| --- | ---: |
| Grün | 25 |
| Gelb | 27 |
| Rot | 12 |
| Taster nach GND, interner Pull-up | 4 |
| Passiver Buzzer, PWM | 26 |
| LDR-Spannungsteiler, ADC1 | 34 |

Pins an das tatsächliche Board anpassen. GPIO12 ist beim klassischen ESP32 ein
Strapping-Pin: Der LED-Aufbau darf seinen Startpegel nicht unerwünscht verändern;
bei Startproblemen einen geeigneten freien Ausgang verwenden und die Konstante
ändern. GPIO34 ist nur Eingang und hat keinen internen Pull-Widerstand.
Jede LED braucht einen passenden Vorwiderstand. Gemeinsame Masse verwenden und
zulässige GPIO-Ströme beachten; ein Buzzer mit höherem Strombedarf braucht eine
geeignete Treiberstufe. Die Belegung gilt nicht für einen Raspberry Pi Pico.

Der LDR-Spannungsteiler muss beim Abdecken kleinere ADC-Werte liefern.
Beispiel: 3,3 V → LDR → ADC-Knoten → Festwiderstand → GND.
Den ADC-Eingang innerhalb des zulässigen Spannungsbereichs halten;
`ATTN_11DB` macht einen GPIO nicht 5-V-tolerant.

Vor dem Spiel in Thonny den Sensor prüfen:

```python
from machine import ADC, Pin
ldr = ADC(Pin(34))  # an PIN_LDR anpassen
ldr.atten(ADC.ATTN_11DB)
ldr.width(ADC.WIDTH_12BIT)
print(ldr.read())  # mehrfach bei Licht und mit Hand darüber ausführen
```

`LDR_SCHWELLE` zwischen den gemessenen Hell-/Dunkelwerten einstellen. 1500 aus
der Vorlage ist nur ein Startwert. Werte knapp an der Schwelle können rauschen;
die Hand muss einen klaren Pegelwechsel erzeugen. Der Taster wird flankengesteuert
ausgewertet; eine zusätzliche mechanische Entprellung ist nicht implementiert.
Bei prellenden Kontakten Hardwareentprellung vorsehen oder gezielt ergänzen und
die Wirkung auf die Reaktionszeit erneut prüfen.

## Auf dem Board starten

Eine aktuelle ESP32-MicroPython-Version mit `PWM.duty_u16()`, `ADC.width()` und
`ADC.read()` verwenden. Die geprüfte `main.py` in Thonny auf das Board kopieren.
Die Datei startet automatisch; Strg+C beendet die Schleife und schaltet LEDs und
Buzzer aus. Die Testdateien werden nicht auf das Board benötigt.

- BEREIT: Grün. Nur ein neuer Tastendruck startet die Runde.
- WARTEN: Gelb. Neuer Tastendruck oder neue LDR-Abdeckung ist ein Fehlstart.
- SIGNAL: Rot, kurzer Startpiep. Die erste gültige Reaktion ergibt die Messzeit.
- ERGEBNIS: Grün und Gelb; bei neuer Bestzeit Melodie und Grün-Blinken.
- FEHLSTART: Rot blinkt und Fehlerton, danach wieder BEREIT.

## Duell und Grenzfälle

- In BEREIT den LDR für `T_MODUS` durchgehend abdecken: Duell (zwei Pieps)
  bzw. Einzel (ein Piep). Die Pause zwischen Pieps dauert ebenfalls `T_PIEP`.
- Eine lange Abdeckung schaltet nur einmal um. Vor dem nächsten Umschalten
  aufdecken. Die Haltezeit wird nur in BEREIT gesammelt.
- Im Duell startet weiterhin der Taster die Runde. Taster = Spieler 1,
  LDR = Spieler 2. Einen beim Start gehaltenen Taster vorher loslassen.
- Beim Fehlstart gewinnt der andere Spieler. Zwei Eingaben im selben
  Schleifendurchlauf zählen als Unentschieden, auch bei doppeltem Fehlstart.
  Das Polling kann deren tatsächliche Reihenfolge dann nicht unterscheiden.
- Bei gleichzeitigem Moduswechsel und Startdruck hat der Moduswechsel Vorrang.
  Ein späterer Start bricht eventuell noch laufende Bestätigungspieps ab.
- Eine Eingabe im letzten WARTEN-Durchlauf zählt noch als Fehlstart.
  In SIGNAL sind Zeiten ab `T_MIN_REAKTION` und unter `T_TIMEOUT` gültig.
  Genau bei `T_TIMEOUT` wird „Zu langsam!“ ausgegeben.
- Eingaben in ERGEBNIS/FEHLSTART werden beobachtet, aber ignoriert. Gehaltene
  Eingaben werden nach der Rückkehr nicht zu einem neuen Ereignis.
- Die Melodie läuft unabhängig von den Eingängen; ERGEBNIS endet nach
  `T_ERGEBNIS`, unabhängig von der Melodie. Zeitgrenzen werden beim ersten
  Schleifendurchlauf ab dem jeweiligen Termin umgesetzt.

## Prüfung

Am Computer aus dem Repository-Ordner:

```sh
python3 -m unittest discover -s tests -v
```

Die Tests simulieren Eingaben, PWM, ADC und den Tick-Überlauf. Sie ersetzen keinen
Board-Test. Auf echter Hardware noch prüfen: Pins, ADC-Kalibrierung, saubere
Taster-/LDR-Flanken, hörbare Töne, Melodie, Modusbestätigung, gehaltene Eingaben,
Fehlstarts beider Spieler und den vollständigen Ablauf.
