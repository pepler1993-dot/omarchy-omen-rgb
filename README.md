# OMEN Tastaturfarben für Omarchy

Ein lokales Omarchy-Panel für vier RGB-Zonen: Farbpalette, eigene Hex-Farben,
Einzelfarben pro Zone, Warmweiß, vier statische Farbvorlagen und RGB-basierte Helligkeit.
Die vierte Zone ist WASD; dies wurde am lokalen Laptop visuell bestätigt.
Die übrigen Bereiche heißen Zone 1–3.
Es gibt keine Animationen und keine Steuerung einzelner Tasten.

## Aktueller Stand

Das Panel und der Zusatztreiber sind dauerhaft installiert. Der Treiber ist auf
HP-Board `8C77` mit Linux 7.1.9-arch1-2 getestet. Alle vier Farben konnten
ausgelesen, geändert und wiederhergestellt werden. Das Panel hat Schreibzugriff.
Neun Python-Tests und die Omarchy-Manifestvalidierung sind bestanden.

DKMS baut das Modul bei Kernelupdates automatisch neu. Der Treiber wird beim
Systemstart geladen; der aktivierte Dienst `omen-rgb-restore.service` stellt
anschließend das zuletzt gespeicherte Profil als Benutzer Kevin wieder her.
Neuladen der installierten Treiberversion und Wiederherstellung durch den Dienst
wurden erfolgreich geprüft. Ein vollständiger Neustart des Laptops wurde nicht
für den Test durchgeführt. Das gespeicherte Profil kann jederzeit im Panel geändert werden.

## Bedienung

Tastatursymbol in der oberen Leiste anklicken. „Alle“ oder eine Zone auswählen,
Farbe anklicken bzw. Hex-Code eingeben und „Auswählen“ drücken. Vorlagen setzen
alle vier Zonen. Erst „Anwenden & speichern“ schreibt die Farben und speichert das
Profil in `~/.local/state/omen-rgb/colors.json`. Ohne Treiber bleibt dieser Knopf
gesperrt. „Neu einlesen“ verwirft die Vorschau und liest den Hardwarezustand ein.
Fn+F4 bleibt die vorhandene hardwareseitige Ein-/Aus-Steuerung.

