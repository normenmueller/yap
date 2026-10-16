# Quellen der Repository-Vorlagen

Diese Dateien bilden die eigenständig nutzbaren Vorlagen `general` und
`db-gitlab`. [English documentation](README.md).

`base/` enthält die gemeinsamen Dateien. `gitlab/db/` ergänzt die unveränderte
DB-Lizenz und das Metadatenmuster; eine zweite Projekt-README gibt es dort nicht.
`ai4x-footer.html` enthält den optionalen gemeinsamen Herkunftshinweis.

## Manuelle Verwendung ohne yap

1. Wähle Deutsch (`de`), Englisch (`en`) oder beide Sprachen; bei beiden zusätzlich
   die Hauptsprache. Kopiere die gewählte `base/README.<Sprache>.md` als
   `README.md`, gegebenenfalls die andere als `README.<Sprache>.md`. Wiederhole
   dies unter `doc/`. Kopiere keine ungewählte Sprache. Übernimm `AGENTS.md`,
   `.gitattributes`, `.gitignore` und die drei `.ai4x/`-Dateien zunächst unverändert.
2. Fülle die benannten Felder mit einfachem Projekttext. Maskiere erforderliche
   Markdown-Sonderzeichen und HTML. `title`, `purpose` und `maintainer` enthalten
   Titel, Zweck und Kontakt; fehlender Zweck oder Kontakt kann ausdrücklich offen
   bleiben. `readme` bezeichnet jeweils den Zieldateinamen derselben Sprache.
   `alternate_link` verlinkt die andere Sprache im selben Verzeichnis oder bleibt
   bei einsprachigen Projekten leer. `languages` und `primary_language` in CONTEXT
   halten die Auswahl fest. Die Agentendateien bleiben englisch.
3. Bei `general` bleiben `db_structure` und `db_authority` leer. `license_notice`
   lautet je nach Dokumentensprache „Noch nicht festgelegt.“ oder
   „Not selected yet.“ Wenn Du ausdrücklich einen Lizenztext mitgibst, lege ihn
   als `LICENSE` ab, verlinke ihn im Lizenzhinweis, ergänze `LICENSE -text` in
   `.gitattributes` und seine Zuständigkeit in CONTEXT.
4. Für DB kopiere `gitlab/db/LICENSE` ohne Änderungen. Prüfe und bestätige vor dem
   Ausfüllen der kopierten `scm-info.yaml` sämtliche vorgeschlagenen Werte für
   dieses Repository. Verwende YAML-Zeichenketten und Listen; JSON-Zeichenketten
   mit Anführungszeichen und JSON-Listen sind ebenfalls gültiges YAML.
   `version: v3` und `license: LicenseRef-DBISL` bleiben fest. Das Feld
   `custom_confidentiality` gehört zum verschachtelten Vertraulichkeitswert.
   Ergänze die Beschreibung von Lizenz und Metadaten in `db_structure` sowie
   `db_authority`, verlinke LICENSE in `license_notice` und ergänze
   `LICENSE -text` in `.gitattributes`.
5. Fülle `copyright` ausdrücklich. Der bestätigte persönliche Vorschlag lautet
   `© 2026 Project contributors`; ändere Urheber,
   Profilverweis oder Jahr bei Bedarf. Aktualisiere das Jahr nicht automatisch.
   Ersetze `footer` durch den Inhalt von `ai4x-footer.html` oder lasse es bei
   ausdrücklicher Abwahl leer. Es dürfen keine offenen Vorlagenfelder bleiben.

Diese Schritte erzeugen weder Git-Repository noch Commit, Remote, serverseitigen
Schutz oder Push. `protected-branches` beschreibt Metadaten und richtet keinen
Branchschutz ein. Die DB-Metadaten werden strukturell geprüft; eine unabhängige
Bestätigung gegen das interne DB-Schema oder die DB-Richtlinie liegt nicht vor.

## Eingaben für den Renderer

`render_template(profile, inputs)` liefert relative Dateipfade und Bytes, ohne
Eingaben zu ändern oder Zieldateien zu schreiben. Ungültige Werte, unbekannte
Felder, offene Vorlagenfelder und unsichere Quellpfade führen zu `ValueError`.

| Eingabe | Pflichtwert oder Vorgabe |
| --- | --- |
| `title` | Nichtleerer einzeiliger Titel. |
| `languages` | Liste `["de"]`, `["en"]` oder beide Sprachen ohne Wiederholung. |
| `primary_language` | Ausdrücklich gewähltes `de` oder `en` aus dieser Liste. |
| `purpose`, `maintainer` | Optionale Objekte mit ausgewählten Sprachkürzeln als Schlüssel und nichtleerem Text als Wert; mehrzeiliger Text ist erlaubt. Fehlende Einträge werden in der jeweiligen Sprache als offen gekennzeichnet. |
| `copyright_holder` | Optionaler einzeiliger Text; Vorgabe `Project contributors`. |
| `copyright_year` | Optionale Ganzzahl 1–9999; feste Vorgabe `2026`. |
| `copyright_url` | Optionale HTTP(S)-Adresse ohne Zugangsdaten oder Leerraum, oder leerer Text. Die Vorgabe ist leer; ein öffentliches Profil wird ausdrücklich gewählt. |
| `ai4x_footer` | Optionaler boolescher Wert; Vorgabe `true`. |
| `license_text` | Nur `general`: optionaler nichtleerer Text, der unverändert als UTF-8 in LICENSE landet, einschließlich abschließenden Leerraums. Ohne Eingabe wird keine Lizenz gewählt. |
| `db_metadata` | Nur DB: vollständiges Metadatenobjekt, wie unten beschrieben. |
| `db_confirmed` | Nur DB: boolesches `true` nach Prüfung des vollständigen Wertesatzes für dieses Repository. |

DB-Metadaten benötigen `version: "v3"`, `license: "LicenseRef-DBISL"`, nichtleere
Zeichenkettenlisten für `contacts`, `reference-ids`, `protected-branches` und
`usage-scenario`, einen nichtleeren Text für `confidentiality` sowie `custom` mit
nichtleeren Werten für `integrity`, `availability` und `confidentiality`.
Zusätzliche Schlüssel sind nicht erlaubt. Ohne maßgebliches Schema werden keine
weiteren erlaubten Werte erfunden. Der Renderer serialisiert die Eingaben als Daten.

`defaults()` liefert eine unabhängige Kopie der Copyright-/Fußzeilenvorschläge und
der vollständigen vorgeschlagenen DB-Metadaten. Sprachauswahl und DB-Bestätigung
werden nicht vorgegeben. Nach erfolgreicher Render-Prüfung liefert
`resolved_inputs(inputs)` die tatsächlich wirksamen Vorgaben und ausdrücklich
offene Zweck-/Kontakteinträge für die Anzeige; es ergänzt oder bestätigt keine
DB-Metadaten eigenmächtig.

Beispiel für `general`:

```json
{
  "title": "Projektbeispiel",
  "languages": ["de"],
  "primary_language": "de",
  "purpose": {"de": "Das beabsichtigte Ergebnis beschreiben."},
  "maintainer": {"de": "Projektteam"}
}
```

Git-Initialisierung, lokale Verknüpfungen und Veröffentlichung bleiben gesonderte
ausdrückliche Vorgänge. Die erzeugten Dateien gehören dem Zielprojekt; spätere
Vorlagenänderungen aktualisieren bestehende Repositories nicht.
