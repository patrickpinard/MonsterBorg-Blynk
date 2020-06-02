#!/usr/bin/env python
# coding: utf-8

# Auteur    : Patrick Pinard
# Date      : 14.5.2020
# Objet     : Télécommander un MonsterBorg avec APP Blynk 
# Source    : MonsterBorgV1.py
# Version   : 1
# Change log:   - V0.8 : modification pour retour en mode Joystick sur Blynk (valeur analogique 0-10)
#               - V0.7 : usage de l'App Blynk en mode binaire avec boutons ON/OFF (0/1)
#               - V0.6 : Usage du Joystick pour gestion analogique de la vitesse moteur et ajusteement des paramètres dynamiques sur onglet"paramètres"
#               - V0.4/V0.5 : alimentation des moteurs et Raspberry Pi 4 très consomateur (5V/3A). Problème avec 10 batteries 1,5V (AAA) car pas suffisant
#                 compléter alimentation par PowerPack USB-C de 5V/3A - 15W pour le Raspberry Pi 4. Plus de problème de coupure de liaison lorsque moteurs en fonction.
#                 Cellularline 10000 fast charge 8x 
#               - V0.3 : ajout boutons slow / fast turn / moteur gauche et droite
#               - V0.2 : Usage de bouton pour avancer/reculer/gauche/droite
#               - V0.1 : fonction de base
# Statut    : fonctionnel

#   Clavier MAC :      
#  {} = "alt/option" + "(" ou ")"
#  [] = "alt/option" + "5" ou "6"
#   ~  = "alt/option" + n    
#   \  = Alt + Maj + / 

# Importation des librairies nécessaires
import sys
import BlynkLib
import time
import ThunderBorg3 as ThunderBorg

# Clé d'accès à Blynk sketch
BLYNK_AUTH = 'votre clé Blynk'

# Paramètres et variables
global vitesse
vitesse = 0.0
CoefficientReductionVitesse = 0.8       # Coefficient de réduction de la vitesse (0.5 = demi vitesse)
CoefficientChangementDirection = 1.5    # Coefficient pour changement de direction rapide
global TB
global ReduireVitesse
ReduireVitesse = False                  # bouton de réduction de la vitesse (PIN Virtual 1)
global DirectionRapide
DirectionRapide =  False                # bouton de changement de direction rapide (PIN Virtual 2)
global direction
direction = 0.0
global STOP
STOP = False                            # bouton d'arrêt d'urgence
global Avancer
Avancer =  False 
global Reculer
Reculer =  False 
global Gauche
Gauche =  False 
global Droite
Droite =  False 
global MoteurGauche
MoteurGauche =  True                   # moteur gauche activé 
global MoteurDroite
MoteurDroite =  True                   # moteur droite activé 
global running                         # running = fonctionnement normal
running = True
interval = 0.1                         # Intervalle d'attente entre deux commandes des moteurs. 
global maxPower

# Puissance des batteries moteurs
voltageIn = 1.2 * 10                   # Voltage des batteries pour le ThunderBorg
voltageOut = 12.0 * 0.95               # Voltage maximum à 95% pour ne pas interrompre le Raspberry Pi (pas possible avec version Pi 4)

print("--------------------------------")
print("    Projet TELSA                ")
print("    Jonathan & Patrick Pinard   ")
print("    version 1.0 / 15 mai 2020   ")
print("    Véhicule télécommandé       ")
print("    MonsterBorg/Raspberyy Pi 4  ")
print("    via APP Blynk Cloud IoT     ")
print("--------------------------------")


# Limite max de la puissance moteur
maxPower = 1

# Initialisation de la carte ThunderBorg
TB = ThunderBorg.ThunderBorg()
TB.Init()
if not TB.foundChip:
    boards = ThunderBorg.ScanForThunderBorg()
    if len(boards) == 0:
        print("Aucune carte ThunderBorg détectée !")
    else:
        print("Carte ThunderBorg à l'adresse %02X :" % (TB.i2cAddress))
        for board in boards:
            print('    %02X (%d)' % (board, board))
        print('Changer adresse I²C dans programme : ')
        print('TB.i2cAddress = 0x%02X' % (boards[0]))
    sys.exit()

# communications failsafe enclenchée
for i in range(5):
    TB.SetCommsFailsafe(True)
    failsafe = TB.GetCommsFailsafe()
    if failsafe:
        break
if not failsafe:
    print('Board %02X pas en mode failsafe!' % (TB.i2cAddress))
    sys.exit()

# Définition des niveaux pour batteries
# Pour 10 batteries AAA de 1,5V, on fixe les limites 
# min : 9,5V, Moyen : 11,5V et Max - 13,5V
global battCurrent, battMax, battMin
battMin = 9.5
battMax = 13.5
TB.SetBatteryMonitoringLimits(battMin, battMax)

# Affichage du niveau min, max et actuel des batteries
battMin, battMax = TB.GetBatteryMonitoringLimits()
battCurrent = TB.GetBatteryReading()
print('Etat des batteries ')
print('    Minimum  (rouge)  :  %02.2f V' % (battMin))
print('    Moyen    (jaune)  :  %02.2f V' % ((battMin + battMax) / 2))
print('    Maximum  (vert)   :  %02.2f V' % (battMax))
print('-------------------------------------')
print('    Voltage actuel    :  %02.2f V' % (battCurrent))
print('-------------------------------------')

# On met les moteurs à l'arrêt tous les moteurs
TB.MotorsOff()

