from machine import Pin
import time

# ---- Zeiten (ms) ----
T_GELB           = 1000   # Auto Gelb
T_ROT            = 1000   # alle Rot (Räumzeit)
T_FUSS           = 3000   # Teil A: Fußgänger Grün (entfällt ab Teil B)
T_ROTGELB        = 1000   # Auto Rot-Gelb
T_BLINK          = 500    # halbe Blinkperiode
T_MIN_GRUEN_AUTO = 4000   # Teil D
T_MIN_GRUEN_FUSS = 4000   # Teil D
T_GELB_BLINK     = 1000   # Teil E
T_UNGEREGELT     = 2000   # Teil E
T_ENTPRELLZEIT   = 30     # Entprellzeit

# ---- Pins (an eigenes Board anpassen) ----
PIN_AUTO_R = Pin(12, Pin.OUT, value=0)
PIN_AUTO_Y = Pin(27, Pin.OUT, value=0)
PIN_AUTO_G = Pin(25, Pin.OUT, value=0)
PIN_FUSS_R = Pin(18, Pin.OUT, value=0)
PIN_FUSS_G = Pin(21, Pin.OUT, value=0)
PIN_BTN    = Pin(4, Pin.IN, Pin.PULL_UP)
PIN_LICHT  = Pin(34, Pin.IN)
PIN_WARTEN = Pin(32, Pin.OUT, value=0)
PIN_BTN_2  = Pin(5, Pin.IN, Pin.PULL_UP)

auto_r = PIN_AUTO_R
auto_y = PIN_AUTO_Y
auto_g = PIN_AUTO_G
fuss_r = PIN_FUSS_R
fuss_g = PIN_FUSS_G

warten = PIN_WARTEN

button = PIN_BTN
barrier = PIN_LICHT
button_ungeregelt = PIN_BTN_2

# ---- State Machine - Zustände ----
AUTO_GRUEN   = 0
AUTO_GELB    = 1
ALLE_ROT_1   = 2
FUSS_GRUEN   = 3
ALLE_ROT_2   = 4
AUTO_ROTGELB = 5
UNGEREGELT   = 6    # Teil E
state = AUTO_GRUEN
zustand_start = time.ticks_ms()

anforderung = False

blink_start = zustand_start
blink_an = True

barrier_Aktiv = None

# BUTTON 1
roh1 = button.value()
stabil1 = roh1
zeit1 = zustand_start

# Button 2
roh1 = button_ungeregelt.value()
stabil1 = roh1
zeit1 = zustand_start

# BUTTON Entprellen

def pruefe_taster(pin, jetzt, alt, stabil, start):

    neu = pin.value()
    tastendruck = False

    # Rohwert hat sich geaendert
    if neu != alt:
        alt = neu
        start = jetzt

    # Signal lange genug stabil?
    if (neu != stabil and
        time.ticks_diff(jetzt, start) >= T_ENTPRELLZEIT):

        stabil = neu

        # Fallende Flanke bei Pull-up
        if stabil == 0:
            tastendruck = True

    return alt, stabil, start, tastendruck


def ausgaenge_setzen(zustand, blink_an, anforderung):
    
    if state == AUTO_GRUEN:
        werte = (0, 0, 1, 1, 0, 0)
        
    elif state == AUTO_GELB:
        werte = (0, 1, 0, 1, 0, int(blink_an))
        
    elif state == ALLE_ROT_1:
        werte = (1, 0, 0, 0, 1, int(blink_an))
        
    elif state == FUSS_GRUEN:
        werte = (1, 0, 0, 0, 1, 0)
        
    elif state == ALLE_ROT_2:
        werte = (1, 0, 0, 0, 1, 0)
    
    elif state == AUTO_ROTGELB:
        werte = (1, 1, 0, 0, 1, 0)
        
 
        
    else:
        # Unbekannter Zustand
        werte = (1, 0, 0, 1, 0, 0)
        
    auto_r.value(werte[0]) 
    auto_y.value(werte[1]) 
    auto_g.value(werte[2]) 
    fuss_r.value(werte[3]) 
    fuss_g.value(werte[4]) 

    warten.value(werte[5])
    
ausgaenge_setzen(state, blink_an, anforderung)


while True:
    jetzt = time.ticks_ms()

    # BUTTON 1 

    roh1, stabil1, zeit1, druck = pruefe_taster(button, jetzt, roh1, stabil1, zeit1)
    

    
    
    
    
    if state == AUTO_GRUEN:
        if druck == True:
           anforderung = True
           
           
    if state == AUTO_GRUEN:
        
        if anforderung == True and time.ticks_diff(jetzt, zustand_start) >= T_MIN_GRUEN_AUTO:
            anforderung = False
            state = AUTO_GELB
            zustand_start = jetzt
            
            
    elif state == AUTO_GELB:
        
        if time.ticks_diff(jetzt, zustand_start) >= T_GELB:
            
            state = ALLE_ROT_1
            zustand_start = jetzt
            
        elif time.ticks_diff(jetzt, blink_start) >= T_BLINK:

            blink_an = not blink_an
            blink_start = jetzt
            
    elif state == ALLE_ROT_1:
        
        if time.ticks_diff(jetzt, zustand_start) >= T_ROT :
            
            state = FUSS_GRUEN
            zustand_start = jetzt
            
        elif time.ticks_diff(jetzt, blink_start) >= T_BLINK:

            blink_an = not blink_an
            blink_start = jetzt
            
    elif state == FUSS_GRUEN:
        if barrier.value() == 1 :
            barrier_Aktiv = True    
        if barrier_Aktiv == True and time.ticks_diff(jetzt, zustand_start) >=  T_MIN_GRUEN_FUSS  :
            
            state = ALLE_ROT_2
            zustand_start = jetzt
            
    elif state == ALLE_ROT_2:
        
        if time.ticks_diff(jetzt, zustand_start) >= T_ROT  :
            
            state = AUTO_ROTGELB
            zustand_start = jetzt
            
    elif state == AUTO_ROTGELB:
        if time.ticks_diff(jetzt, zustand_start) >= T_ROTGELB  :
            state = AUTO_GRUEN
            zustand_start = jetzt
    
    ausgaenge_setzen(state, blink_an, anforderung)
    
   
   
   
   
   
   
   
   