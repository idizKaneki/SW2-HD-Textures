/* SW2HD.asi 2.0.3 - Samurai Warriors 2 (PC) : textures HD remplacees a la volee (decors, personnages, menus...).
 * Le jeu charge ses images d'origine et calcule ses decoupages normalement ; au moment de
 * l'affichage, ce module donne a Direct3D la version HD (meme image, 2 fois plus fine).
 * Les images HD sont dans le dossier Textures_HD\ du jeu (ancien nom : SW2HD\) : <crc32>.sw2h (crc32 = empreinte des pixels
 * d'origine). Une image dont l'original a change (mise a jour d'un autre mod) n'est simplement
 * pas remplacee.
 * Journal : SW2HD.log ; reglages : SW2HD.ini [Settings] :
 *   Enable=1          0 = module desactive
 *   Log=1             journal SW2HD.log
 *   VideoMemory=1     images HD en memoire video (ne pese pas sur la memoire du jeu)
 *   Mipmaps=1         filtrage des versions reduites (moins de scintillement de loin)
 * 2.0.3 : F11 coupe / remet les textures HD en jeu (comparaison).
 * 2.0.2 : dossier des images renomme Textures_HD (SW2HD toujours lu).
 * 2.0.1 : accroche fiable meme quand le jeu cree Direct3D tres tot (lancement direct).
 * 2.0 : toutes les textures, chaines de mipmaps, memoire video, rechargement apres Reset.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
typedef unsigned char u8; typedef unsigned int u32;
#define VTBL(o) (*(void***)(o))

static char g_dir[260], g_logp[260], g_ini[260];
static char g_log[8192]; static int g_loglen, g_dolog = 1;
static CRITICAL_SECTION g_cs;
static void flushlog(void) {
    DWORD w; HANDLE h;
    if (!g_dolog || !g_loglen) { g_loglen = 0; return; }
    h = CreateFileA(g_logp, FILE_APPEND_DATA, FILE_SHARE_READ, 0, OPEN_ALWAYS, 0x80, 0);
    if (h != INVALID_HANDLE_VALUE) { WriteFile(h, g_log, g_loglen, &w, 0); CloseHandle(h); }
    g_loglen = 0;
}
static void lg(const char *s) { while (*s) { if (g_loglen >= (int)sizeof g_log - 1) flushlog(); g_log[g_loglen++] = *s++; } }
static void lgn(u32 v) { char b[12]; int i = 11; b[i] = 0; if (!v) b[--i] = '0'; while (v) { b[--i] = '0' + v % 10; v /= 10; } lg(b + i); }

/* ---------- CRC32 (zlib) ---------- */
static u32 crct[256];
static void crcinit(void) { u32 i, j, c; for (i = 0; i < 256; i++) { c = i; for (j = 0; j < 8; j++) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1; crct[i] = c; } }
static u32 crcrun(u32 c, const u8 *p, u32 n) { while (n--) c = crct[(c ^ *p++) & 255] ^ (c >> 8); return c; }
static int isdxt(u32 f) { return (f & 0xFFFFFF) == 0x545844; }
static u32 rowbytes(u32 fmt, u32 w) {
    if (fmt == 0x31545844) return ((w + 3) / 4) * 8;
    if (fmt == 0x33545844 || fmt == 0x35545844) return ((w + 3) / 4) * 16;
    if (fmt == 21 || fmt == 22) return w * 4;
    return 0;
}
static u32 nrows(u32 fmt, u32 h) { return isdxt(fmt) ? (h + 3) / 4 : h; }