„Gaming RGB“ steht bei den anderen Farbvorlagen und wählt für die vier Zonen `00E5FF`, `8000FF`,
`FF00CC`, `FF8000` und setzt die Helligkeit auf 100 %. Cyan, Violett und Pink
geben den großen Bereichen einen kräftigen RGB-Look. WASD hebt sich in Orange
ab. Alle Farben werden ohne Dimmung ausgegeben.
Die [OMEN-Zonenbelegung von omenctl](https://github.com/SwarritSrivastava/omenctl#zone-map)
ordnet die vierte Zone (Treiberindex 3) den WASD-Tasten zu; der Benutzer hat
diese Zuordnung am lokalen Laptop bestätigt.
Die Vorlage wird zunächst nur
in der Vorschau angezeigt; „Anwenden & speichern“ übernimmt sie. WASD kann als
gemeinsame Zone hervorgehoben werden; die vier Tasten erhalten dieselbe Farbe.
Eine freie Farbwahl für jede einzelne Taste wird vom Treiber nicht angeboten.

„Helligkeit“ skaliert RGB-Komponenten; es ist kein nachgewiesener Hardware-Dimmer.
Beim Absenken auf null bleiben die Ausgangsfarben im gespeicherten Profil erhalten.
Das gespeicherte Profil wird beim Systemstart automatisch wiederhergestellt.

## Installation des Panels (ohne Treiber)

```sh
python3 install-panel.py
```

Das Skript kopiert nur die vier UI-/Adapter-Dateien nach
`~/.config/omarchy/plugins/kevin.omen-rgb/` und fügt das Widget zur Leiste hinzu.
Vor einer Änderung an `shell.json` wird eine datierte Sicherung erstellt.

## Hardwaretest und dauerhafte Einrichtung

Der ursprüngliche Test schrieb `800000 008000 000080 808080`, las diese Werte
zurück und stellte anschließend `0F84FA 710FFA F9350F FAAC0F` wieder her.
Die ursprünglichen Farben sind in `original-colors.json` gesichert.
Das danach vom Benutzer gewählte weiße Profil wurde beim Installationstest
korrekt wiederhergestellt.

Installierte Bestandteile:

- DKMS-Quellcode unter `/usr/src/kevin-omen-rgb-0.4`.
- Installiertes Modul unter `/usr/lib/modules/7.1.9-arch1-2/updates/dkms/omen_rgb.ko.zst`.
- Automatisches Laden über `/etc/modules-load.d/kevin-omen-rgb.conf`.
- `/etc/systemd/system/omen-rgb-restore.service`, aktiviert für `multi-user.target`.

Der Dienst setzt ausschließlich die Eigentümerschaft der einen RGB-Datei auf
`kevin` und stellt danach als Benutzer Kevin das gespeicherte Profil wieder her.
Vorhandene HP-Treiber werden nicht ersetzt. Das Panel lädt selbst keine Treiber
und startet keine privilegierten Prozesse.

`install-driver.py` enthält die ausgeführte Installation. `verify-installation.py`
prüft das Neuladen, einen Farbwechsel und die Wiederherstellung durch den Dienst.
Diese Skripte benötigen Rootrechte. Die Alltagsbedienung benötigt keine.

Bei manueller Entladung und erneutem Laden des Moduls muss der Dienst mit
`sudo systemctl restart omen-rgb-restore.service` erneut laufen, um Schreibrechte
und gespeicherte Farben wiederherzustellen. Beim normalen Systemstart geschieht
das automatisch.

## Entwicklung und Prüfung

```sh
make -C driver
python3 -m unittest -v
omarchy plugin validate .
python3 rgb.py status
```

`rgb.py` verwendet ausschließlich die vier Farben über die feste sysfs-Datei
`/sys/devices/platform/omen_rgb/rgb_zones/colors`. Alle vier Zonen werden in einer
Firmware-Transaktion geschrieben. Nur nach bestätigtem Rücklesen wird das Profil
atomar gespeichert. Ungültige Eingaben werden vor jedem Hardwarezugriff abgelehnt.

## Treiberherkunft und Anpassungen

Referenz: [Alez22/omenkey](https://github.com/Alez22/omenkey), `omen_rgb.c`,
abgerufen am 2026-09-05 (unveränderte Referenz in `vendor/`). Protokollursprung:
[pelrun/hp-omen-linux-module](https://github.com/pelrun/hp-omen-linux-module).
Die Referenz nennt das Board 8BA9 als getestet; der lokale Farbtest auf Board
8C77 war am 2026-09-05 ebenfalls erfolgreich. [OmenLinux](https://github.com/OmenLinux/omen-rgb-keyboard)
nennt die Baureihe 16-wf1xxx als getestet, verwendet aber einen anderen Treiber.

Lokale Änderungen: nullinitialisierte Anfragepuffer, Prüfung von ACPI-Status,
Antworttyp und Antwortlänge, Ablehnung verkürzter Farbzustände, Board-Begrenzung
auf 8C77, Weglassen der unbestätigten Helligkeitsbefehle und ein gemeinsames
`colors`-Attribut für atomare Vier-Zonen-Updates. Die vorhandenen `hp_wmi`- und
`hp_bioscfg`-Module werden nicht ersetzt. Der Farbtest lief mit beiden bestehenden Modulen geladen erfolgreich; ein
Langzeittest liegt nicht vor.

## Entfernen

Zuerst in einem Terminal den Wiederherstellungsdienst und Treiber entfernen:

```sh
sudo systemctl disable --now omen-rgb-restore.service
sudo rm /etc/systemd/system/omen-rgb-restore.service
sudo rm /etc/modules-load.d/kevin-omen-rgb.conf
sudo systemctl daemon-reload
sudo modprobe -r omen_rgb
sudo dkms remove -m kevin-omen-rgb -v 0.4 --all
```

Danach das Panel entfernen:

```sh
omarchy plugin remove kevin.omen-rgb --yes
```

Quellcode unter `/usr/src/kevin-omen-rgb-0.4` und im Work-Verzeichnis sowie das
Farbprofil unter `~/.local/state/omen-rgb/colors.json` bleiben dabei erhalten.

Lizenz: GPL-2.0-only, siehe `LICENSE`. Der Referenztreiber trägt denselben SPDX-Hinweis.
