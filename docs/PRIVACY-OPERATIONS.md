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
- Die konkrete OIDC-Subject-Kennung des freigegebenen Kontos steht in
  `privacy.approved_subjects`.

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
8. Erst nach dokumentierter Entscheidung einzelne Konten freigeben. Keine
   Massenfreigabe. Ablehnung, erkennbares Unwohlsein und Stoppwünsche unabhängig
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

Die Bereinigung muss tatsächlich regelmässig laufen. `privacy_admin.py --status`, Timer/Exitstatus und
Warteschlangen prüfen, Fehler untersuchen und Betriebsnachweise privat führen. Automatische Alarmierung
ist durch den Timer allein nicht eingerichtet; einen zuständigen Menschen und
regelmässige Statuskontrolle verbindlich benennen.
Rechtstexte anpassen, wenn Code, Zeiten oder tatsächlicher Betrieb abweichen.

Verschlüsselte Backups mit dokumentierter Laufzeit und Zugriffsbeschränkung
führen. Auskunfts-/Löschanfragen auch für enthaltene Daten bewerten. Backups nicht
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