/* ---------- catalogue des images HD : crc -> (w, h, fmt d'origine) ---------- */
typedef struct { u32 crc, w, h, fmt; } HDF;
static HDF *g_hd; static int g_nhd;
static u32 g_dims[256][3]; static int g_ndims;          /* combinaisons (w,h,fmt) presentes */
static int hdfind(u32 crc) { int lo = 0, hi = g_nhd - 1; while (lo <= hi) { int m = (lo + hi) / 2; if (g_hd[m].crc == crc) return m; if (g_hd[m].crc < crc) lo = m + 1; else hi = m - 1; } return -1; }
static int dimsok(u32 w, u32 h, u32 f) { int i; for (i = 0; i < g_ndims; i++) if (g_dims[i][0] == w && g_dims[i][1] == h && g_dims[i][2] == f) return 1; return 0; }
/* index.bin (ecrit par sw2_hd.py) : 'SW2I', nombre, puis (crc, w, h, fmt) tries par crc */
static void catalogue(void) {
    char p[300]; HANDLE f; u32 h[2]; DWORD rd = 0; int i;
    lstrcpyA(p, g_dir); lstrcatA(p, "index.bin");
    f = CreateFileA(p, GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, 0x80, 0);
    if (f == INVALID_HANDLE_VALUE) return;
    if (ReadFile(f, h, 8, &rd, 0) && rd == 8 && h[0] == 0x49325753 && h[1] > 0 && h[1] < 1000000) {
        g_hd = (HDF*)HeapAlloc(GetProcessHeap(), 0, h[1] * sizeof(HDF));
        if (g_hd && ReadFile(f, g_hd, h[1] * sizeof(HDF), &rd, 0) && rd == h[1] * sizeof(HDF)) g_nhd = (int)h[1];
    }
    CloseHandle(f);
    for (i = 0; i < g_nhd; i++) if (!dimsok(g_hd[i].w, g_hd[i].h, g_hd[i].fmt) && g_ndims < 256) {
        g_dims[g_ndims][0] = g_hd[i].w; g_dims[g_ndims][1] = g_hd[i].h; g_dims[g_ndims][2] = g_hd[i].fmt; g_ndims++; }
}

/* ---------- textures du jeu suivies ---------- */
#define NT 32768
#define TOMB ((void*)1)
typedef struct { void *p; u32 w, h, fmt, lv; int idx; void *hd; u8 *bits; int pitch; u32 hdlv; } TX;
static TX g_t[NT];
static int tget(void *p, int create) {
    u32 i = ((u32)p >> 4) & (NT - 1), k; int tomb = -1;
    for (k = 0; k < NT; k++, i = (i + 1) & (NT - 1)) {
        if (g_t[i].p == p) return (int)i;
        if (g_t[i].p == TOMB) { if (tomb < 0) tomb = (int)i; continue; }
        if (!g_t[i].p) {
            if (!create) return -1;
            if (tomb >= 0) i = (u32)tomb;
            ZeroMemory(&g_t[i], sizeof(TX)); g_t[i].p = p; g_t[i].idx = -1; return (int)i;
        }
    }
    return -1;
}

typedef struct { void **vt; void *o; } VO;
#define NV 8
static void *vorig(VO *t, void *obj) { int i; for (i = 0; i < NV; i++) if (t[i].vt == VTBL(obj)) return t[i].o; return 0; }
static void vhook2(void **vt, int idx, void *fn, VO *t) {
    int i; DWORD old;
    for (i = 0; i < NV; i++) if (t[i].vt == vt) return;
    if (vt[idx] == fn) return;
    for (i = 0; i < NV && t[i].vt; i++) ;
    if (i == NV) return;
    VirtualProtect(&vt[idx], 4, 0x40, &old); t[i].o = vt[idx]; t[i].vt = vt; vt[idx] = fn; VirtualProtect(&vt[idx], 4, old, &old);
}
static void *fn2(VO *t, void *obj, int idx) { void *f = vorig(t, obj); return f ? f : VTBL(obj)[idx]; }
static void vhook(void **vt, int idx, void *fn, void **orig) {
    DWORD old; if (vt[idx] == fn) return;
    VirtualProtect(&vt[idx], 4, 0x40, &old); *orig = vt[idx]; vt[idx] = fn; VirtualProtect(&vt[idx], 4, old, &old);
}

typedef int (WINAPI *TLockF)(void*, u32, int*, void*, u32);
typedef int (WINAPI *TUnlockF)(void*, u32);
typedef u32 (WINAPI *RelF)(void*);
typedef int (WINAPI *CTF)(void*, u32, u32, u32, u32, u32, u32, void**, HANDLE*);
typedef int (WINAPI *STF)(void*, u32, void*);
typedef int (WINAPI *CDF)(void*, u32, u32, HANDLE, u32, u32*, void**);
static VO vLock[NV], vUnlock[NV], vRel[NV];
static CTF oCT; static STF oST; static CDF oCD;
static void *g_dev; static DWORD g_inside_tid;
#define INSIDE (g_inside_tid == GetCurrentThreadId())
static u32 g_nrep, g_nload, g_nfail; static int g_vram = 1, g_mips = 1;
typedef int (WINAPI *UTF)(void*, void*, void*);
typedef int (WINAPI *SSSF)(void*, u32, u32, u32);
static SSSF oSSS;

