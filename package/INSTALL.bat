@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Samurai Warriors 2 - HD Textures : install

set "MOD=%~dp0"
set "MOD=%MOD:~0,-1%"
for %%i in ("%MOD%\..") do set "JEU=%%~fi"
rem archive extracted with an extra folder level (Windows "Extract all"): look one level higher
if not exist "%JEU%\sw2.exe" for %%i in ("%MOD%\..\..") do if exist "%%~fi\sw2.exe" set "JEU=%%~fi"
set "TEX=%MOD%\textures\Textures_HD"

echo.
echo  ============================================================
echo    Samurai Warriors 2 (PC) - HD Textures / Textures HD
echo  ============================================================
echo.

if not exist "%JEU%\sw2.exe" goto :err_dossier
if not exist "%MOD%\files\SW2HD.asi" goto :err_fichiers
if not exist "%MOD%\files\dinput8.dll" goto :err_fichiers
(echo test> "%JEU%\_sw2hd_test.tmp") 2>nul || goto :err_droits
del "%JEU%\_sw2hd_test.tmp" >nul 2>&1

echo  Game folder / Dossier du jeu : %JEU%
echo  Close the game before going on. / Fermez le jeu avant de continuer.
echo.

echo  [1/3] HD textures / Textures HD
set "NB=?"
if exist "%MOD%\textures\count.txt" set /p NB=<"%MOD%\textures\count.txt"
set "TROUVE=0"
if exist "%TEX%" for /f %%n in ('dir /b /a-d "%TEX%\*.sw2h" 2^>nul ^| find /c /v ""') do set "TROUVE=%%n"
if not exist "%TEX%\index.bin" goto :tex_absent
if not "%TROUVE%"=="%NB%" goto :err_incomplet
if exist "%JEU%\Textures_HD" (
  echo    removing the previous version / suppression de l'ancienne version...
  rd /s /q "%JEU%\Textures_HD" 2>nul
  if exist "%JEU%\Textures_HD" goto :err_occupe
)
move "%TEX%" "%JEU%\Textures_HD" >nul 2>&1
if not exist "%JEU%\Textures_HD\index.bin" goto :err_occupe
echo    OK (%TROUVE% textures)
goto :etape2
:tex_absent
if exist "%TEX%" goto :err_incomplet
if not exist "%JEU%\Textures_HD\index.bin" goto :err_textures
echo    already in place / déjà en place
:etape2

echo  [2/3] Game module / Module du jeu
copy /y "%MOD%\files\SW2HD.asi" "%JEU%\SW2HD.asi" >nul || goto :err_occupe
if not exist "%JEU%\SW2HD.ini" copy /y "%MOD%\files\SW2HD.ini" "%JEU%\SW2HD.ini" >nul
echo    SW2HD.asi + SW2HD.ini OK

echo  [3/3] ASI loader / Chargeur ASI
if exist "%JEU%\dinput8.dll" (
  echo    dinput8.dll already present ^(another mod^), kept / déjà présent ^(autre mod^), conservé
) else (
  copy /y "%MOD%\files\dinput8.dll" "%JEU%\dinput8.dll" >nul || goto :err_occupe
  echo dinput8.dll installed by SW2_HD_Textures> "%MOD%\files\dinput8_installed.txt"
  echo    dinput8.dll ^(Ultimate ASI Loader^) installed / installé
)

echo.
echo  Install complete. Enjoy! / Installation terminée. Bon jeu !
echo  To check that it works: after playing, SW2HD.log in the game folder
echo  should say "Direct3D pret". / Pour vérifier : après une partie, SW2HD.log
echo  dans le dossier du jeu doit contenir "Direct3D pret".
echo  To remove / Pour désinstaller : UNINSTALL.bat
goto :fin

:err_dossier
echo  [ERROR / ERREUR] sw2.exe not found in / introuvable dans :
echo    %JEU%
echo  The SW2_HD_Textures folder must be inside the game folder, next to sw2.exe.
echo  Le dossier SW2_HD_Textures doit être dans le dossier du jeu, à côté de sw2.exe.
goto :fin

:err_fichiers
echo  [ERROR / ERREUR] Mod files are missing: extract the "Plugin" archive again.
echo  Des fichiers du mod sont manquants : ré-extrayez l'archive "Plugin".
goto :fin

:err_textures
echo  [ERROR / ERREUR] The HD textures are missing (SW2_HD_Textures\textures\Textures_HD).
echo  Download BOTH files from Nexus (Plugin and Textures), extract them into the
echo  game folder, then run INSTALL.bat again.
echo  Les textures HD manquent (SW2_HD_Textures\textures\Textures_HD).
echo  Téléchargez les DEUX fichiers sur Nexus (Plugin et Textures), extrayez-les
echo  dans le dossier du jeu, puis relancez INSTALL.bat.
goto :fin

:err_incomplet
echo  [ERROR / ERREUR] The archive is not fully extracted: %TROUVE% textures out of %NB%.
echo  Wait until the extraction is finished (or extract the archive again),
echo  then run INSTALL.bat again. Nothing was changed.
echo  L'archive n'est pas entièrement extraite : %TROUVE% textures sur %NB%.
echo  Attendez la fin de l'extraction (ou ré-extrayez l'archive), puis relancez
echo  INSTALL.bat. Rien n'a été modifié.
goto :fin

:err_droits
echo  [ERROR / ERREUR] Cannot write to the game folder.
echo  Right-click INSTALL.bat, then "Run as administrator".
echo  Impossible d'écrire dans le dossier du jeu.
echo  Clic droit sur INSTALL.bat, puis "Exécuter en tant qu'administrateur".
goto :fin

:err_occupe
echo  [ERROR / ERREUR] A file is in use: close the game (and any window open on
echo  the Textures_HD folder), then run INSTALL.bat again.
echo  Un fichier est utilisé : fermez le jeu (et toute fenêtre ouverte sur le
echo  dossier Textures_HD), puis relancez INSTALL.bat.
goto :fin

:fin
echo.
pause
endlocal
