# -*- coding: utf-8 -*-
"""
Fabrique l'archive Nexus "Samurai Warriors 2 - HD Textures".

A placer dans un meme dossier (par ex. SW2_atelier\\remaster\\mod_hd) :
  creer_mod_hd.py, INSTALL.bat, UNINSTALL.bat, readme.txt,
  files\\SW2HD.asi, files\\SW2HD.ini

Prend les textures dans le dossier Textures_HD du jeu et le chargeur ASI (dinput8.dll)
a cote de sw2.exe. Ne modifie rien dans le jeu.

Usage :
  python creer_mod_hd.py --version 1.0
"""
import argparse
import os
import struct
import sys
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
JEU = os.environ.get('SW2_JEU', r'C:\Games\KOEI\SAMURAI WARRIORS 2')
NOM = 'SW2_HD_Textures'
FICHIERS = ['INSTALL.bat', 'UNINSTALL.bat', 'readme.txt', 'files/SW2HD.asi', 'files/SW2HD.ini']


def lire_index(p):
    d = open(p, 'rb').read()
    if d[:4] != b'SW2I': sys.exit('[ERREUR] index.bin inattendu')
    n = struct.unpack_from('<I', d, 4)[0]
    return [struct.unpack_from('<I', d, 8 + 16 * i)[0] for i in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', default='1.0')
    a = ap.parse_args()

    for f in FICHIERS:
        if not os.path.isfile(os.path.join(ICI, f)): sys.exit('[ERREUR] Fichier manquant : ' + f)
    asi = open(os.path.join(ICI, 'files', 'SW2HD.asi'), 'rb').read()
    if asi[:2] != b'MZ' or b'2.0.3' not in asi.replace(b'\0', b''): print('[!] SW2HD.asi : version 2.0.3 non reconnue')
    dll = os.path.join(JEU, 'dinput8.dll')
    if not os.path.isfile(dll) or open(dll, 'rb').read(2) != b'MZ': sys.exit('[ERREUR] dinput8.dll introuvable dans ' + JEU)

    tex = os.path.join(JEU, 'Textures_HD')
    if not os.path.isdir(tex): tex = os.path.join(JEU, 'SW2HD')         # ancien nom
    idx = os.path.join(tex, 'index.bin')
    if not os.path.isfile(idx): sys.exit('[ERREUR] ' + idx + ' introuvable')
    crcs = lire_index(idx)
    presents = {f for f in os.listdir(tex) if f.endswith('.sw2h')}
    attendus = {'%08x.sw2h' % c for c in crcs}
    if presents != attendus:
        sys.exit('[ERREUR] index.bin et les fichiers ne correspondent pas (%d manquants, %d en trop).'
                 ' Relancez : python sw2_hd.py module hd_D' % (len(attendus - presents), len(presents - attendus)))
    print('%d textures HD, index OK' % len(crcs), flush=True)

    archive = os.path.join(ICI, '%s_v%s.zip' % (NOM, a.version))
    tmp = archive + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in FICHIERS:
            z.write(os.path.join(ICI, f), '%s/%s' % (NOM, f))
        z.write(dll, '%s/files/dinput8.dll' % NOM)
        z.writestr('%s/textures/count.txt' % NOM, str(len(attendus)))
        z.write(idx, '%s/textures/Textures_HD/index.bin' % NOM)
        for i, f in enumerate(sorted(attendus)):
            z.write(os.path.join(tex, f), '%s/textures/Textures_HD/%s' % (NOM, f))
            if (i + 1) % 500 == 0: print('  %d / %d' % (i + 1, len(attendus)), flush=True)
    print('Verification de l archive...', flush=True)
    with zipfile.ZipFile(tmp) as z:
        mauvais = z.testzip()
        n = sum(1 for x in z.namelist() if x.endswith('.sw2h'))
    if mauvais or n != len(attendus): sys.exit('[ERREUR] archive incorrecte (%s)' % (mauvais or n))
    os.replace(tmp, archive)
    print('Termine : %s (%.0f Mo)' % (archive, os.path.getsize(archive) / 1048576))
    print('Contenu : module, installeur, readme, chargeur ASI, %d textures HD ; aucun fichier original du jeu.' % n)


if __name__ == '__main__':
    main()