/* charge l'image HD n : renvoie la texture HD (et son nombre de niveaux dans *nlv) */
static void *charger(int n, u32 *nlv) {
    char p[300], nm[16]; HANDLE f; u32 h[12], r, lv, nl, w, hh; DWORD rd; void *sys = 0, *t = 0; int lr[2], ok = 1;
    const char *hx = "0123456789abcdef"; int i;
    for (i = 0; i < 8; i++) nm[i] = hx[(g_hd[n].crc >> (28 - 4 * i)) & 15]; nm[8] = 0;
    lstrcpyA(p, g_dir); lstrcatA(p, nm); lstrcatA(p, ".sw2h");
    f = CreateFileA(p, GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, 0x08000080, 0);   /* SEQUENTIAL_SCAN */
    if (f == INVALID_HANDLE_VALUE) { g_nfail++; return 0; }
    if (!ReadFile(f, h, 32, &rd, 0) || rd != 32 || h[0] != 0x48325753) { CloseHandle(f); g_nfail++; return 0; }
    nl = 1;
    if (h[1] >= 2) { if (!ReadFile(f, h + 8, 16, &rd, 0) || rd != 16) { CloseHandle(f); g_nfail++; return 0; } nl = h[8]; if (nl < 1 || nl > 14) nl = 1; }
    g_inside_tid = GetCurrentThreadId();
    /* 1) texture en memoire systeme, remplie niveau par niveau */
    if (oCT(g_dev, h[5], h[6], nl, 0, h[7], g_vram ? 2 : 1, &sys, 0) != 0) sys = 0;
    if (sys) {
        TLockF lk = (TLockF)fn2(vLock, sys, 19); TUnlockF ul = (TUnlockF)fn2(vUnlock, sys, 20);
        for (lv = 0, w = h[5], hh = h[6]; lv < nl && ok; lv++, w = w > 1 ? w / 2 : 1, hh = hh > 1 ? hh / 2 : 1) {
            u32 rb = rowbytes(h[7], w), nr = nrows(h[7], hh);
            if (!rb || lk(sys, lv, lr, 0, 0) != 0) { ok = 0; break; }
            { u8 *dst = (u8*)(size_t)(u32)lr[1];
              for (r = 0; r < nr && ok; r++) if (!ReadFile(f, dst + r * lr[0], rb, &rd, 0) || rd != rb) ok = 0; }
            ul(sys, lv);
        }
        if (!ok) { ((RelF)fn2(vRel, sys, 2))(sys); sys = 0; }
    }
    /* 2) copie en memoire video (pool DEFAULT) : rien ne reste dans la memoire du jeu */
    if (sys && g_vram) {
        if (oCT(g_dev, h[5], h[6], nl, 0, h[7], 0, &t, 0) == 0 && t) {
            if (((UTF)VTBL(g_dev)[31])(g_dev, sys, t) != 0) { ((RelF)fn2(vRel, t, 2))(t); t = 0; }
        } else t = 0;
        ((RelF)fn2(vRel, sys, 2))(sys);
    } else t = sys;
    g_inside_tid = 0;
    CloseHandle(f);
    if (t) { g_nload++; *nlv = nl; } else g_nfail++;
    return t;
}
static void lacher(void *hd) { if (hd) ((RelF)fn2(vRel, hd, 2))(hd); }

