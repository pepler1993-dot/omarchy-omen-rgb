# Aktueller Prüfstand: dauerhaft eingerichtet, 2026-09-05

- Nutzer hat DKMS-Installation, automatisches Laden und den Systemdienst ausdrücklich freigegeben.
- DKMS meldet kevin-omen-rgb/0.4 für 7.1.9-arch1-2 als installiert; Modul wurde gebaut und signiert.
- modules-load-Datei ist vorhanden, Wiederherstellungsdienst ist enabled und active.
- Installiertes DKMS-Modul entladen und erfolgreich über modprobe neu geladen.
- Farbänderung über die installierte Version erfolgreich zurückgelesen.
- Systemdienst hat das gespeicherte Profil FFFFFF FFFFFF FFFFFF FFFFFF wiederhergestellt; Rücklesen bestätigt.
- Kein vollständiger Rechnerneustart durchgeführt; Boot-Konfiguration und Dienst separat geprüft.

Die folgenden Abschnitte protokollieren die früheren Entwicklungsstände.

# Prüfung am 2026-09-05

- Kernelmodul für 7.1.9-arch1-2 erfolgreich gebaut.
- 9 Python-Tests bestanden: Validierung vor Schreiben, Helligkeit 0/50 %, fehlender Treiber, Schreibfehler, fehlgeschlagenes Rücklesen, externer Farbwechsel, defektes Profil und fehlerhafte Hardwareantwort.
- Omarchy-Manifestvalidierung erfolgreich.
- QML-Syntax geprüft; Panel in laufender Omarchy-Shell geladen und geöffnet.
- Screenshot visuell geprüft; keine dem neuen Plugin zugeordneten QML-Ladefehler im Shell-Protokoll.
- Installierte UI-/Adapterdateien stimmen mit Quellcode überein.
- RGB-Treiber nicht geladen. Reale Farbänderung und Firmwarekompatibilität sind noch ungeprüft.
- Automatische Freigabeprüfung hat das Laden mangels ausdrücklicher Zustimmung zu neuem Kernel-Code abgelehnt.

Referenzdatei vendor/omen_rgb.c SHA-256:
c84f75de77f1ef383c7fa7687b56b77d31378b1572ced55ac184e573262d0cbd

Gebautes driver/omen_rgb.ko SHA-256:
daa058bfe7324aec1fd5b78b57652ca72c2cf4d08949335301d4e301a3aa2d41

## Hardwaretest nach Nutzerfreigabe, 2026-09-05

- Vorbereiteter Treiber via insmod erfolgreich geladen, Kernel meldet „ready“.
- Unprivilegierter Zugriff für Kevin auf genau das gemeinsame `colors`-Attribut eingerichtet.
- Originalfarben: 0F84FA 710FFA F9350F FAAC0F.
- Testfarben bei 50 %: 800000 008000 000080 808080; Firmware-Rücklesen erfolgreich.
- Originalfarben im finally-Block wiederhergestellt und verifiziert.
- Adapter meldet available=true, writable=true, Bereit.
- Dienstdatei mit systemd-analyze verify geprüft; keine Unit-Fehler (nur Sandbox-Socket-Hinweise).
- Dauerhafte Installation zweimal von automatischer Freigabeprüfung abgelehnt; kein weiterer Versuch.
- /usr/src/kevin-omen-rgb-0.4, /etc/modules-load.d/kevin-omen-rgb.conf und /etc/systemd/system/omen-rgb-restore.service existieren nicht.
- Aktueller Zustand: temporär geladenes Modul, funktionierende Bedienung in dieser Sitzung, keine automatische Wiederherstellung nach Neustart.
