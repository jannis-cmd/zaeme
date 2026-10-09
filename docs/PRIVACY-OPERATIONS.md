# Datenschutzbetrieb für Zäme

Stand: 9. Oktober 2026. Diese Betriebsanleitung ergänzt die öffentlichen Rechtstexte;
sie bestätigt weder eine juristische Freigabe noch einen abgeschlossenen Audit.
Keine Kontoidentitäten, Zugangsdaten, Gesundheitsdaten oder ausgefüllten
Vertretungsnachweise in dieses öffentliche Repository aufnehmen.

## Tatsächlicher Standard

Die öffentliche App verlangt eine Anmeldung. Anonyme Gesprächszugänge,
Sprachnotizen, eigenständige Transkription sowie Classic-/Scribe-/TTS-Pfade sind
öffentlich deaktiviert. Nur der kontrollierte Agents-Relay darf Gespräche führen.
Vor jeder Bucherfassung verlangt der Server die aktuelle Freigabeversion und die
getrennte Annahme der Nutzungsbedingungen. Gastbücher werden nicht automatisch in
Konten importiert. Konten haben keine angesammelte Zeit- oder Personenquote;
600 Sekunden je Gespräch und technische Schutzgrenzen gelten weiterhin.

Echte Profile sind standardmässig gesperrt. Eine Freigabe ist nur möglich, wenn in
der privaten Auth-Konfiguration sämtliche folgenden Voraussetzungen erfüllt sind:

- `privacy.real_profiles_enabled` ist ausdrücklich `true`.
- `privacy.provider_contracts_confirmed` ist ausdrücklich `true`.
- `privacy.risk_review_approved` ist ausdrücklich `true`.
- Für öffentlichen Zugang wird `privacy.real_profiles_access` auf `public` gesetzt.
  Damit sind alle angemeldeten Konten zugelassen, ohne zusätzliche Kontoliste.
  Bei fehlendem Wert gilt `restricted`: Dann muss die konkrete OIDC-Subject-Kennung
  in `privacy.approved_subjects` stehen. Unbekannte Modi sperren den Zugang.

Die Subject-Liste gehört ausschliesslich in die private Konfiguration. Keine
Beispielidentitäten oder echte Freigabedaten committen. Eine technische Freigabe
ist kein Beleg, dass Einwilligung, Vertretung und Eignung im Einzelfall vorliegen.
Eine neue Konfiguration muss in allen betroffenen Prozessen geladen werden;
laufende Gespräche vor einer Einschränkung gezielt beenden, nicht auf einen
bereits laufenden Prozess mit alter Konfiguration vertrauen.

## Vor einer Freigabe echter Profile

1. Verantwortlichkeit und Bearbeitungsinventar dokumentieren: MYNA ist Betreiber
   von Zäme; die Kirchgemeinde betreibt die Hauptwebsite. Die gemeinsame Domain
   teilt einen Browser-Origin. Diesen Zugriffspfad in der Risikoanalyse ausdrücklich
   behandeln; ein Betreiberhinweis schafft keine technische Isolation.
2. Für Hetzner, Infomaniak und ElevenLabs die tatsächlich geltenden Vertragsfassungen,
   Auftragsbearbeitungsregelungen, Unterauftragnehmer, Speicherorte und Transferwege
   privat dokumentieren. Deutschland für die aktuellen App-/Auth-Hosts anhand der
   Hostmetadaten nachvollziehen. Bei einem Standortwechsel neu prüfen.