static int WINAPI hLock(void *t, u32 lv, int *lr, void *rc, u32 fl) {
    int r = ((TLockF)vorig(vLock, t))(t, lv, lr, rc, fl);
    if (r == 0 && lv == 0 && lr && !rc && !(fl & 0x10) && !INSIDE) {
        int i; EnterCriticalSection(&g_cs);
        i = tget(t, 0); if (i >= 0) { g_t[i].bits = (u8*)(size_t)(u32)lr[1]; g_t[i].pitch = lr[0]; }
        LeaveCriticalSection(&g_cs);
    }
    return r;
}
static int WINAPI hUnlock(void *t, u32 lv) {
    if (lv == 0 && !INSIDE) {
        int i; EnterCriticalSection(&g_cs);
        i = tget(t, 0);
        if (i >= 0 && g_t[i].bits) {
            TX *x = &g_t[i]; int n = -1;
            if (dimsok(x->w, x->h, x->fmt)) {
                u32 rb = rowbytes(x->fmt, x->w), nr = nrows(x->fmt, x->h), r, c = 0xFFFFFFFFu;
                for (r = 0; r < nr; r++) c = crcrun(c, x->bits + r * x->pitch, rb);
                n = hdfind(c ^ 0xFFFFFFFFu);
            }
            if (n != x->idx && x->hd) { lacher(x->hd); x->hd = 0; }
            x->idx = n; x->bits = 0;
            if (n >= 0 && !x->hd) { x->hd = charger(n, &x->hdlv); if (!x->hd) x->idx = -1; }   /* pendant le chargement du jeu */
        }
        LeaveCriticalSection(&g_cs);
    }
    return ((TUnlockF)vorig(vUnlock, t))(t, lv);
}
static u32 WINAPI hRel(void *t) {
    u32 n = ((RelF)vorig(vRel, t))(t);
    if (n == 0) {
        int i; void *hd = 0; EnterCriticalSection(&g_cs);
        i = tget(t, 0); if (i >= 0) { hd = g_t[i].hd; g_t[i].p = TOMB; g_t[i].hd = 0; }
        LeaveCriticalSection(&g_cs);
        lacher(hd);
    }
    return n;
}
static int WINAPI hCT(void *d, u32 w, u32 h, u32 lv, u32 us, u32 fmt, u32 pool, void **out, HANDLE *sh) {
    int r = oCT(d, w, h, lv, us, fmt, pool, out, sh);
    if (r == 0 && out && *out) {
        vhook2(VTBL(*out), 2, (void*)hRel, vRel);
        vhook2(VTBL(*out), 19, (void*)hLock, vLock);
        vhook2(VTBL(*out), 20, (void*)hUnlock, vUnlock);
        if (!INSIDE) {
            int i; EnterCriticalSection(&g_cs);
            i = tget(*out, 1); if (i >= 0) { g_t[i].w = w; g_t[i].h = h; g_t[i].fmt = fmt; g_t[i].lv = lv ? lv : 99; }
            LeaveCriticalSection(&g_cs);
        }
    }
    return r;
}
/* F10 : note dans SW2HD.log les images HD affichees a l'ecran (pour reperer une image) */
static int g_off;   /* F11 : HD coupee / remise en direct (pour comparer) */
static int g_snap; static u32 g_seen[512]; static int g_nseen;
static void noter(int idx) {
    int k; if (g_nseen >= 512) return;
    for (k = 0; k < g_nseen; k++) if (g_seen[k] == (u32)idx) return;
    g_seen[g_nseen++] = (u32)idx;
}
static int WINAPI hST(void *d, u32 st, void *tex) {
    if (tex && g_nhd && !g_off) {
        int i; void *hd = 0; u32 nl = 1; EnterCriticalSection(&g_cs);
        i = tget(tex, 0);
        if (i >= 0 && g_t[i].idx >= 0 && g_snap) noter(g_t[i].idx);
        if (i >= 0 && g_t[i].idx >= 0) {
            if (!g_t[i].hd) { g_t[i].hd = charger(g_t[i].idx, &g_t[i].hdlv); if (!g_t[i].hd) g_t[i].idx = -1; }
            hd = g_t[i].hd; nl = g_t[i].hdlv;
        }
        LeaveCriticalSection(&g_cs);
        if (hd) {
            g_nrep++;
            if (g_mips && nl > 1 && st < 16 && oSSS) oSSS(d, st, 7, 2);      /* D3DSAMP_MIPFILTER = LINEAR */
            return oST(d, st, hd);
        }
    }
    return oST(d, st, tex);
}
/* le jeu remet parfois MIPFILTER a NONE : avec Mipmaps=1, on garde LINEAR (sans effet sur une texture a 1 niveau) */
static int WINAPI hSSS(void *d, u32 st, u32 type, u32 v) {
    if (g_mips && type == 7 && v == 0) v = 2;
    return oSSS(d, st, type, v);
}
/* Reset (changement de mode, Alt+Tab plein ecran) : les textures en memoire video doivent etre liberees avant */
typedef int (WINAPI *ResetF)(void*, void*);
static ResetF oReset;
static int WINAPI hReset(void *d, void *pp) {
    if (g_vram) {
        int i, n = 0; EnterCriticalSection(&g_cs);
        for (i = 0; i < 8; i++) oST(d, (u32)i, 0);             /* plus aucune image HD liee */
        for (i = 0; i < NT; i++) if (g_t[i].p && g_t[i].p != TOMB && g_t[i].hd) { lacher(g_t[i].hd); g_t[i].hd = 0; n++; }
        lg("Reset : "); lgn((u32)n); lg(" images HD liberees (rechargees a la demande)\r\n"); flushlog();
        LeaveCriticalSection(&g_cs);
    }
    return oReset(d, pp);
}
typedef int (WINAPI *PresentF)(void*, void*, void*, void*, void*);
static PresentF oPresent; static u32 g_frames;
static int g_f10, g_f11;
static int WINAPI hPresent(void *d, void *a, void *b, void *c, void *e) {
    int down = (GetAsyncKeyState(VK_F10) & 0x8000) != 0;
    if (g_snap) {
        int k; const char *hx = "0123456789abcdef";
        EnterCriticalSection(&g_cs);
        lg("--- F10 : images HD a l'ecran ("); lgn((u32)g_nseen); lg(") ---\r\n");
        for (k = 0; k < g_nseen; k++) {
            HDF *h = &g_hd[g_seen[k]]; char b[9]; int j;
            for (j = 0; j < 8; j++) b[j] = hx[(h->crc >> (28 - 4 * j)) & 15]; b[8] = 0;
            lg(b); lg(" "); lgn(h->w); lg("x"); lgn(h->h); lg("\r\n");
        }
        flushlog(); g_snap = 0; g_nseen = 0;
        LeaveCriticalSection(&g_cs);
    }
    if (down && !g_f10) { g_snap = 1; g_nseen = 0; }
    g_f10 = down;
    { int d11 = (GetAsyncKeyState(VK_F11) & 0x8000) != 0;
      if (d11 && !g_f11) { g_off = !g_off; EnterCriticalSection(&g_cs); lg(g_off ? "F11 : textures d'origine\r\n" : "F11 : textures HD\r\n"); flushlog(); LeaveCriticalSection(&g_cs); }
      g_f11 = d11; }
    if (++g_frames == 600 || g_frames % 18000 == 0) {
        EnterCriticalSection(&g_cs);
        lg("images HD chargees : "); lgn(g_nload); lg(" | echecs : "); lgn(g_nfail); lg(" | remplacements : "); lgn(g_nrep); lg("\r\n"); flushlog();
        LeaveCriticalSection(&g_cs);
    }
    return oPresent(d, a, b, c, e);
}
static int WINAPI hCD(void *d3d, u32 ad, u32 ty, HANDLE w, u32 fl, u32 *pp, void **out) {
    int r = oCD(d3d, ad, ty, w, fl, pp, out);
    if (r == 0 && out && *out) {
        void **vt = VTBL(*out); g_dev = *out;
        vhook(vt, 17, (void*)hPresent, (void**)&oPresent);
        vhook(vt, 23, (void*)hCT, (void**)&oCT);
        vhook(vt, 65, (void*)hST, (void**)&oST);
        vhook(vt, 69, (void*)hSSS, (void**)&oSSS);
        vhook(vt, 16, (void*)hReset, (void**)&oReset);
        lg("Direct3D pret\r\n"); flushlog();
    }
    return r;
}

