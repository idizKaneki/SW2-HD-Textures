"""sw2_hd.py - remaster HD des textures de Samurai Warriors 2.

Etape 1 (extraire) :
    python sw2_hd.py extraire
  -> copie toutes les textures du jeu en PNG, sans doublons, rangees par categorie :
     textures_originales\\  = les couleurs (sans canal alpha : c'est ce dossier qu'on agrandit avec l'IA)
     textures_masques\\     = le canal alpha a part (masque de brillance / transparence), gere par le script
     (+ manifeste.tsv qui note d'ou vient chacune)
     et prepare un petit dossier "echantillon" (une vingtaine de textures variees)
     pour choisir le modele d'IA.
     Ne modifie jamais les fichiers du jeu.

Etape 2 (injecter) :
    python sw2_hd.py injecter DOSSIER_HD
  -> prend les PNG agrandis du dossier (ex. hd_A, cherche aussi dans les sous-dossiers),
     leur recolle les masques, les reencode au format du jeu, reconstruit les archives
     dans hd_build\\ puis les installe dans le jeu (les originaux sont sauvegardes avant).
     Pour l'instant : seulement les textures rangees "seules" dans leur entree (personnages,
     soldats...). Les autres sont comptees et laissees d'origine.

Analyse (conteneurs) :
    python sw2_hd.py conteneurs
  -> ecrit conteneurs.zip (rapport + quelques petites entrees d'exemple) a m'envoyer.
     Lecture seule.

Version anglaise :
    python sw2_hd.py extraire_us
  -> ajoute les images propres a la version anglaise (lues dans SW2_atelier\\originaux_us),
     copiees aussi dans textures_us\\ pour chaiNNer.

Analyse (empreintes) :
    python sw2_hd.py empreintes
  -> ecrit empreintes.tsv (empreinte CRC32 des pixels de chaque texture) a m'envoyer
     avec le journal SW2TexDiag.log. Lecture seule.

Module HD (methode conseillee) :
    python sw2_hd.py module DOSSIER_HD
  -> prepare le dossier SW2HD\\ du jeu pour le module SW2HD.asi : TOUTES les textures en x2
     (3D avec mipmaps, menus/ecrans sans), francaises et anglaises, identifiees par l'empreinte
     de l'image d'origine. Les archives du jeu restent d'origine (python sw2_hd.py restaurer).
     Relancable : seules les images nouvelles ou modifiees sont reecrites.

Echantillon cible :
    python sw2_hd.py echantillon2
  -> dossier echantillon2 : 6 portraits de la selection de personnage + 10 textures variees,
     pour comparer des recettes d'IA. Lecture seule.

Copie d'une selection :
    python sw2_hd.py copier LISTE.txt DOSSIER
  -> copie les textures d'origine dont l'empreinte est dans LISTE.txt (une par ligne) dans DOSSIER.

Bilan pour la publication :
    python sw2_hd.py bilan
  -> taille du dossier SW2HD par categorie et taille zip estimee ; ecrit categories.tsv. Lecture seule.

Etape 3 (restaurer) :
    python sw2_hd.py restaurer
  -> remet les archives d'origine dans le jeu.

Les archives lues : LINKDATA_BNS_NA depuis la sauvegarde d'origine (sauvegarde_bns) si elle existe,
sinon depuis le jeu ; LINKDATA_DNS_NA depuis le jeu.
"""
import sys, os, struct, hashlib, shutil

JEU = os.environ.get('SW2_JEU', r'C:\Games\KOEI\SAMURAI WARRIORS 2')
ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, 'textures_originales')
SORTIE_ALPHA = os.path.join(ICI, 'textures_masques')
SAUVE_BNS = os.path.join(ICI, 'sauvegarde_bns')
SAUVE_DNS = os.path.join(ICI, 'sauvegarde_dns')
BUILD = os.path.join(ICI, 'hd_build')
TEXTES_US = os.path.join(ICI, 'textures_us')   # images propres a la version anglaise, a passer dans chaiNNer


def dossier_us():
    """dossier des archives anglaises d'origine (SW2_atelier\\originaux_us, cherche aussi dans ses sous-dossiers)"""
    base = os.environ.get('SW2_US', os.path.join(ICI, '..', 'originaux_us'))
    for racine, _, fichiers in os.walk(base):
        if any(f.lower() == 'linkdata_bns_na.idx' for f in fichiers): return racine
    return None


def archive_us(base):
    d = dossier_us()
    if not d: return None
    i, l = trouver(d, base + '.idx'), trouver(d, base + '.lnk')
    return (i, l) if i and l else None
SECTEUR = 2048
MAGIC = b'GT1G'

# categories approximatives (d'apres le diagnostic du 13/10/2026)
CATEGORIES_BNS = [(0, 434, 'interface'), (435, 574, 'personnages'), (575, 834, 'soldats'),
                  (835, 1264, 'armes_objets'), (1265, 1317, 'calligraphies'), (1318, 1348, 'ciels'),
                  (1349, 99999, 'decors')]


def categorie(arch, e):
    if arch == 'DNS': return 'ecrans_dns'
    for a, b, nom in CATEGORIES_BNS:
        if a <= e <= b: return nom
    return 'divers'


def trouver(dossier, nom):
    if not os.path.isdir(dossier): return None
    for f in os.listdir(dossier):
        if f.lower() == nom.lower(): return os.path.join(dossier, f)
    return None