3. Für ElevenLabs prüfen, dass das Geschäftskonto und die verwendeten Dienste vom
   geltenden DPA erfasst werden. Dessen veröffentlichte SCC-Regelung mit Schweizer
   Anpassungen nicht mit einem pauschalen Nachweis für sämtliche Eigenbearbeitungen
   oder Unterauftragnehmer verwechseln. Geltungsbereich, ergänzende Massnahmen und
   Transferbeurteilung nachvollziehbar dokumentieren. Eine DPF-Zertifizierung nur
   für die tatsächlich zertifizierte Rechtseinheit und den erfassten Bereich
   heranziehen; Nachweis und Prüfdatum privat ablegen.
   Zusätzlich die [ElevenAgents-Bedingungen](https://elevenlabs.io/agents-terms)
   prüfen: Ziff. 2.E verlangt für sensible Daten mit erhöhten Schutzanforderungen
   eine ausdrückliche schriftliche Anbieterzusage. Ziff. 4.A stellt Anforderungen
   an den Endnutzervertrag. Die bedingte mindestens fünfjährige Nachweisfrist in
   4.B gegenüber der aktuellen 90-Tage-Bereinigung klären; ohne Prüfung weder
   vollständige Vertragserfüllung noch die pauschale Pflicht zum Speichern von
   Gesprächsinhalten über fünf Jahre behaupten. Nach 7.D ist der BYO-Anbieter
   kein automatischer Unterauftragnehmer von ElevenLabs. Die OEM-Anwendbarkeit
   und Tarifberechtigung für unsere öffentliche Agents-App gesondert bestätigen.
4. Einstellungen über API/Dashboard prüfen: beide Agenten ohne Audioaufzeichnung,
   `retention_days=1`, `delete_transcript_and_pii=true`, `delete_audio=true`.
   `apply_to_existing_conversations=false` schützt nicht vor alten Aufbewahrungen:
   vorhandene Altbestände separat inventarisieren und bereinigen. Kein Zero
   Retention behaupten. Mit einem synthetischen Test die konkrete Anbieter-
   Löschplanung prüfen und später die Ausführung nachvollziehen.
5. Trainingsabwahl prüfen und Nachweis privat ablegen. Betreiberbestätigung vom
   9. Oktober 2026: neue Eingaben wurden über ElevenLabs → Terms and privacy →
   Data use von der Modellverbesserung abgewählt. Das ist keine unabhängige Prüfung,
   wirkt nicht rückwirkend und ersetzt keine Prüfung weiterer Eigenbearbeitungen.
   Änderungen des Kontos oder Tarifs erfordern eine erneute Kontrolle.
6. Risiko-Vorprüfung dokumentieren. Vulnerable Personen, mögliche Gesundheitsdaten,
   KI-Personalisierung, Auslandsverarbeitung und unverschlüsselte lokale Bücher
   gemeinsam bewerten. Bei potenziell hohem Risiko eine DSFA nach Art. 22 DSG
   erstellen; bei weiterhin hohem Restrisiko die Voraussetzungen von Art. 23 DSG
   und einer Konsultation beachten. Schutzmassnahmen, Restrisiko, Entscheidung,
   verantwortliche Person und Datum festhalten. Eine Selbstdeklaration in der
   Oberfläche erledigt diese Prüfung nicht.
7. Verständliche Aufklärung und freiwillige Entscheidung für alle tatsächlichen
   Gesprächsteilnehmenden sicherstellen. Urteilsfähigkeit ist situationsbezogen;
   Angehörigenstatus ist keine Vertretungsbefugnis. Eine Vollmacht/Beistandschaft
   muss diese Entscheidung umfassen. Keine pauschale «Vertretung durch Familie»
   annehmen. Rechtliche Zweifelsfälle vor Nutzung fachlich klären; keine
   Identitäts-/Gesundheitsunterlagen in Buchtexte oder öffentliche Tickets kopieren.
8. Erst nach dokumentierter Entscheidung für den öffentlichen Zielbetrieb den
   Modus `public` setzen und die öffentlichen Rechtstexte auf diesen Betrieb
   aktualisieren. Die Konfigurationsflags dokumentieren eine Entscheidung; sie
   ersetzen keine Vertragsnachweise oder Risikoprüfung. Ablehnung, erkennbares Unwohlsein und Stoppwünsche unabhängig
   von einer vorherigen Zustimmung respektieren. Gesundheitsangaben werden nicht
   gezielt abgefragt; unbeabsichtigte sensible Inhalte bleiben in der Risikoanalyse.

## Rechte, Widerruf und Löschung bearbeiten

Anfragen an `info@myna-ai.ch` sicher zuordnen. Nur erforderliche Identitätsnachweise
verlangen, einen geeigneten Übermittlungsweg anbieten und keine Ausweiskopien
vorsorglich sammeln. Die regelmässige DSG-Auskunftsfrist beträgt 30 Tage;
notwendige Verlängerungen begründen und rechtzeitig mitteilen. Auskunft umfasst
auch Anbieterbearbeitungen, soweit MYNA verantwortlich ist, nicht nur den lokalen
Buchexport. Ablehnungen oder Einschränkungen rechtlich begründen.

- Buchwiderruf nach bestätigter Serveranfrage sperrt neue KI-Verarbeitung und
  beendet zugehörige Relay-Gespräche. Bereits abgesandte Modellanfragen können
  nicht zurückgeholt werden; Ergebnisse werden bei Widerruf nicht übernommen.
- Offline vorgemerkte Anfragen sperren zunächst nur den lokalen Client. Bei einer
  Meldung «noch nicht bestätigt» Serverstatus prüfen und dem Nutzer keine
  geräteübergreifende Sperre oder abgeschlossene Löschung bestätigen.
- Eine Buchlöschung entfernt die lokale Kopie nach Serverbestätigung. Andere
  Geräte, Downloads, Exporte und fremde Kopien werden dadurch nicht gelöscht.
- Anbieterzuordnungen enthalten technische Gesprächskennungen und beteiligte
  Buchkennungen. Widerruf eines Gruppenbuchs stellt das gesamte zugehörige
  Gruppengespräch zur Löschung an, nicht bloss einzelne Gesprächszeilen.
- Den Betreiber-Cleanup mit `privacy_admin.py --drain` ausführen; der
  Dienst `zaeme-privacy.service` und `zaeme-privacy.timer` sind für Wiederholungen
  alle fünf Minuten vorgesehen. Die private `ZAEME_AUTH_CONFIG` und die
  Anbieter-Schlüsseldatei müssen im geschützten Dienstkontext bereitstehen. Löschqueue, Versuche, Wiederholungen und
  Anbieterfehler prüfen. Nie unbearbeitete Einträge als gelöscht markieren und
  keine Roh-Antworten mit Gesprächsinhalten in Logs ausgeben. Bei wiederholten
  Fehlern den Anbieter kontaktieren, Verarbeitung ggf. pausieren und Betroffene
  korrekt über den Stand informieren.
- Zufällige Anfrage-Korrelationskennungen werden als Anbieter-`user_id` verwendet,
  ohne reale Kontokennung oder Buchinhalt zu übermitteln. Der Cleanup sucht damit
  auch Gespräche, deren Anbieterkennung wegen eines Verbindungsabbruchs nicht
  beim Relay angekommen ist. `unresolved_requests` prüfen: Eine leere
  Anbieter-Liste beweist wegen möglicher Meldeverzögerung nicht, dass keine
  Verarbeitung stattgefunden hat. Offene Zuordnungen müssen untersucht werden.
- Eine Widerrufsbestätigung bestätigt keine abgeschlossene Anbieter-Löschung.
  Dafür tatsächliche Anbieterantworten/Status prüfen; Sicherheits-, Abrechnungs-
  und gesetzlich gebundene Daten getrennt behandeln.
- `privacy_admin.py --revoke-user OIDC_SUBJECT` sperrt alle zugeordneten Bücher
  und Zäme-Sitzungen des Kontos; die Kennung nur im geschützten Operator-Kontext
  verarbeiten, nicht in öffentlichen Logs. `--export-user OIDC_SUBJECT --output
  ABSOLUTER_PRIVATER_NEUER_PFAD` erzeugt eine private Auskunftsdatei, optional
  mit `--include-conversations` auch Anbieter-Gesprächsdaten. Der Zielpfad darf
  noch nicht existieren. Dateien sicher übermitteln und nach Zweckfortfall löschen;
  lokale Bücher beim Nutzer gesondert einholen. Fehler beim Anbieterexport klären,
  bevor Vollständigkeit bestätigt wird.
- «Überall bei Zäme abmelden» widerruft sämtliche App-Sitzungen des Kontos. Das
  löscht weder das gemeinsame ZITADEL-Konto noch Bücher oder Rechte in weiteren
  MYNA-Anwendungen. Kontolöschung und andere Dienste gesondert koordinieren.
- Browserdaten erst löschen lassen, wenn gewünschter Widerruf und sichere
  Zuordnung erledigt sind. Blosse Browserlöschung erreicht den Server nicht.

## Aufbewahrung und Wiederherstellung

Aktive Freigaben bleiben bis Widerruf gespeichert. Freigabeereignisse und
widerrufene Nachweise werden grundsätzlich nach 90 Tagen bereinigt; widerrufene
Nachweise bleiben bei offenen zugeordneten Anbieter-Löschungen darüber hinaus
erhalten. Gelöschte Anbieterzuordnungen werden nach 90 Tagen bereinigt, offene
Aufträge nicht wegen Zeitablaufs verworfen. Ein Tag alte aktive Anbieterressourcen
werden durch den Cleanup ebenfalls zur Löschung gestellt; dies ergänzt die
Anbieterkonfiguration und ist keine exakte Ein-Tages-Garantie bei Ausfällen.

Die Bereinigung muss tatsächlich regelmässig laufen. `privacy_admin.py --check`
liefert Exitcode 2, wenn seit mehr als 15 Minuten kein erfolgreicher Cleanup
vorliegt, offene Anbieterressourcen älter als 24 Stunden noch auf Löschung
warten oder ungeklärte Zuordnungen älter als 24 Stunden bestehen. Ressourcenalter
meint das Erstellungsdatum, nicht 24 Stunden seit Widerruf. Die zusätzliche
`zaeme-privacy-check.timer` prüft alle fünf Minuten und macht Fehler im
Systemd-Dienststatus sichtbar; sie verschickt selbst keine Benachrichtigungen. Der zusätzliche
`myna-monitor.timer` prüft ihren Dienststatus und verschickt Betriebsalarme.
 `privacy_admin.py --status`, Timer/Exitstatus und
Warteschlangen prüfen, Fehler untersuchen und Betriebsnachweise privat führen. Der zusätzliche `myna-monitor.timer` übernimmt die E-Mail-Alarmierung;
einen zuständigen Menschen und regelmässige Kontrolle des Alarmwegs verbindlich
benennen. Ein Ausfall des gesamten Hosts oder des Mailwegs kann damit nicht
unabhängig erkannt werden.
Rechtstexte anpassen, wenn Code, Zeiten oder tatsächlicher Betrieb abweichen.

Für Zäme läuft `zaeme-backup.timer` täglich um 03:40 UTC mit bis zu 15 Minuten
Zufallsverzögerung. Er sichert die SQLite-Datenbank per Online-Backup, die private
Serverkonfiguration, das technische Budget und Wiederherstellungsinformationen.
Bücher im Browser sind nicht enthalten. Der geschützte Staging-Bereich liegt in
`/run` (auf dem geprüften Host tmpfs). Das Archiv wird mit `age` verschlüsselt;
der private Entschlüsselungsschlüssel bleibt ausserhalb der Server. Verschlüsselte
Archive liegen rootgeschützt unter `/var/backups/zaeme/encrypted`. Nach 14 Tagen
werden sie beim nächsten erfolgreichen täglichen Lauf bereinigt. Alte manuelle
Klartext-Sicherungen wurden erst nach bytegenauer Prüfung ihrer verschlüsselten
Kopie ersetzt.

Die Root-Dienste dürfen keine vom App-Benutzer veränderbaren Programme ausführen:
`deploy/scripts/backup.sh` als root:root 0755 nach `/usr/local/sbin/zaeme-backup`
installieren. `backup_check.py` als root:root 0644 nach
`/usr/local/sbin/myna-backup-check` installieren; Aufruf mit isoliertem `python3 -I`
und Arbeitsverzeichnis `/`. Nur den öffentlichen `age`-Empfänger rootgeschützt in
`/etc/zaeme-backup/recipient.txt` ablegen, im Format `Public key: age1…`.
Pakete aus den offiziellen Betriebssystemquellen verwenden.

`zaeme-backup-check.timer` prüft stündlich: mindestens ein Archiv mit age-Header,
private Dateirechte und letzter Archivzeitpunkt vor höchstens 36 Stunden. Fehler
führen zu Exitcode 2. Diese Metadatenprüfung beweist weder Entschlüsselbarkeit
noch eine unabhängige Kopie. Auf myna-3 prüft `myna-auth-backup-check.timer` die
bestehenden verschlüsselten ZITADEL-Sicherungen nach denselben Kriterien. Die
Dateien `deploy/myna-auth-*` gehören nur auf den Auth-Host, die `zaeme-*`-Units
auf den App-Host.

Am 9.10.2026 wurde ein Zäme-Archiv verschlüsselt auf den Betreiber-Mac kopiert,
in-memory entschlüsselt, die SQLite-Integrität geprüft und die Invalidierung
aller Sessions/Freigaben in einer isolierten Kopie erprobt. Kein Produktivzustand
wurde zurückgespielt. Die automatisierte unabhängige Replikation, ein vollständiger
Dienst-Wiederanlauf und ein unabhängiger externer Totalausfall-Monitor bleiben offen. Lokale Kopien
unterliegen derselben 14-Tage-Richtfrist und müssen beim regelmässigen Betrieb
ebenfalls bereinigt werden; hierfür läuft noch kein unabhängiger Automatismus.
 Auskunfts-/Löschanfragen auch für enthaltene Daten bewerten. Backups nicht
als Dauerarchiv verwenden. Vor einer Wiederherstellung:

1. Öffentliches Routing und ausgehende Anbieter-Verarbeitung sperren.
2. Seit Backup-Erstellung erfolgte Widerrufe, Kontosperren und Löschungen aus
   getrennt geschützt aufbewahrten Betriebsnachweisen nachvollziehen.
3. Diese Sperren und Löschungen auf den wiederhergestellten Stand anwenden;
   alte Freigaben und Sessions nicht ungeprüft reaktivieren.
4. Offene Anbieter-Löschaufträge abgleichen und kontrolliert wieder aufnehmen.
5. Erst nach dokumentierter Prüfung Verbindung und Verarbeitung freigeben.

Die technische 90-Tage-Bereinigung allein löst kein Widerrufs-Replay aus älteren
Backups. Backupfristen und unabhängige Widerrufs-/Löschhinweise darauf abstimmen.

## Sicherheitsvorfälle und Änderungen

Bei einem Vorfall neue Verarbeitungen begrenzen, aktive Sitzungen/Relays sperren,
notwendige Beweismittel mit minimalen Daten sichern und betroffene Anbieter
kontaktieren. Keine sensiblen Gesprächsinhalte in öffentliche Issues kopieren.
Risiko und Umfang bewerten, Massnahmen und Zeitpunkte dokumentieren. Besteht
voraussichtlich ein hohes Risiko für Persönlichkeit oder Grundrechte, Meldung an
den EDÖB so rasch als möglich nach Art. 24 DSG prüfen und vornehmen; notwendige
Information der betroffenen Personen gesondert prüfen. Die DSGVO-72-Stunden-Regel
nicht pauschal als Schweizer Frist ausgeben. Bei einem zugleich betroffenen
Hauptwebsite-Vorfall die Kirchgemeinde informieren und deren IDG-Pflichten/
zuständige Aufsicht getrennt berücksichtigen.

Bei wesentlichen Änderungen Freigabeversion in Code und Texten gemeinsam ändern,
erneute Buchfreigabe verlangen und Nutzungsbedingungen separat vorlegen. Keine
alten Nachweise als Zustimmung zu einem neuen Zweck interpretieren. Anbieter,
Länder, neue Eingaben, Löschfristen, technische Schnittstellen und Betriebsgrenzen
regelmässig mit dem tatsächlichen Stand abgleichen.

## Primärquellen

- [Schweizer DSG](https://www.fedlex.admin.ch/eli/cc/2022/491/de): insbesondere
  Art. 6, 9, 16–19, 22–25, 28, 30–31.
- [EDÖB Informationspflicht](https://www.edoeb.admin.ch/de/informationspflicht).
- [EDÖB Auslandbekanntgabe](https://www.edoeb.admin.ch/de/bekanntgabe-von-personendaten-ins-ausland).
- [EDÖB DSFA](https://www.edoeb.admin.ch/de/datenschutz-folgenabschaetzung).
- [ElevenLabs Geschäftskunden-DPA](https://elevenlabs.io/dpa).
- [ElevenLabs Aufbewahrung](https://elevenlabs.io/docs/eleven-agents/customization/privacy/retention).
- [ElevenLabs Trainingsabwahl](https://help.elevenlabs.io/hc/en-us/articles/29952728805393-Is-my-data-used-to-improve-ElevenLabs-AI-models).
- [Hetzner Standorte](https://docs.hetzner.com/cloud/general/locations/).

## Technischer Auslieferungsnachweis vom 9. Oktober 2026

80 Python-Tests, 44 JavaScript-Tests und SDK-Build bestanden. Desktop- und mobile Login-/Freigabeansichten geprüft. Auf dem öffentlichen Dienst wurden ausschliesslich synthetische Daten getestet: Zusammenfassung mit Freigabe, authentifizierter Sprach-Relay mit Anbieter-Metadaten und Audio, Gesprächsabbruch durch Widerruf. Die beiden entstandenen Anbieter-Gespräche wurden anschliessend erfolgreich gelöscht; keine offene Löschung oder unaufgelöste Anfrage blieb zurück. Alle sechs öffentlichen Verarbeitungsrouten verweigerten anonyme Anfragen mit HTTP 401. Rechtstexte blieben erreichbar. Der Lösch-Timer läuft; sein manuell ausgelöster Dienst meldete Erfolg. Die neuen Sicherheits-Prompts wurden an beiden bestehenden Agenten geprüft, ohne deren BYO-LLM-Konfiguration zu ändern. Das ersetzt keine rechtliche oder klinische Freigabe.

## Bestätigung vor jedem Gespräch

Vor Mikrofon-/Anbieterstart zeigt die App ausgewählte Personen und die KI-/
Anbieterinformation. Eine nicht vorausgewählte Bestätigung betrifft alle Anwesenden
und gegebenenfalls eine tatsächlich befugte Vertretung. Geänderte Auswahl oder
Buchinhalte verwerfen die Bestätigung. Der Server verlangt die aktuelle
`voice_notice`-Fassung und `confirmed: true`; Browser-Mikrofonfreigabe allein
genügt nicht. Nachweise enthalten Version, Zeitpunkt und technische Buchkennungen,
keine Stimme oder Gesprächsinhalte, und erscheinen im kontogebundenen Export.
Dies ist eine Erklärung des Bedienenden, kein unabhängiger Nachweis der tatsächlichen
Urteilsfähigkeit oder Vertretungsbefugnis.

## Ergänzender technischer Nachweis: Startbestätigung und Betriebskontrolle

84 Python- und 46 JavaScript-Tests bestanden; SDK-Build und Secret-Scan des
Auslieferungsstands bestanden. Der Gesprächshinweis wurde mit zwei synthetischen
Büchern auf Desktop und Mobilgerät geprüft, einschliesslich Abbrechen, Escape und
zurückgesetzter Checkbox beim nächsten Start. Live verweigerte der Server einen
Start ohne aktuelle Gesprächsbestätigung. Ein bestätigter synthetischer Start
lieferte Audio über den authentifizierten Relay; Widerruf schloss die Verbindung.
Beide Anbieter-Testgespräche wurden gelöscht; null offene Löschungen oder
ungeklärte Zuordnungen blieben zurück. Die zusätzliche Statusprüfung ist aktiv
und meldete frischen Cleanup sowie keine überfälligen Einträge. Sie liefert lokale
Systemd-Fehlerzustände, selbst keine externe Alarmzustellung. Der später ergänzte Monitor übernimmt
die E-Mail-Zustellung. Echte Profile bleiben in der
Produktionskonfiguration deaktiviert; Verträge und DSFA wurden nicht freigegeben.

## Betriebsalarme über Infomaniak

`myna-monitor.timer` läuft auf App- und Auth-Host alle fünf Minuten. Rootgeschütztes
`/etc/myna-monitor/config.json` enthält SMTP-Zugang, Empfänger und die Dienstliste.
Kein Empfänger und keine Zugangsdaten gehören ins Repository. Das Programm aus
`deploy/scripts/monitor.py` wird root:root 0644 nach
`/usr/local/sbin/myna-monitor` installiert und mit `python3 -I` ausgeführt.
Der SMTP-Client verwendet ausschliesslich `mail.infomaniak.com:587`, zwingendes
STARTTLS mit Zertifikatsprüfung und keine Debug-/Antwortprotokollierung.

Überwacht werden aktive App-Dienste und Timer, die Ergebnisse von Lösch-/Backup-
Prüfungen sowie öffentliche HTTPS-Erreichbarkeit. Erfolgreiche One-shot-Dienste
müssen nicht dauerhaft aktiv bleiben. Erste und geänderte Störungen melden sich
sofort, unveränderte frühestens alle sechs Stunden; Entwarnung erfolgt einmal.
Meldungen enthalten nur feste Dienstbezeichnungen und allgemeine Statuswerte,
keine Logauszüge, Kennungen, Profile, Stimmen oder Gesprächsinhalte. Nach fehl-
geschlagenem Versand bleibt die Meldung für einen erneuten Versuch offen.

Am 9.10.2026 wurde die angeforderte Testmail vom SMTP-Server angenommen; ein
Postfacheingang wurde nicht unabhängig geprüft. SMTP/TLS-Anmeldung wurde auch
vom App-Host bestätigt. Beide regulären Prüfungen meldeten null Störungen.
Monitor-Konfigurationen sind in den verschlüsselten Backups enthalten. Nach
Wiederherstellung die Programme/Units rootgeschützt neu installieren, Zieladresse
und Zugang prüfen und einen angekündigten Test versenden. Für eine Testnachricht
im geschützten Operator-Kontext: `python3 -I /usr/local/sbin/myna-monitor --test`.

Dies ersetzt keine unabhängig betriebene Überwachung: Bei vollständigem Host-,
Netz-, Timer- oder SMTP-Ausfall kann die eigene Meldung ausbleiben. Fehler des
Monitor-Dienstes in Systemd untersuchen und den Zustellweg regelmässig prüfen.