/* Accroche sur Direct3DCreate9 lui-meme (dans d3d9.dll) : le jeu passe forcement par la, meme s'il
 * cree son Direct3D tres tot (lancement direct, sans Steam). Avant 2.0.1, seul le "secours" ci-dessous
 * existait : si le jeu creait son Direct3D avant lui, le module restait inactif. */
typedef void *(WINAPI *C9)(u32);
static C9 oC9; static volatile LONG g_c9;
static void *WINAPI hC9(u32 v) {
    void *d = oC9(v);
    if (d) vhook(VTBL(d), 16, (void*)hCD, (void**)&oCD);
    return d;
}
static int accrocher_c9(HMODULE m) {
    u8 *p, *t; DWORD old; int i;
    if (!m || InterlockedCompareExchange(&g_c9, 1, 0) != 0) return 0;   /* deja fait (ou tente) */
    p = (u8*)GetProcAddress(m, "Direct3DCreate9");
    t = p ? (u8*)VirtualAlloc(0, 16, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE) : 0;
    if (!t) { g_c9 = 3; return 0; }
    if (p[0] == 0xE9) {                                            /* deja detourne (overlay...) : on suit */
        u32 dst = (u32)p + 5 + *(int*)(p + 1);
        t[0] = 0xE9; *(int*)(t + 1) = (int)(dst - ((u32)t + 5));
    } else if (p[0] == 0x8B && p[1] == 0xFF && p[2] == 0x55 && p[3] == 0x8B && p[4] == 0xEC) {
        for (i = 0; i < 5; i++) t[i] = p[i];                       /* mov edi,edi ; push ebp ; mov ebp,esp */
        t[5] = 0xE9; *(int*)(t + 6) = (int)(((u32)p + 5) - ((u32)t + 10));
    } else { VirtualFree(t, 0, MEM_RELEASE); g_c9 = 3; return 0; }
    oC9 = (C9)t;
    VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &old);
    p[0] = 0xE9; *(int*)(p + 1) = (int)((u32)hC9 - ((u32)p + 5));
    VirtualProtect(p, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), p, 5);
    g_c9 = 2; return 1;
}