# Connection à Blynk 
print('......Connection à Blynk Cloud en cours, veuillez patienter 2 secondes ......')
blynk = BlynkLib.Blynk(BLYNK_AUTH)
time.sleep(2)
if blynk.connect:
    print("La connexion à blynk est réussie")
else:
    print("Echec de connexion à Blynk Cloud. Contrôlez la connectivité")

# Handler Blynk (appel par interruption sur Virtual Pin)

# Lecture des paramètres  
@blynk.VIRTUAL_WRITE(12)
def ParametreCoeffDirectionRapide_handler(value):
    global CoefficientChangementDirection
    CoefficientChangementDirection = int(value[0])/10
    print('Coefficient de direction rapide : ', CoefficientChangementDirection)

# Lecture des paramètres  
@blynk.VIRTUAL_WRITE(13)
def ParametreCoefficientReductionVitesse_handler(value):
    global CoefficientChangementDirection
    CoefficientReductionVitesse = int(value[0])/10
    print('Coefficient de réduction de vitesse : ', CoefficientReductionVitesse)


# Lecture des paramètres  
@blynk.VIRTUAL_WRITE(5)
def ParametreMaxPower_handler(value):
    global maxPower
    maxPower = int(value[0])/10
    print('Puissance maximale (0-100%): ', int(maxPower*100), " %")

# DirectionRapide 
@blynk.VIRTUAL_WRITE(1)
def DirectionRapide_handler(value):
    global DirectionRapide
    if str(value[0]) == "1":
        DirectionRapide = True
        print('Direction rapide enclenché')
    else:
        DirectionRapide = False
        print('Direction rapide arrêté') 

# ReduireVitesse 
@blynk.VIRTUAL_WRITE(2)
def ReduireVitesse_handler(value):
    global ReduireVitesse
    if str(value[0]) == "1":
        ReduireVitesse = True
        print('Réduction vitesse enclenché')
    else:
        ReduireVitesse = False
        print('Réduction vitesse arrêté') 

# STOP 
@blynk.VIRTUAL_WRITE(3)
def STOP_handler(value):
    global STOP
    global running
    print("Arrêt Urgence : {}".format(value))
    STOP = bool(value)
    if STOP:
        running = False
    else:
        running = True
    
# direction gauche/droite
@blynk.VIRTUAL_WRITE(6) 
def direction_handler(value):
    global direction
    if int(value[0])>0:
        direction = (int(value[0]))/10
        print('Direction droite : ', direction)
    else:
        direction = (int(value[0]))/10
        print('Direction gauche : ', direction)  

# Avancer/Reculer avec Joystock (axe X)
@blynk.VIRTUAL_WRITE(7) 
def AvancerReculer_handler(value):
    global vitesse
    if int(value[0])<=10:
        vitesse = (float(value[0]))/10
        print("Avancer, vitesse : ", vitesse)
    else:
        vitesse = (float(value[0]))/10
        print("Reculer, vitesse : ", vitesse)


# niveau de la batterie
@blynk.VIRTUAL_WRITE(0) 
def Batterie_handler(value):
    global battCurrent, battMin, battMax
    battCurrent = TB.GetBatteryReading()
    blynk.virtual_write(0,battCurrent) 
    print("Niveau de la batterie = ", battCurrent)
    if battCurrent < battMin:
        TB.SetLeds(1, 0, 0)
    if battCurrent > battMax:
        TB.SetLeds(0, 1, 0)
    if battCurrent > battMin and battCurrent < battMax:
        TB.SetLeds(0, 0, 1)

directionfinale = 0.0
vitessefinale = 0.0
vitesse = 0.0
direction = 0.0
VitesseMoteurGauche = 0.0
VitesseMoteurDroite  = 0.0
t = 0

print("MaxPower = ", maxPower)
print("Changement de direction rapide : ", DirectionRapide)
print("Réduction de la vitesse : ", ReduireVitesse)
print("Vitesse : ", vitessefinale)

while running and blynk.connect:
    t = t+1    
    blynk.run()
    if ReduireVitesse:
        vitessefinale = vitesse * CoefficientReductionVitesse * maxPower
    else:
        vitessefinale = vitesse * maxPower

    # Determine la vitesse des moteurs droite et gauche

    VitesseMoteurGauche = vitessefinale
    VitesseMoteurDroite = vitessefinale

    directionfinale = direction * CoefficientChangementDirection
        
    if directionfinale>0:                                                                                                                                                                   
        VitesseMoteurGauche *= 1 - directionfinale *CoefficientReductionVitesse
    else:
        VitesseMoteurDroite *= 1 + directionfinale *CoefficientReductionVitesse
    
 
    TB.SetMotor1(VitesseMoteurDroite)
    TB.SetMotor2(VitesseMoteurGauche)
   

    if t>100:
        battCurrent = TB.GetBatteryReading()
        blynk.virtual_write(0,battCurrent) 
        t=0
        print("Niveau de la batterie = ", battCurrent)
        if battCurrent < battMin:
            TB.SetLeds(1, 0, 0)
        if battCurrent > battMax:
            TB.SetLeds(0, 1, 0)
        if battCurrent > battMin and battCurrent < battMax:
            TB.SetLeds(0, 0, 1)

    # interval de processing
    time.sleep(interval)
        
TB.MotorsOff()
TB.SetCommsFailsafe(False)
TB.SetLedShowBattery(False)
TB.SetLeds(0, 0, 0)
