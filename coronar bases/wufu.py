from wpautil import get_network_credentials as gnc
import network, time
ssid = "Telecentro-cb2b"    #Nombre del SSID que está guardado previamente aunque tenga contraseña.pywpa -i <INTERFACE> scan | grep $SSID  --nocolor y xargs wpautil get_credentials
cipher = gnc(ssid)   // Ejecuta este comando para obtener la información de credenciales SSID actualmente guardada.pywpa -i <INTERFACE> scan | grep $SSID  --nocolor y xargs wpautil get_credentials