static DWORD WINAPI worker(LPVOID a) {
    HMODULE m; C9 c; void *d3d; (void)a;
    m = LoadLibraryA("d3d9.dll");
    if (accrocher_c9(m)) { lg("accroche : Direct3DCreate9 (thread)\r\n"); flushlog(); }
    /* secours : notre propre Direct3D, pour accrocher CreateDevice si le jeu a deja appele Direct3DCreate9 */
    c = m ? (C9)GetProcAddress(m, "Direct3DCreate9") : 0;
    d3d = c ? c(32) : 0;
    if (d3d) vhook(VTBL(d3d), 16, (void*)hCD, (void**)&oCD); else lg("ERREUR : d3d9 introuvable\r\n");
    flushlog();
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID res) {
    (void)res;
    if (reason == DLL_PROCESS_ATTACH) {
        int i, n, k;
        DisableThreadLibraryCalls(inst);
        InitializeCriticalSection(&g_cs); crcinit();
        n = (int)GetModuleFileNameA(inst, g_dir, 200);
        for (i = n; i > 0 && g_dir[i-1] != '\\' && g_dir[i-1] != '/'; i--) {}
        g_dir[i] = 0;
        lstrcpyA(g_ini, g_dir); lstrcatA(g_ini, "SW2HD.ini");
        lstrcpyA(g_logp, g_dir); lstrcatA(g_logp, "SW2HD.log");
        {   /* dossier des images : Textures_HD (2.0.2), sinon l'ancien nom SW2HD */
            char t[300]; lstrcpyA(t, g_dir); lstrcatA(t, "Textures_HD\\index.bin");
            lstrcatA(g_dir, GetFileAttributesA(t) != INVALID_FILE_ATTRIBUTES ? "Textures_HD\\" : "SW2HD\\");
        }
        g_dolog = (int)GetPrivateProfileIntA("Settings", "Log", 1, g_ini);
        g_vram = (int)GetPrivateProfileIntA("Settings", "VideoMemory", 1, g_ini);
        g_mips = (int)GetPrivateProfileIntA("Settings", "Mipmaps", 1, g_ini);
        DeleteFileA(g_logp);
        if (!GetPrivateProfileIntA("Settings", "Enable", 1, g_ini)) { lg("SW2HD desactive (SW2HD.ini)\r\n"); flushlog(); return 1; }
        catalogue();
        lg("SW2HD 2.0.3 : "); lgn((u32)g_nhd); lg(" images HD dans "); lg(g_dir);
        lg(g_vram ? " | memoire video" : " | memoire du jeu"); lg(g_mips ? " | mipmaps\r\n" : "\r\n");
        if (!g_nhd) { lg("aucune image : module inactif\r\n"); flushlog(); return 1; }
        if (accrocher_c9(GetModuleHandleA("d3d9.dll"))) lg("accroche : Direct3DCreate9\r\n");
        flushlog();
        CreateThread(0, 0, worker, 0, 0, 0);
        (void)k;
    } else if (reason == DLL_PROCESS_DETACH) {
        flushlog();
    }
    return 1;
}
