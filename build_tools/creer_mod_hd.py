# -*- coding: utf-8 -*-
"""
Fabrique les 2 archives Nexus "Samurai Warriors 2 - HD Textures" (1.0.1).
Pas d'installeur (.bat) : les deux s'extraient directement dans le dossier du jeu, a cote de sw2.exe.
  - Plugin   : SW2HD.asi, SW2HD.ini, dinput8.dll, SW2HD_readme.txt (petit)
  - TexturePack : Textures_HD\\ (images HD seulement, aucun programme)

A placer dans un meme dossier (par ex. SW2_atelier\\remaster\\mod_hd) :
  creer_mod_hd.py, readme.txt, files\\SW2HD.asi, files\\SW2HD.ini

Prend les textures dans le dossier Textures_HD du jeu et le chargeur ASI (dinput8.dll)
a cote de sw2.exe. Ne modifie rien dans le jeu.

Usage :
  python creer_mod_hd.py --version 1.0.1
"""
import argparse
import os
import struct
import sys
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
JEU = os.environ.get('SW2_JEU', r'C:\Games\KOEI\SAMURAI WARRIORS 2')
NOM = 'SW2_HD_Textures'
FICHIERS = ['readme.txt', 'files/SW2HD.asi', 'files/SW2HD.ini']
DANS_ZIP = {'readme.txt': 'SW2HD_readme.txt', 'files/SW2HD.asi': 'SW2HD.asi', 'files/SW2HD.ini': 'SW2HD.ini'}


def lire_index(p):
    d = open(p, 'rb').read()
    if d[:4] != b'SW2I': sys.exit('[ERREUR] index.bin inattendu')
    n = struct.unpack_from('<I', d, 4)[0]
    return [struct.unpack_from('<I', d, 8 + 16 * i)[0] for i in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', default='1.0.1')
    a = ap.parse_args()

    for f in FICHIERS:
        if not os.path.isfile(os.path.join(ICI, f)): sys.exit('[ERREUR] Fichier manquant : ' + f)
    asi = open(os.path.join(ICI, 'files', 'SW2HD.asi'), 'rb').read()
    if asi[:2] != b'MZ' or b'1.0.1' not in asi.replace(b'\0', b''): sys.exit('[ERREUR] files\\SW2HD.asi n est pas la version 1.0.1')
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

    def finir(tmp, archive):
        with zipfile.ZipFile(tmp) as z:
            mauvais = z.testzip()
        if mauvais: sys.exit('[ERREUR] archive incorrecte (%s)' % mauvais)
        os.replace(tmp, archive)
        print('Termine : %s (%.0f Mo)' % (archive, os.path.getsize(archive) / 1048576), flush=True)

    # 1) Plugin : petit fichier, tout ce qui est programme
    plugin = os.path.join(ICI, '%s_Plugin_v%s.zip' % (NOM, a.version))
    with zipfile.ZipFile(plugin + '.tmp', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in FICHIERS:
            z.write(os.path.join(ICI, f), DANS_ZIP[f])
        z.write(dll, 'dinput8.dll')
    finir(plugin + '.tmp', plugin)

    # 2) Textures : seulement des images, aucun programme
    textures = os.path.join(ICI, '%s_TexturePack_v%s.zip' % (NOM, a.version))
    with zipfile.ZipFile(textures + '.tmp', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(idx, 'Textures_HD/index.bin')
        for i, f in enumerate(sorted(attendus)):
            z.write(os.path.join(tex, f), 'Textures_HD/%s' % f)
            if (i + 1) % 500 == 0: print('  %d / %d' % (i + 1, len(attendus)), flush=True)
    print('Verification de l archive des textures...', flush=True)
    with zipfile.ZipFile(textures + '.tmp') as z:
        n = sum(1 for x in z.namelist() if x.endswith('.sw2h'))
    if n != len(attendus): sys.exit('[ERREUR] archive des textures incomplete (%d / %d)' % (n, len(attendus)))
    finir(textures + '.tmp', textures)
    print('Contenu : Plugin (module, reglages, readme, chargeur ASI) + Textures (%d images HD) ;'
          ' aucun fichier original du jeu.' % n)

if __name__ == '__main__':
    main()
