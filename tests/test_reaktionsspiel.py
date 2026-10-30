"""CPython-Tests: python3 -m unittest discover -s tests -v"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

PERIODE = 1 << 30

def ticks_diff(neu, alt):
    return (neu - alt + PERIODE // 2) % PERIODE - PERIODE // 2

spec = importlib.util.spec_from_file_location(
    "reaktionsspiel", Path(__file__).resolve().parents[1] / "main.py"
)
spiel = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"machine": types.SimpleNamespace(Pin=None, ADC=None, PWM=None)}):
    spec.loader.exec_module(spiel)
spiel.time = types.SimpleNamespace(ticks_diff=ticks_diff)
spiel.random = types.SimpleNamespace(randint=lambda a, b: a)

HELL, DUNKEL = 3000, 500


class SpielTest(unittest.TestCase):
    def setUp(self):
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)
        self.g = spiel.Reaktionsspiel(0, 1, HELL)

    def signal(self, duell=False):
        self.g.duell = duell
        self.g.update(0, 0, HELL)
        self.g.update(1, 1, HELL)
        self.g.update(spiel.T_WARTEN_MIN, 1, HELL)
        self.assertEqual(self.g.state, spiel.SIGNAL)
        return spiel.T_WARTEN_MIN

    def test_start_und_neue_zufallszeit_pro_runde(self):
        self.assertEqual(self.g.ausgaenge(0), (1, 0, 0, 0))
        werte = iter([spiel.T_WARTEN_MIN, spiel.T_WARTEN_MAX])
        aufrufe = []
        def zufall(a, b):
            aufrufe.append((a, b))
            return next(werte)
        with patch.object(spiel.random, 'randint', zufall):
            self.g.update(0, 0, HELL)
            self.assertEqual(self.g.wartezeit, spiel.T_WARTEN_MIN)
            self.g.update(1, 1, HELL)
            self.g.wechsel(spiel.BEREIT, 2)
            self.g.update(3, 0, HELL)
            self.assertEqual(self.g.wartezeit, spiel.T_WARTEN_MAX)
        self.assertEqual(aufrufe, [(spiel.T_WARTEN_MIN, spiel.T_WARTEN_MAX)] * 2)

    def test_halten_startet_nicht_erneut(self):
        self.g.update(0, 0, HELL)
        self.g.update(100, 0, HELL)
        self.assertEqual(self.g.state, spiel.WARTEN)
        self.g.update(spiel.T_WARTEN_MIN, 0, HELL)
        self.g.update(spiel.T_WARTEN_MIN + 300, 0, HELL)
        self.assertEqual(self.g.state, spiel.SIGNAL)

    def test_wartegrenze_und_piepende(self):
        self.g.update(0, 0, HELL)
        self.assertEqual(self.g.update(spiel.T_WARTEN_MIN-1, 1, HELL), (0, 1, 0, 0))
        self.assertEqual(self.g.update(spiel.T_WARTEN_MIN, 1, HELL), (0, 0, 1, spiel.F_SIGNAL))
        self.assertEqual(self.g.update(spiel.T_WARTEN_MIN+spiel.T_PIEP, 1, HELL), (0, 0, 1, 0))

    def test_fehlstart_warten_blinken_und_ende(self):
        self.g.update(0, 0, HELL)
        self.g.update(1, 1, HELL)
        self.assertEqual(self.g.update(10, 0, HELL), (0, 0, 1, spiel.F_FEHLER))
        self.assertIn('Fehlstart!', self.output.getvalue())
        self.assertEqual(self.g.update(10+spiel.T_BLINK, 0, HELL), (0, 0, 0, spiel.F_FEHLER))
        self.assertEqual(self.g.update(10+spiel.T_FEHLSTART, 0, HELL), (1, 0, 0, 0))
        self.assertIsNone(self.g.bestzeit)

    def test_zu_schnell_und_minimal_gueltig(self):
        t = self.signal()
        self.g.update(t+spiel.T_MIN_REAKTION-1, 0, HELL)
        self.assertEqual(self.g.state, spiel.FEHLSTART)
        self.assertIsNone(self.g.bestzeit)
        self.g = spiel.Reaktionsspiel(0, 1, HELL)
        t = self.signal()
        self.g.update(t+spiel.T_MIN_REAKTION, 0, HELL)
        self.assertEqual(self.g.state, spiel.ERGEBNIS)
        self.assertEqual(self.g.bestzeit, spiel.T_MIN_REAKTION)

    def test_reaktion_waehrend_startpiep(self):
        t = self.signal()
        aus = self.g.update(t+spiel.T_MIN_REAKTION, 0, HELL)
        self.assertEqual(aus[3], spiel.MELODIE[0][0])
        self.assertIn('Reaktionszeit: 100 ms', self.output.getvalue())

    def test_timeout_grenze_und_keine_bestzeit(self):
        t = self.signal()
        self.g.update(t+spiel.T_TIMEOUT, 0, HELL)
        self.assertEqual(self.g.state, spiel.BEREIT)
        self.assertIn('Zu langsam!', self.output.getvalue())
        self.assertIsNone(self.g.bestzeit)
        self.g.update(t+spiel.T_TIMEOUT+1, 0, HELL)
        self.assertEqual(self.g.state, spiel.BEREIT)

    def test_ldr_startet_nicht_und_bereits_abgedeckt_zaehlt_nicht(self):
        self.g.update(0, 1, DUNKEL)
        self.assertEqual(self.g.state, spiel.BEREIT)
        self.g.update(1, 0, DUNKEL)
        self.g.update(2, 1, DUNKEL)
        self.g.update(1+spiel.T_WARTEN_MIN, 1, DUNKEL)
        self.assertEqual(self.g.state, spiel.SIGNAL)
        self.g.update(2102, 1, DUNKEL)
        self.assertEqual(self.g.state, spiel.SIGNAL)
        self.g.update(2103, 1, HELL)
        self.g.update(2200, 1, DUNKEL)
        self.assertEqual(self.g.state, spiel.ERGEBNIS)

    def test_ldr_fehlstart_in_warten(self):
        self.g.update(0, 0, HELL)
        self.g.update(1, 1, DUNKEL)
        self.assertEqual(self.g.state, spiel.FEHLSTART)

    def test_melodie_notengrenzen_blinken_und_ergebnisdauer(self):
        t = self.signal()
        start = t+250
        self.g.update(start, 0, HELL)
        grenze = 0
        for hz, dauer in spiel.MELODIE:
            self.assertEqual(self.g.ausgaenge(start+grenze)[3], hz)
            self.assertEqual(self.g.ausgaenge(start+grenze+dauer-1)[3], hz)
            grenze += dauer
        self.assertEqual(self.g.ausgaenge(start+spiel.T_BLINK)[:2], (0, 1))
        self.assertEqual(self.g.ausgaenge(start+grenze), (1, 1, 0, 0))
        self.g.update(start+1000, 1, HELL)
        self.g.update(start+1001, 0, HELL)  # ignoriert
        self.assertEqual(self.g.state, spiel.ERGEBNIS)
        self.g.update(start+spiel.T_ERGEBNIS-1, 0, HELL)
        self.assertEqual(self.g.state, spiel.ERGEBNIS)
        self.assertEqual(self.g.update(start+spiel.T_ERGEBNIS, 0, HELL), (1, 0, 0, 0))

    def test_bestzeit_nur_streng_besser(self):
        for zeit, erwartet, neu in [(250,250,True), (300,250,False), (250,250,False), (200,200,True)]:
            self.g.ergebnis(1000, zeit, True, False)
            self.assertEqual(self.g.bestzeit, erwartet)
            self.assertEqual(self.g.neue_bestzeit, neu)
            if not neu:
                self.assertEqual(self.g.ausgaenge(1000), (1, 1, 0, 0))

    def test_modus_durchgehend_einmal_und_pieps(self):
        self.g.update(0, 1, DUNKEL)
        self.g.update(spiel.T_MODUS-1, 1, DUNKEL)
        self.assertFalse(self.g.duell)
        t = spiel.T_MODUS
        self.assertEqual(self.g.update(t, 1, DUNKEL)[3], spiel.F_SIGNAL)
        self.assertTrue(self.g.duell)
        self.assertEqual(self.g.update(t+spiel.T_PIEP, 1, DUNKEL)[3], 0)
        self.assertEqual(self.g.update(t+2*spiel.T_PIEP, 1, DUNKEL)[3], spiel.F_SIGNAL)
        self.assertEqual(self.g.update(t+3*spiel.T_PIEP, 1, DUNKEL)[3], 0)
        self.g.update(4*spiel.T_MODUS, 1, DUNKEL)
        self.assertTrue(self.g.duell)
        self.g.update(9000, 1, HELL)
        self.g.update(9001, 1, DUNKEL)
        self.g.update(9001+spiel.T_MODUS, 1, DUNKEL)
        self.assertFalse(self.g.duell)
        self.assertEqual(self.g.ausgaenge(9001+spiel.T_MODUS+spiel.T_PIEP)[3], 0)

    def test_modus_kurze_und_unterbrochene_geste(self):
        self.g.update(0, 1, DUNKEL)
        self.g.update(1000, 1, HELL)
        self.g.update(1001, 1, DUNKEL)
        self.g.update(2000, 1, DUNKEL)
        self.assertFalse(self.g.duell)
        self.g.update(3001, 1, DUNKEL)
        self.assertTrue(self.g.duell)

    def test_modus_zaehlt_nicht_ausserhalb_bereit(self):
        self.g = spiel.Reaktionsspiel(0, 1, DUNKEL)
        self.g.update(0, 0, DUNKEL)
        self.g.update(2000, 1, DUNKEL)
        self.g.update(4000, 1, DUNKEL)  # Timeout → BEREIT
        self.g.update(4001, 1, DUNKEL)  # jetzt beginnt erst die Modusgeste
        self.g.update(6000, 1, DUNKEL)
        self.assertFalse(self.g.duell)
        self.g.update(6001, 1, DUNKEL)
        self.assertTrue(self.g.duell)

    def test_duell_beide_gewinner_und_unentschieden(self):
        for button, ldr, meldung in [(0,HELL,'Spieler 1 gewinnt'),
                                     (1,DUNKEL,'Spieler 2 gewinnt'),
                                     (0,DUNKEL,'Unentschieden!')]:
            self.g = spiel.Reaktionsspiel(0, 1, HELL)
            t = self.signal(duell=True)
            self.output.truncate(0); self.output.seek(0)
            self.g.update(t+250, button, ldr)
            self.assertIn(meldung, self.output.getvalue())
            self.assertEqual(self.g.state, spiel.ERGEBNIS)

    def test_duell_fehlstart_anderer_gewinnt(self):
        for signal_phase in [False, True]:
            for button, ldr, gewinner in [(0,HELL,'Spieler 2 gewinnt'),
                                          (1,DUNKEL,'Spieler 1 gewinnt'),
                                          (0,DUNKEL,'Unentschieden!')]:
                self.g = spiel.Reaktionsspiel(0, 1, HELL)
                if signal_phase:
                    t = self.signal(duell=True)
                else:
                    self.g.duell = True
                    self.g.update(0, 0, HELL)
                    self.g.update(1, 1, HELL)
                    t = 0
                self.output.truncate(0); self.output.seek(0)
                self.g.update(t+50, button, ldr)
                self.assertIn(gewinner, self.output.getvalue())
                self.assertEqual(self.g.state, spiel.FEHLSTART)

    def test_ueberlauf(self):
        start = PERIODE-1000
        self.g = spiel.Reaktionsspiel(start, 1, HELL)
        self.g.update(start, 0, HELL)
        self.g.update(start+1, 1, HELL)
        self.g.update((start+spiel.T_WARTEN_MIN) % PERIODE, 1, HELL)
        self.g.update((start+spiel.T_WARTEN_MIN+250) % PERIODE, 0, HELL)
        self.assertEqual(self.g.bestzeit, 250)

    def test_hauptschleife_mit_simulierter_hardware(self):
        class Ende(Exception):
            pass
        pins = {}
        jetzt = [0]
        zeiten = iter([0, 10, 20, 2010, 2260, 2410, 5260])
        class Pin:
            OUT, IN, PULL_UP = 1, 0, 2
            def __init__(self, nr, modus=None, pull=None, value=0):
                self.nr, self.wert = nr, value
                self.verlauf = []
                pins[nr] = self
            def value(self, wert=None):
                if wert is not None:
                    self.wert = wert
                    self.verlauf.append((jetzt[0], wert))
                if self.nr == spiel.PIN_BTN:
                    return 0 if jetzt[0] in (10, 2260) else 1
                return self.wert
        class ADC:
            ATTN_11DB, WIDTH_12BIT = 3, 12
            def __init__(self, pin): self.pin = pin
            def atten(self, wert): self.attenuation = wert
            def width(self, wert): self.bits = wert
            def read(self): return HELL
        class PWM:
            def __init__(self, pin, freq, duty_u16):
                self.aus = duty_u16 == 0
                self.deinitialized = False
            def freq(self, wert): self.frequenz = wert
            def duty_u16(self, wert): self.aus = wert == 0
            def deinit(self): self.deinitialized = True
        def tick():
            try:
                jetzt[0] = next(zeiten)
            except StopIteration:
                raise Ende()
            return jetzt[0]
        with patch.object(spiel, 'Pin', Pin), patch.object(spiel, 'ADC', ADC), \
             patch.object(spiel, 'PWM', PWM), \
             patch.object(spiel, 'time', types.SimpleNamespace(ticks_ms=tick, ticks_diff=ticks_diff)):
            with self.assertRaises(Ende):
                spiel.main()
        self.assertEqual(spiel.ldr.attenuation, ADC.ATTN_11DB)
        self.assertEqual(spiel.ldr.bits, ADC.WIDTH_12BIT)
        self.assertIn((2010, 1), pins[spiel.PIN_LED_ROT].verlauf)
        self.assertIn('Reaktionszeit: 250 ms', self.output.getvalue())
        self.assertTrue(spiel.buzzer.aus)
        self.assertTrue(spiel.buzzer.deinitialized)
        for nr in (spiel.PIN_LED_GRUEN, spiel.PIN_LED_GELB, spiel.PIN_LED_ROT):
            self.assertEqual(pins[nr].wert, 0)

    def test_ton_nur_bei_aenderung(self):
        class Buzzer:
            def __init__(self): self.calls = []
            def freq(self, f): self.calls.append(('freq', f))
            def duty_u16(self, d): self.calls.append(('duty', d))
        fake = Buzzer()
        with patch.object(spiel, 'buzzer', fake), patch.object(spiel, 'letzter_ton', None):
            for hz in [0, 0, spiel.F_SIGNAL, spiel.F_SIGNAL, 0, 0]:
                spiel.ton(hz)
        self.assertEqual(fake.calls, [('duty',0), ('freq',spiel.F_SIGNAL),
                                      ('duty',32768), ('duty',0)])


if __name__ == '__main__':
    unittest.main()