def archive(base):
    """renvoie (idx, lnk) : BNS depuis la sauvegarde d'origine si possible"""
    dossiers = [os.path.join(JEU, 'linkdata'), JEU, 'linkdata', '.']
    if base == 'LINKDATA_BNS_NA': dossiers.insert(0, SAUVE_BNS)
    for d in dossiers:
        i, l = trouver(d, base + '.idx'), trouver(d, base + '.lnk')
        if i and l: return i, l
    sys.exit(base + ' introuvable')


def lire_idx(p):
    d = open(p, 'rb').read()
    if d[:4] != b'SM4L': sys.exit(p + ' : index inattendu')
    return [struct.unpack_from('<4I', d, 16 + 16 * i) for i in range(struct.unpack_from('<I', d, 4)[0])]


def octets(fmt, w, h):
    if fmt == 0x06: return max(1, w // 4) * max(1, h // 4) * 8
    if fmt == 0x08: return max(1, w // 4) * max(1, h // 4) * 16
    if fmt in (0x01, 0x02): return w * h * 4
    return None


def blocs(data):
    """(offset bloc, [(index, offset en-tete, fmt, w, h, mips)]) pour chaque GT1G valide de l'entree"""
    i = 0
    while True:
        i = data.find(MAGIC, i)
        if i < 0: return
        ok = len(data) >= i + 24 and all(48 <= c <= 57 for c in data[i + 4:i + 8])
        if ok:
            tot, tab, nb = struct.unpack_from('<3I', data, i + 8)
            ok = 0 < nb < 4096 and 0x10 <= tab < 0x10000 and 0x20 <= tot and i + tot <= len(data)
        if not ok: i += 4; continue
        tx = []
        for k in range(nb):
            p = i + tab + struct.unpack_from('<I', data, i + tab + 4 * k)[0]
            t = data[p:p + 8]
            tx.append((k, p, t[1], 1 << (t[2] & 15), 1 << (t[2] >> 4), t[0] >> 4))
        yield i, tx
        i += tot


def decoder(fmt, w, h, px):
    from PIL import Image
    if fmt == 0x06: return Image.frombuffer('RGBA', (w, h), px, 'bcn', 1).copy()
    if fmt == 0x08: return Image.frombuffer('RGBA', (w, h), px, 'bcn', 3).copy()
    return Image.frombuffer('RGBA', (w, h), px, 'raw', 'BGRA', 0, 1).copy()


def extraire():
    try:
        from PIL import Image
    except ImportError:
        sys.exit('Pillow manquant : pip install pillow')
    for d in (SORTIE, SORTIE_ALPHA):
        if os.path.isdir(d): shutil.rmtree(d)
    os.makedirs(SORTIE, exist_ok=True)
    vus = {}      # empreinte -> [categorie, fmt, w, h, mips, [occurrences]]
    for base, court in (('LINKDATA_BNS_NA', 'BNS'), ('LINKDATA_DNS_NA', 'DNS')):
        idx, lnk = archive(base); E = lire_idx(idx)
        print(f'{court} : lecture de {lnk}', flush=True)
        with open(lnk, 'rb') as f:
            for e, (s, ns, sz, _) in enumerate(E):
                if sz < 32: continue
                f.seek(s * SECTEUR); data = f.read(sz)
                for off, tx in blocs(data):
                    for k, p, fmt, w, h, mips in tx:
                        n = octets(fmt, w, h)
                        if n is None or p + 8 + n > len(data): continue
                        px = data[p + 8:p + 8 + n]
                        cle = hashlib.md5(bytes([fmt]) + struct.pack('<HH', w, h) + px).hexdigest()[:16]
                        occ = f'{court}:{e}:{off}:{k}'
                        if cle in vus:
                            vus[cle][5].append(occ); continue
                        cat = categorie(court, e)
                        dossier = os.path.join(SORTIE, cat); os.makedirs(dossier, exist_ok=True)
                        im = decoder(fmt, w, h, px)
                        im.convert('RGB').save(os.path.join(dossier, cle + '.png'))
                        a = im.getchannel('A')
                        if a.getextrema() != (255, 255):
                            da = os.path.join(SORTIE_ALPHA, cat); os.makedirs(da, exist_ok=True)
                            a.save(os.path.join(da, cle + '.png'))
                        vus[cle] = [cat, fmt, w, h, mips, [occ]]
                if e % 200 == 0: print(f'  entree {e}/{len(E)} - {len(vus)} textures uniques', flush=True)
    with open(os.path.join(SORTIE, 'manifeste.tsv'), 'w', encoding='utf-8') as m:
        m.write('empreinte\tcategorie\tformat\tlargeur\thauteur\tmips\templacements\n')
        for cle, (cat, fmt, w, h, mips, occ) in sorted(vus.items(), key=lambda x: (x[1][0], x[0])):
            m.write(f'{cle}\t{cat}\t{fmt}\t{w}\t{h}\t{mips}\t{";".join(occ)}\n')
    echantillon(vus)
    par_cat = {}
    for v in vus.values(): par_cat[v[0]] = par_cat.get(v[0], 0) + 1
    print('Termine :', len(vus), 'textures uniques')
    for c, n in sorted(par_cat.items()): print(f'  {c:15s} {n}')
    print('Dossier :', SORTIE)


def echantillon(vus):
    """quelques textures variees (les plus grandes de chaque categorie) pour comparer les modeles d'IA"""
    dest = os.path.join(SORTIE, '..', 'echantillon')
    if os.path.isdir(dest): shutil.rmtree(dest)
    os.makedirs(dest)
    par_cat = {}
    for cle, (cat, fmt, w, h, mips, occ) in vus.items():
        par_cat.setdefault(cat, []).append((w * h, len(occ), cle))
    for cat, lst in par_cat.items():
        lst.sort(reverse=True)
        pas = max(1, len(lst) // 3)
        for _, _, cle in lst[::pas][:3]:
            shutil.copyfile(os.path.join(SORTIE, cat, cle + '.png'), os.path.join(dest, f'{cat}_{cle}.png'))
    print('Echantillon :', os.path.abspath(dest))


# ---------------------------------------------------------------- reinjection

def log2(n): return n.bit_length() - 1


def lire_manifeste():
    p = os.path.join(SORTIE, 'manifeste.tsv')
    if not os.path.exists(p): sys.exit('manifeste.tsv introuvable : lance d abord  extraire')
    m = {}
    for ligne in open(p, encoding='utf-8').read().splitlines()[1:]:
        c = ligne.split('\t')
        if len(c) < 7: continue
        m[c[0]] = dict(cat=c[1], fmt=int(c[2]), w=int(c[3]), h=int(c[4]), mips=int(c[5]), occ=c[6].split(';'))
    return m


def encoder(im, fmt):
    import io
    if fmt == 0x01 or fmt == 0x02:
        return im.tobytes('raw', 'BGRA')
    out = io.BytesIO(); im.save(out, 'DDS', pixel_format={6: 'DXT1', 8: 'DXT5'}[fmt])
    n = octets(fmt, im.width, im.height); d = out.getvalue()[128:]
    if len(d) < n: raise ValueError('encodage incomplet')
    return d[:n]


FACTEUR_HD = 2      # seul agrandissement accepte (au-dela, le jeu manque de memoire)
# Images 2D (menus, HUD, ecrans) : le jeu les decoupe en pixels exacts, une image x2 s'affiche
# tronquee (teste le 14/10/2026). Elles restent d'origine (et restent compatibles avec le mod FR).
CATEGORIES_EXCLUES = {'interface', 'ecrans_dns'}
FACTEURS = {}


def image_hd(cle, info, hd):
    """image RGBA finale (couleurs IA + masque agrandi) ou None"""
    from PIL import Image
    p = hd.get(cle)
    if not p: return None
    im = Image.open(p).convert('RGB')
    w, h = im.size
    FACTEURS[(w // info['w']) if w % info['w'] == 0 else 0] = FACTEURS.get((w // info['w']) if w % info['w'] == 0 else 0, 0) + 1
    if (w, h) != (info['w'] * FACTEUR_HD, info['h'] * FACTEUR_HD):
        return 'taille'
    pm = os.path.join(SORTIE_ALPHA, info['cat'], cle + '.png')
    if os.path.exists(pm):
        a = Image.open(pm).convert('L').resize((w, h), Image.LANCZOS)
    else:
        a = Image.new('L', (w, h), 255)
    im.putalpha(a)
    return im


def reconstruire(data, remplace):
    """remplace = {index texture: image RGBA} dans le bloc GT1G qui commence l'entree"""
    tot, tab, nb = struct.unpack_from('<3I', data, 8)
    offs = [struct.unpack_from('<I', data, tab + 4 * k)[0] for k in range(nb)]
    neuf = bytearray(data[:tab + offs[0]]); noffs = []
    for k in range(nb):
        p = tab + offs[k]; fin = tab + offs[k + 1] if k + 1 < nb else tot
        t = bytearray(data[p:p + 8]); fmt = t[1]
        w, h = 1 << (t[2] & 15), 1 << (t[2] >> 4)
        noffs.append(len(neuf) - tab)
        if k in remplace:
            im = remplace[k]; n = octets(fmt, w, h)
            t[2] = log2(im.width) | (log2(im.height) << 4)
            neuf += t + encoder(im, fmt) + data[p + 8 + n:fin]
        else:
            neuf += data[p:fin]
    for k, o in enumerate(noffs): struct.pack_into('<I', neuf, tab + 4 * k, o)
    struct.pack_into('<I', neuf, 8, len(neuf))
    return bytes(neuf + data[tot:])


def lire_conteneur(d):
    """('S'|'L', [(debut, fin)], position de la table) ou None.
    S : [33b59][n][10][0] puis n x (debut/16, taille).  L : [n][debuts x n], fin = debut suivant."""
    if len(d) < 16: return None
    v0, n = struct.unpack_from('<2I', d, 0)
    if v0 == 0x33b59 and 0 < n < 100000 and 16 + 8 * n <= len(d):
        enf = []
        for k in range(n):
            o, t = struct.unpack_from('<2I', d, 16 + 8 * k); o *= 16
            if o < 16 + 8 * n or o + t > len(d): return None
            enf.append((o, o + t))
        return 'S', enf
    n = v0
    if 0 < n < 100000 and 4 + 4 * n <= len(d):
        offs = list(struct.unpack_from('<%dI' % n, d, 4))
        if offs[0] < 4 + 4 * n or offs[0] > 4 + 4 * n + 64 or offs != sorted(offs) or offs[-1] > len(d): return None
        return 'L', [(o, (offs[i + 1] if i + 1 < n else len(d))) for i, o in enumerate(offs)]
    return None


def reconstruire_entree(data, remplace):
    """remplace = {offset du bloc GT1G: {index texture: image}} -> (donnees, nb remplacees, nb ratees)"""
    tous = sum(len(v) for v in remplace.values())
    if set(remplace) == {0} and data[:4] == MAGIC:
        return reconstruire(data, remplace[0]), tous, 0
    c = lire_conteneur(data)
    if not c:
        if 0 in remplace and data[:4] == MAGIC:
            return reconstruire(data, remplace[0]), len(remplace[0]), tous - len(remplace[0])
        return data, 0, tous
    typ, enf = c
    debuts = [a for a, b in enf]
    align = 2048
    while align > 4 and any(a % align for a in debuts): align //= 2
    if typ == 'S': align = max(align, 16)
    neuf = bytearray(data[:min(debuts)]); nouv = []; faits = 0
    for a, b in enf:
        while len(neuf) % align: neuf.append(0)
        morceau = data[a:b]
        if a in remplace and morceau[:4] == MAGIC:
            morceau = reconstruire(morceau, remplace[a]); faits += len(remplace[a])
        nouv.append((len(neuf), len(morceau))); neuf += morceau
    if typ == 'S':
        for k, (a, t) in enumerate(nouv): struct.pack_into('<2I', neuf, 16 + 8 * k, a // 16, t)
        fin = max(b for a, b in enf); neuf += data[fin:]
    else:
        for k, (a, t) in enumerate(nouv): struct.pack_into('<I', neuf, 4 + 4 * k, a)
    # verification : la table relue donne bien les memes morceaux
    c2 = lire_conteneur(bytes(neuf))
    if not c2 or len(c2[1]) != len(enf): return data, 0, tous
    for (a, b), (a2, b2) in zip(enf, c2[1]):
        if a not in remplace and data[a:b] != bytes(neuf[a2:a2 + (b - a)]): return data, 0, tous
    return bytes(neuf), faits, tous - faits


def source(base):
    """archive d'origine : la sauvegarde si elle existe, sinon le jeu (sauvegarde creee au passage)"""
    sauve = SAUVE_BNS if base == 'LINKDATA_BNS_NA' else SAUVE_DNS
    i, l = trouver(sauve, base + '.idx'), trouver(sauve, base + '.lnk')
    if i and l: return i, l
    jeu = os.path.join(JEU, 'linkdata')
    i, l = trouver(jeu, base + '.idx'), trouver(jeu, base + '.lnk')
    if not (i and l): sys.exit(base + ' introuvable dans ' + jeu)
    os.makedirs(sauve, exist_ok=True)
    print('sauvegarde de', base, '...', flush=True)
    for f in (i, l): shutil.copyfile(f, os.path.join(sauve, os.path.basename(f)))
    return trouver(sauve, base + '.idx'), trouver(sauve, base + '.lnk')


def injecter(dossier):
    dossier = dossier if os.path.isabs(dossier) else os.path.join(ICI, dossier)
    if not os.path.isdir(dossier): sys.exit('dossier introuvable : ' + dossier)
    man = lire_manifeste()
    hd = {}
    for racine, _, fichiers in os.walk(dossier):
        for f in fichiers:
            if f.lower().endswith('.png'): hd[f[:-4].split('_')[-1]] = os.path.join(racine, f)
    a_faire = {}   # (archive, entree) -> {(offset bloc, index): cle}
    ignore = {'conteneur': 0, 'mipmaps': 0, 'taille': 0, 'exclues': 0}
    for cle, info in man.items():
        if cle not in hd: continue
        if info['cat'] in CATEGORIES_EXCLUES: ignore['exclues'] += 1; continue
        if info['mips'] > 1: ignore['mipmaps'] += 1; continue
        for occ in info['occ']:
            arch, e, off, k = occ.split(':')
            if arch not in ('BNS', 'DNS'): continue
            a_faire.setdefault((arch, int(e)), {})[(int(off), int(k))] = cle
    print(f'{len(hd)} images HD trouvees ; {sum(len(v) for v in a_faire.values())} emplacements a remplacer', flush=True)
    os.makedirs(BUILD, exist_ok=True); faits = 0; cache = {}
    for base, court in (('LINKDATA_BNS_NA', 'BNS'), ('LINKDATA_DNS_NA', 'DNS')):
        cibles = {e: v for (a, e), v in a_faire.items() if a == court}
        dest_l = os.path.join(BUILD, base + '.lnk'); dest_i = os.path.join(BUILD, base + '.idx')
        for f in (dest_l, dest_i):
            if os.path.exists(f): os.remove(f)
        if not cibles: continue
        idx, lnk = source(base); E = lire_idx(idx); nouv = []; cur = 0
        print(f'{court} : reconstruction ({len(cibles)} entrees modifiees)...', flush=True)
        with open(lnk, 'rb') as f, open(dest_l, 'wb') as o:
            for e, (s0, ns, sz, x) in enumerate(E):
                data = None
                if e in cibles:
                    f.seek(s0 * SECTEUR); brut = f.read(sz); remplace = {}
                    for (off, k), cle in cibles[e].items():
                        if cle not in cache: cache[cle] = image_hd(cle, man[cle], hd)
                        im = cache[cle]
                        if im == 'taille': ignore['taille'] += 1
                        elif im is not None: remplace.setdefault(off, {})[k] = im
                    if remplace:
                        data, n, rate = reconstruire_entree(brut, remplace)
                        faits += n; ignore['conteneur'] += rate
                if data is not None:
                    cnt = (len(data) + SECTEUR - 1) // SECTEUR
                    o.write(data + b'\0' * (cnt * SECTEUR - len(data))); taille = len(data)
                else:
                    f.seek(s0 * SECTEUR); reste = ns * SECTEUR; cnt = ns; taille = sz
                    while reste:
                        b = f.read(min(reste, 1 << 24)); o.write(b); reste -= len(b)
                nouv.append((cur, cnt, taille, x)); cur += cnt
                if e % 500 == 0: print(f'  entree {e}/{len(E)}', flush=True)
        with open(dest_i, 'wb') as o:
            o.write(b'SM4L' + struct.pack('<3I', len(nouv), cur, 0))
            for v in nouv: o.write(struct.pack('<4I', *v))
        if len(cache) > 400: cache.clear()
    print('Agrandissements trouves dans le dossier :', ', '.join(f'x{k}: {v}' for k, v in sorted(FACTEURS.items())))
    print(f'{faits} textures remplacees.', 'Laissees d origine :',
          f"{ignore['exclues']} (interface/ecrans 2D, volontairement d origine), {ignore['conteneur']} (conteneur de format inconnu), {ignore['mipmaps']} (avec mipmaps),",
          f"{ignore['taille']} (pas en x{FACTEUR_HD} : refusees)")
    installer_build()


def installer_build():
    jeu = os.path.join(JEU, 'linkdata')
    for base in ('LINKDATA_BNS_NA', 'LINKDATA_DNS_NA'):
        l, i = os.path.join(BUILD, base + '.lnk'), os.path.join(BUILD, base + '.idx')
        if not (os.path.exists(l) and os.path.exists(i)):
            # rien a modifier dans cette archive : on remet l'originale si une sauvegarde existe
            sauve = SAUVE_BNS if base == 'LINKDATA_BNS_NA' else SAUVE_DNS
            si, sl = trouver(sauve, base + '.idx'), trouver(sauve, base + '.lnk')
            if si and sl:
                print('archive d origine remise :', base, flush=True)
                shutil.copyfile(si, trouver(jeu, base + '.idx')); shutil.copyfile(sl, trouver(jeu, base + '.lnk'))
            continue
        source(base)   # garantit la sauvegarde avant d'ecraser
        print('installation de', base, '...', flush=True)
        shutil.copyfile(i, trouver(jeu, base + '.idx') or os.path.join(jeu, base + '.idx'))
        shutil.copyfile(l, trouver(jeu, base + '.lnk') or os.path.join(jeu, base + '.lnk'))
    print('Installe. Lance le jeu (option LAA de sw2.exe activee).')
    print('Pour revenir en arriere : python', os.path.abspath(__file__), 'restaurer')


def restaurer():
    jeu = os.path.join(JEU, 'linkdata')
    for base, sauve in (('LINKDATA_BNS_NA', SAUVE_BNS), ('LINKDATA_DNS_NA', SAUVE_DNS)):
        i, l = trouver(sauve, base + '.idx'), trouver(sauve, base + '.lnk')
        if not (i and l): continue
        print('restauration de', base, '...', flush=True)
        shutil.copyfile(i, trouver(jeu, base + '.idx')); shutil.copyfile(l, trouver(jeu, base + '.lnk'))
    print('Archives d origine remises en place.')


def crc_par_cle(garder=None):
    """{cle: crc32 des pixels d'origine (niveau 0)} lu dans les archives d'origine"""
    import zlib
    man = lire_manifeste(); par_occ = {}; res = {}
    for cle, info in man.items():
        if garder and not garder(info): continue
        a, e, off, k = info['occ'][0].split(':'); par_occ.setdefault((a, int(e)), []).append((int(off), int(k), cle))
    for base, court in (('LINKDATA_BNS_NA', 'BNS'), ('LINKDATA_DNS_NA', 'DNS'), ('LINKDATA_BNS_NA', 'UB'), ('LINKDATA_DNS_NA', 'UD')):
        if not any(a == court for a, e in par_occ): continue
        if court in ('UB', 'UD'):
            ar = archive_us(base)
            if not ar: print('archives anglaises introuvables : images US ignorees'); continue
            idx, lnk = ar
        else:
            idx, lnk = source(base)
        E = lire_idx(idx)
        with open(lnk, 'rb') as f:
            for (a, e), lst in sorted(par_occ.items()):
                if a != court: continue
                s0, ns, sz, _ = E[e]; f.seek(s0 * SECTEUR); d = f.read(sz)
                tx = {off: t for off, t in blocs(d)}
                for off, k, cle in lst:
                    if off not in tx or k >= len(tx[off]): continue
                    _, p, fmt, w, h, mips = tx[off][k]; nb = octets(fmt, w, h)
                    res[cle] = zlib.crc32(d[p + 8:p + 8 + nb]) & 0xFFFFFFFF
    return res


D3D_FMT = {0x06: 0x31545844, 0x07: 0x33545844, 0x08: 0x35545844, 0x01: 21, 0x02: 21}



def dossier_hd():
    """dossier des images HD du jeu : Textures_HD (l'ancien dossier SW2HD est renomme)"""
    neuf, ancien = os.path.join(JEU, 'Textures_HD'), os.path.join(JEU, 'SW2HD')
    if not os.path.exists(neuf) and os.path.isdir(ancien):
        os.rename(ancien, neuf); print('dossier SW2HD renomme en Textures_HD')
    return neuf

CATS_2D = ('interface', 'ecrans_dns')


def niveaux(im, plein):
    """chaine de mipmaps (niveau 0 compris), jusqu'a 4 pixels de cote ; plein=False -> 1 seul niveau"""
    from PIL import Image
    lv = [im]
    while plein and min(lv[-1].size) > 4:
        w, h = lv[-1].width // 2, lv[-1].height // 2
        rgb = lv[-1].convert('RGB').resize((w, h), Image.LANCZOS)
        a = lv[-1].getchannel('A').resize((w, h), Image.LANCZOS)
        rgb.putalpha(a); lv.append(rgb)
    return lv


def module(dossier, categories=None):
    """prepare le dossier SW2HD du jeu pour SW2HD.asi : toutes les textures (3D avec mipmaps, 2D sans)"""
    from PIL import Image
    dossier = dossier if os.path.isabs(dossier) else os.path.join(ICI, dossier)
    if not os.path.isdir(dossier): sys.exit('dossier introuvable : ' + dossier)
    man = lire_manifeste(); hd = {}
    for racine, _, fichiers in os.walk(dossier):
        for f in fichiers:
            if f.lower().endswith('.png'): hd[f[:-4].split('_')[-1]] = os.path.join(racine, f)
    garder = lambda i: (categories is None or i['cat'] in categories) and i['fmt'] in D3D_FMT
    print('calcul des empreintes des images d origine (francaises et anglaises)...', flush=True)
    crcs = crc_par_cle(garder)
    dest = dossier_hd(); os.makedirs(dest, exist_ok=True)
    index = {}; manque = refuse = deja = 0; total = 0; n = 0
    for cle, info in sorted(man.items()):
        if not garder(info) or cle not in crcs: continue
        if cle not in hd: manque += 1; continue
        crc = crcs[cle]
        if crc in index: continue
        cible = os.path.join(dest, '%08x.sw2h' % crc)
        source_png = hd[cle]
        if os.path.exists(cible) and os.path.getmtime(cible) >= os.path.getmtime(source_png):
            with open(cible, 'rb') as o: t = o.read(8)
            if t[:4] == b'SW2H' and struct.unpack_from('<I', t, 4)[0] == 2:
                index[crc] = (info['w'], info['h'], D3D_FMT[info['fmt']]); deja += 1; continue
        im = image_hd(cle, info, hd)
        if im is None or im == 'taille': refuse += 1; continue
        fmt = info['fmt']
        masque = os.path.exists(os.path.join(SORTIE_ALPHA, info['cat'], cle + '.png'))
        hfmt = 0x01 if fmt in (0x01, 0x02) else (0x06 if fmt == 0x06 and not masque else 0x08)
        lv = niveaux(im, info['cat'] not in CATS_2D)
        data = b''.join(encoder(x, hfmt) for x in lv)
        tete = struct.pack('<12I', 0x48325753, 2, info['w'], info['h'], D3D_FMT[fmt], im.width, im.height,
                           D3D_FMT[hfmt], len(lv), 0, 0, 0)
        with open(cible + '.tmp', 'wb') as o: o.write(tete + data)
        os.replace(cible + '.tmp', cible)
        index[crc] = (info['w'], info['h'], D3D_FMT[fmt]); total += len(data); n += 1
        if n % 200 == 0: print(f'  {n} images ecrites...', flush=True)
    # nettoyage des images qui ne servent plus
    for f in os.listdir(dest):
        if f.endswith('.sw2h') and int(f[:8], 16) not in index: os.remove(os.path.join(dest, f))
    with open(os.path.join(dest, 'index.bin'), 'wb') as o:
        o.write(struct.pack('<2I', 0x49325753, len(index)))
        for crc in sorted(index): o.write(struct.pack('<4I', crc, *index[crc]))
    taille = sum(os.path.getsize(os.path.join(dest, f)) for f in os.listdir(dest))
    us = [c for c, i in man.items() if garder(i) and i['occ'][0][:1] == 'U']
    print(f"images anglaises : {len(us)} dans le manifeste, {sum(c in crcs for c in us)} reconnues dans les archives US,",
          f"{sum(c in hd for c in us)} avec image HD")
    print(f'{len(index)} images HD dans {dest} ({n} ecrites, {deja} deja a jour ; {taille // 1048576} Mo au total).',
          f'Sans image HD : {manque} ; refusees (pas en x{FACTEUR_HD}) : {refuse}')
    print('Avec le module, les archives du jeu doivent etre celles d origine : python sw2_hd.py restaurer')


def extraire_us():
    """ajoute les textures propres a la version anglaise (titres, ecrans en anglais...)"""
    from PIL import Image
    man = lire_manifeste()
    vus = {c: i for c, i in man.items()}
    if os.path.isdir(TEXTES_US): shutil.rmtree(TEXTES_US)
    os.makedirs(TEXTES_US); nouvelles = 0
    for base, court in (('LINKDATA_BNS_NA', 'UB'), ('LINKDATA_DNS_NA', 'UD')):
        ar = archive_us(base)
        if not ar: sys.exit('archives anglaises introuvables dans ' + os.path.abspath(os.path.join(ICI, '..', 'originaux_us')))
        idx, lnk = ar; E = lire_idx(idx)
        print(f'{court} : lecture de {lnk}', flush=True)
        with open(lnk, 'rb') as f:
            for e, (s0, ns, sz, _) in enumerate(E):
                if sz < 32: continue
                f.seek(s0 * SECTEUR); data = f.read(sz)
                for off, tx in blocs(data):
                    for k, p, fmt, w, h, mips in tx:
                        nb = octets(fmt, w, h)
                        if nb is None or p + 8 + nb > len(data): continue
                        px = data[p + 8:p + 8 + nb]
                        cle = hashlib.md5(bytes([fmt]) + struct.pack('<HH', w, h) + px).hexdigest()[:16]
                        occ = f'{court}:{e}:{off}:{k}'
                        if cle in vus:
                            if not any(o.startswith(court) for o in vus[cle]['occ']): vus[cle]['occ'].append(occ)
                            continue
                        cat = categorie('DNS' if court == 'UD' else 'BNS', e)
                        im = decoder(fmt, w, h, px)
                        os.makedirs(os.path.join(SORTIE, cat), exist_ok=True)
                        im.convert('RGB').save(os.path.join(SORTIE, cat, cle + '.png'))
                        im.convert('RGB').save(os.path.join(TEXTES_US, f'{cat}_{cle}.png'))
                        a = im.getchannel('A')
                        if a.getextrema() != (255, 255):
                            os.makedirs(os.path.join(SORTIE_ALPHA, cat), exist_ok=True)
                            a.save(os.path.join(SORTIE_ALPHA, cat, cle + '.png'))
                        vus[cle] = dict(cat=cat, fmt=fmt, w=w, h=h, mips=mips, occ=[occ]); nouvelles += 1
                if e % 500 == 0: print(f'  entree {e}/{len(E)} - {nouvelles} images propres a l anglais', flush=True)
    with open(os.path.join(SORTIE, 'manifeste.tsv'), 'w', encoding='utf-8') as m:
        m.write('empreinte\tcategorie\tformat\tlargeur\thauteur\tmips\templacements\n')
        for cle, i in sorted(vus.items(), key=lambda x: (x[1]['cat'], x[0])):
            m.write(f"{cle}\t{i['cat']}\t{i['fmt']}\t{i['w']}\t{i['h']}\t{i['mips']}\t{';'.join(i['occ'])}\n")
    print(nouvelles, 'images propres a la version anglaise copiees dans', TEXTES_US)
    print('A passer dans chaiNNer (chaine D) avec la sortie dans hd_D, puis : python sw2_hd.py module hd_D')


def echantillon2():
    from PIL import Image
    man = lire_manifeste()
    dest = os.path.join(ICI, 'echantillon2')
    if os.path.isdir(dest): shutil.rmtree(dest)
    os.makedirs(dest)
    def entrees(info): return [int(o.split(':')[1]) for o in info['occ'] if o.startswith('BNS:')]
    def prendre(a, b, n):
        lst = sorted((c for c, i in man.items() if i['cat'] == 'interface' and i['w'] >= 512 and i['h'] >= 512
                      and any(a <= e <= b for e in entrees(i))), key=lambda c: (min(entrees(man[c])), c))
        return lst[::max(1, len(lst) // n)][:n]
    choix = prendre(286, 305, 5) + prendre(208, 227, 1)   # personnages en pied (selection) + 1 portrait sepia
    autres = []
    for cat in ('personnages', 'soldats', 'decors', 'armes_objets', 'interface'):
        lst = sorted(c for c, i in man.items() if i['cat'] == cat and i['w'] * i['h'] >= 256 * 256)
        autres += lst[::max(1, len(lst) // 2)][:2]
    for c in choix + autres:
        shutil.copyfile(os.path.join(SORTIE, man[c]['cat'], c + '.png'),
                        os.path.join(dest, ('portrait' if c in choix else man[c]['cat']) + '_' + c + '.png'))
    print(len(choix), 'portraits et', len(autres), 'autres textures copies dans', dest)


def copier(liste, dossier):
    man = lire_manifeste()
    liste = liste if os.path.isabs(liste) else os.path.join(ICI, liste)
    dest = dossier if os.path.isabs(dossier) else os.path.join(ICI, dossier)
    cles = [l.strip() for l in open(liste, encoding='utf-8') if l.strip() and not l.startswith('#')]
    if os.path.isdir(dest): shutil.rmtree(dest)
    os.makedirs(dest); n = 0
    for c in cles:
        if c in man:
            shutil.copyfile(os.path.join(SORTIE, man[c]['cat'], c + '.png'), os.path.join(dest, c + '.png')); n += 1
        else: print('inconnue :', c)
    print(n, 'textures copiees dans', dest)


def empreintes():
    import zlib
    man = lire_manifeste(); par_occ = {}
    for cle, info in man.items():
        a, e, off, k = info['occ'][0].split(':'); par_occ.setdefault((a, int(e)), []).append((int(off), int(k), cle))
    out = open(os.path.join(ICI, 'empreintes.tsv'), 'w', encoding='utf-8'); n = 0
    out.write('empreinte\tcategorie\tformat\tlargeur\thauteur\tmips\tcrc32\n')
    for base, court in (('LINKDATA_BNS_NA', 'BNS'), ('LINKDATA_DNS_NA', 'DNS')):
        idx, lnk = source(base); E = lire_idx(idx)
        with open(lnk, 'rb') as f:
            for (a, e), lst in sorted(par_occ.items()):
                if a != court: continue
                s0, ns, sz, _ = E[e]; f.seek(s0 * SECTEUR); d = f.read(sz)
                tx = {off: t for off, t in blocs(d)}
                for off, k, cle in lst:
                    if off not in tx or k >= len(tx[off]): continue
                    _, p, fmt, w, h, mips = tx[off][k]; nb = octets(fmt, w, h)
                    crc = zlib.crc32(d[p + 8:p + 8 + nb]) & 0xFFFFFFFF
                    i = man[cle]
                    out.write(f"{cle}\t{i['cat']}\t{fmt}\t{w}\t{h}\t{mips}\t{crc:08x}\n"); n += 1
    out.close(); print(n, 'empreintes ecrites dans', os.path.join(ICI, 'empreintes.tsv'))


def conteneurs():
    """rapport sur les entrees ou les textures ne sont pas au debut (conteneurs)"""
    import zipfile
    man = lire_manifeste(); par = {}
    for cle, info in man.items():
        for occ in info['occ']:
            a, e, off, k = occ.split(':')
            if off != '0': par.setdefault((a, int(e)), set()).add(int(off))
    rap = [f'{len(par)} entrees avec des textures dans un conteneur\n']
    exemples = []
    for base, court in (('LINKDATA_BNS_NA', 'BNS'), ('LINKDATA_DNS_NA', 'DNS')):
        idx, lnk = source(base); E = lire_idx(idx)
        ents = sorted(e for a, e in par if a == court)
        with open(lnk, 'rb') as f:
            for e in ents:
                s0, ns, sz, _ = E[e]; f.seek(s0 * SECTEUR); d = f.read(sz)
                gt = sorted(o for o, _ in blocs(d))
                n = min(64, len(d) // 4); tete = struct.unpack_from('<%dI' % n, d, 0)
                trouves = [(i * 4, v) for i, v in enumerate(tete) if v in gt]
                rap.append(f'{court} {e} taille {sz} | blocs GT1G a {gt[:12]}{" ..." if len(gt) > 12 else ""} ({len(gt)})\n')
                rap.append(f'   debut : {" ".join("%x" % v for v in tete[:24])}\n')
                rap.append(f'   offsets GT1G cites au debut : {trouves[:12]}\n')
                exemples.append((sz, court, e, d))
    exemples.sort()
    choix = exemples[:4] + [x for x in exemples if x[0] > 1 << 20][:1]
    with zipfile.ZipFile(os.path.join(ICI, 'conteneurs.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('rapport.txt', ''.join(rap))
        for sz, court, e, d in choix:
            if sz <= 8 << 20: z.writestr(f'{court}_{e:05d}.bin', d)
    print('conteneurs.zip cree dans', ICI, '- envoie-le-moi.')



def bilan():
    """taille du dossier SW2HD par categorie (+ compression estimee) ; ecrit categories.tsv (pour le paquet Nexus)"""
    import zlib
    man = lire_manifeste()
    print('calcul des empreintes des images d origine (francaises et anglaises)...', flush=True)
    crcs = crc_par_cle(lambda i: i['fmt'] in D3D_FMT)
    cat_de = {}
    for cle, crc in crcs.items(): cat_de.setdefault(crc, man[cle]['cat'])
    dest = dossier_hd()
    par = {}
    for f in sorted(os.listdir(dest)):
        if not f.endswith('.sw2h'): continue
        c = cat_de.get(int(f[:8], 16), 'inconnu')
        par.setdefault(c, []).append(f)
    with open(os.path.join(ICI, 'categories.tsv'), 'w') as o:
        for c, fs in sorted(par.items()):
            for f in fs: o.write(f[:8] + '\t' + c + '\n')
    print(f"{'categorie':<14}{'images':>8}{'Mo':>8}{'Mo zip (estim.)':>17}")
    tb = tz = 0
    for c, fs in sorted(par.items()):
        b = sum(os.path.getsize(os.path.join(dest, f)) for f in fs)
        ech = fs[::max(1, len(fs) // 60)]
        eb = ez = 0
        for f in ech:
            d = open(os.path.join(dest, f), 'rb').read(); eb += len(d); ez += len(zlib.compress(d, 6))
        z = int(b * ez / eb) if eb else 0
        tb += b; tz += z
        print(f'{c:<14}{len(fs):>8}{b // 1048576:>8}{z // 1048576:>17}', flush=True)
    print(f"{'TOTAL':<14}{sum(len(x) for x in par.values()):>8}{tb // 1048576:>8}{tz // 1048576:>17}")
    print('Liste ecrite :', os.path.join(ICI, 'categories.tsv'))

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'injecter' and len(sys.argv) > 2: injecter(sys.argv[2])
    elif cmd == 'extraire_us': extraire_us()
    elif cmd == 'module' and len(sys.argv) > 2: module(sys.argv[2])
    elif cmd == 'copier' and len(sys.argv) > 3: copier(sys.argv[2], sys.argv[3])
    else: {'extraire': extraire, 'restaurer': restaurer, 'conteneurs': conteneurs, 'empreintes': empreintes, 'echantillon2': echantillon2, 'bilan': bilan}.get(cmd, lambda: print(__doc__))()
