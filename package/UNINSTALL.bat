@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Samurai Warriors 2 - HD Textures : uninstall

set "MOD=%~dp0"
set "MOD=%MOD:~0,-1%"
for %%i in ("%MOD%\..") do set "JEU=%%~fi"
if not exist "%JEU%\sw2.exe" for %%i in ("%MOD%\..\..") do if exist "%%~fi\sw2.exe" set "JEU=%%~fi"
set "TEX=%MOD%\textures\Textures_HD"

echo.
echo  ============================================================
echo    Samurai Warriors 2 (PC) - HD Textures : uninstall / désinstallation
echo  ============================================================
echo.
if not exist "%JEU%\sw2.exe" goto :err_dossier
echo  Game folder / Dossier du jeu : %JEU%
echo  Close the game before going on. / Fermez le jeu avant de continuer.
echo.

echo  [1/3] Game module / Module du jeu
del /f /q "%JEU%\SW2HD.asi" >nul 2>&1
if exist "%JEU%\SW2HD.asi" goto :err_occupe
del /f /q "%JEU%\SW2HD.ini" "%JEU%\SW2HD.log" >nul 2>&1
echo    OK

echo  [2/3] HD textures / Textures HD
if exist "%JEU%\Textures_HD" (
  if exist "%TEX%\index.bin" (
    rd /s /q "%JEU%\Textures_HD" 2>nul
  ) else (
    if not exist "%MOD%\textures" mkdir "%MOD%\textures"
    rem kept in the mod folder so INSTALL.bat can put them back without downloading again
    move "%JEU%\Textures_HD" "%TEX%" >nul 2>&1
  )
  if exist "%JEU%\Textures_HD" goto :err_occupe
)
echo    OK

echo  [3/3] ASI loader / Chargeur ASI
if exist "%MOD%\files\dinput8_installed.txt" (
  if exist "%JEU%\*.asi" (
    echo    dinput8.dll kept: other mods use it / conservé : d'autres mods l'utilisent
  ) else (
    del /f /q "%JEU%\dinput8.dll" >nul 2>&1
    del /f /q "%MOD%\files\dinput8_installed.txt" >nul 2>&1
    echo    dinput8.dll removed / supprimé
  )
) else (
  echo    dinput8.dll was not installed by this mod, kept / non installé par ce mod, conservé
)

echo.
echo  Uninstall complete. / Désinstallation terminée.
echo  The HD textures are kept in SW2_HD_Textures\textures: delete the
echo  SW2_HD_Textures folder to free the disk space, or run INSTALL.bat to
echo  reinstall. / Les textures HD restent dans SW2_HD_Textures\textures :
echo  supprimez le dossier SW2_HD_Textures pour libérer la place, ou relancez
echo  INSTALL.bat pour réinstaller.
goto :fin

:err_dossier
echo  [ERROR / ERREUR] sw2.exe not found in / introuvable dans :
echo    %JEU%
goto :fin

:err_occupe
echo  [ERROR / ERREUR] A file is in use: close the game (and any window open on
echo  the Textures_HD folder), then run UNINSTALL.bat again.
echo  Un fichier est utilisé : fermez le jeu (et toute fenêtre ouverte sur le
echo  dossier Textures_HD), puis relancez UNINSTALL.bat.
goto :fin

:fin
echo.
pause
endlocal
