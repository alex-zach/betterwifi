#
# Alexander Zach
# a.zach@atria.or.at
#
# This script is a better version of wifi_configurator.py
#

import os, time, hashlib

# reads /etc/betterwifi/networks.conf
# returns an array of tuples (ssid, passphrase)
def knownNetworks():
    try:
        f = open('/etc/betterwifi/networks.conf')
        lines = f.readlines()
        f.close()
        networks = []
        for line in lines:
            if line.startswith('#'):
                continue
            split = line.strip().split(':')
            if len(split) == 2:
                networks.append(tuple(split))
        return networks
    except:
        return []

# scan all networks
# returns an array of tuples (bssid, frequency, signal level, flags, ssid)
def scanNetworks(interface='wlan0'):
    os.system('wpa_cli -i %s scan > /dev/null 2>&1' % interface)
    time.sleep(0.5)
    f = os.popen('wpa_cli -i %s scan_results' % interface)
    lines = f.readlines()
    networks = []
    for line in lines:
        split = line.strip().split('\t')
        if len(split) == 5:
            split[1] = int(split[1])
            split[2] = int(split[2])
            networks.append(tuple(split))
    return networks

# read configured networks
# returns an arry of tuples (nid, ssid, bssid, flags)
def configuredNetworks(interface='wlan0'):
    f = os.popen('wpa_cli -i %s list_networks' % interface)
    lines = f.readlines()
    networks = []
    for line in lines:
        split = line.strip().split('\t')
        if len(split) == 4:
            split[0] = int(split[0])
            networks.append(tuple(split))
    return networks

# read the wpa_state 
def networkState(interface='wlan0'):
    f = os.popen('wpa_cli -i %s status' % interface)
    lines = f.readlines()
    networks = []
    for line in lines:
        split = line.strip().split('=')
        if len(split) == 2 and split[0] == 'wpa_state':
            return split[1]
    return 'UNKNOWN'

# adds a new network
def addNetwork(ssid, passphrase, interface='wlan0'):
    f = os.popen('wpa_cli -i %s add_network' % interface)
    nid = int(f.read().strip())
    os.system('wpa_cli -i %s set_network %d ssid \'"%s"\' > /dev/null 2>&1' % (interface, nid, ssid))
    os.system('wpa_cli -i %s set_network %d psk \'"%s"\' > /dev/null 2>&1' % (interface, nid, passphrase))
    return nid

# connects to an network
def connectNetwork(ssid, passphrase, interface='wlan0'):
    existing_networks = configuredNetworks(interface)
    nid = -1
    for n in existing_networks:
        if n[1] == ssid:
            nid = n[0]
            break
    if nid == -1:
        nid = addNetwork(ssid, passphrase, interface)
    else:
        os.system('wpa_cli -i %s set_network %d psk \'"%s"\' > /dev/null 2>&1' % (interface, nid, passphrase))
    os.system('wpa_cli -i %s select_network %d > /dev/null 2>&1' % (interface, nid))
    time.sleep(5)
    return networkState(interface) == 'COMPLETED'

# starts the access point
def startAP(ssid, passphrase, interface='wlan0'):
    channels = {2412:1, 2417:2, 2422:3, 2427:4, 2432:5, 2437:6, 2442:7, 2447:8, 2452:9, 2457:10, 2462:11, 2467:12, 2472:13}
    channel_count = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    
    networks = scanNetworks(interface)
    
    for network in networks:
        channel_count[channels[network[1]]] += 1
    
    channel = 6
    channel_list = [1, 11, 3, 9]
    
    for c in channel_list:
        if channel_count[channel] > channel_count[c]:
            channel = c
            
    os.system('rm /etc/betterwifi/hostapd_wallaby.conf > /dev/null 2>&1')
    
    f = open('/etc/betterwifi/hostapd_wallaby.conf', 'w')
    f.write(('interface=wlan0\n' +
            'ssid=%s\n' + 
            'channel=%d\n' +
            'wpa=3\n' +
            'wpa_passphrase=%s\n') % (ssid, channel, passphrase))
    f.close()
    
    os.system('ifconfig wlan0 192.168.125.1')
    time.sleep(1)
    os.system('wpa_cli ter')
    time.sleep(1)
    os.system('hostapd /etc/betterwifi/hostapd_wallaby.conf &')
    time.sleep(5)
    os.system('/usr/sbin/udhcpd /etc/udhcpd.conf')
            

knetworks = knownNetworks()
anetworks = scanNetworks()

cnetworks = []

for nw in knetworks:
    found = False
    for snw in anetworks:
        if nw[0] == snw[4]:
            found = True
            break
    if found:
        cnetworks.append(nw)

print(cnetworks)
for nw in cnetworks:
    if connectNetwork(nw[0], nw[1]):
        break
else:
    f = os.popen('wallaby_get_id.sh')
    ssid = f.read()
    passphrase=hashlib.sha256(ssid).hexdigest()[0:6]+'00'
    
    try:
        f = open('/etc/betterwifi/ap.conf')
        lines = f.readlines()
        f.close()
    
        for line in lines:
            split = line.strip().split('=')
            if len(split) == 2:
                if split[0] == 'ssid':
                    ssid = split[1]
                elif split[0] == 'passphrase':
                    passphrase = split[1]
    except:
        pass

    startAP(ssid, passphrase)
