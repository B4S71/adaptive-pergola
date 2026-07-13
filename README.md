# Adaptive Pergola

Adaptive Pergola ist eine Home-Assistant-Custom-Integration fuer Pergolen mit verstellbaren Lamellen (Lamellendach / Louvered Roof). Die Integration berechnet aus Sonnenstand, Dachgeometrie, Wetter- und Klimabedingungen die Ziel-Lamellenstellung und steuert den Aktor automatisch.

Der Code ist der Pergola-Zweig von [Adaptive Cover Pro](https://github.com/jrhubott/adaptive-cover-pro): die komplette Louvered-Roof-Funktionalitaet (Stand `2.31.1-beta.24` des Forks [B4S71/adaptive-cover-pro](https://github.com/B4S71/adaptive-cover-pro), Branch `contrib/louvered-roof-pergola`) als eigenstaendige Integration mit eigener Domain `adaptive_pergola`. Alle anderen Cover-Typen (Vertikal, Awning, Tilt, Venetian, Dachfenster) wurden entfernt — nur der Louvered-Roof-Typ und das virtuelle Building Profile sind enthalten. Geraeteklassen, Entitaeten, Optionen und Verhalten entsprechen dem Original.

## Funktionen

- Sonnenstandsgefuehrte Lamellenwinkel-Berechnung (Minimal-Block-Pose, Occupancy-Shading-Geometrie, gerichtete Terrassen-Erweiterungen)
- Max-Light-Modus (Profilwinkel / edge-on, Zwei-Regime nah/fern, achsrelativ)
- Shade-Airflow-Pose, optional temperaturgesteuert (`lr_airflow_by_temp`)
- Klima-Modus (Sommer/Winter) mit dachspezifischen Posen statt Venetian-Slat-Regeln
- Morning Position mit Post-Sunrise-Hold (Kondensat / Dawn-Gap), Lead = 0 moeglich
- Evening-Reopening-Sicherheitswinkel
- Wetter-Override (Wind, Regen, Sperrsensoren), Cloud Suppression, Solar-Forecast-Gating ueber die Startzeit des aktiven Fensters
- Manual Override mit Erkennung, Zeitfenster, Reset-Button und Statussensoren
- Building Profile: gemeinsame Sensor-Konfiguration fuer mehrere Pergola-Sektionen
- Config Flow komplett in der UI (Geometrie, Kinematik-Kalibrierung `lr_tilt_vertical_pct`, Verhalten, Klima, Wetter, Debug)

## Installation mit HACS

1. Oeffne HACS in Home Assistant.
2. Gehe zu den benutzerdefinierten Repositories.
3. Fuege `https://github.com/B4S71/adaptive-pergola` als Repository vom Typ `Integration` hinzu.
4. Suche nach `Adaptive Pergola` und installiere die Integration.
5. Starte Home Assistant neu.
6. Richte die Integration ueber `Einstellungen > Geraete & Dienste > Integration hinzufuegen` ein.

## Manuelle Installation

1. Kopiere den Ordner [custom_components/adaptive_pergola](custom_components/adaptive_pergola) nach `config/custom_components/adaptive_pergola` deiner Home-Assistant-Instanz.
2. Starte Home Assistant neu.
3. Fuege `Adaptive Pergola` in den Integrationen hinzu.

## Konfiguration

Im Config Flow definierst du unter anderem:

- Ziel-Cover-Entitaet (benoetigt `set_tilt_position`)
- Dachgeometrie: Achs-Azimut, Dachneigung, Dach- und Schutzhoehe, Footprint, Lamellen-Chord/Staerke/Abstand, Fahrbereich `theta_min`–`theta_max`
- Tilt-Kalibrierung: `lr_tilt_vertical_pct` fuer nichtlineare Kurbelkinematik
- Gerichtete Schutzflaechen-Erweiterungen (Distanz + Azimut je Arm)
- Klima-, Wetter-, Licht/Wolken- und Verhaltensoptionen wie in Adaptive Cover Pro

Dokumentation der Konzepte: [Adaptive Cover Pro Wiki](https://github.com/jrhubott/adaptive-cover-pro/wiki).

## Herkunft und Weiterentwicklung

Die Weiterentwicklung der Pergola-Logik passiert in diesem Repository; die Basis-Funktionalitaet von Adaptive Cover Pro bleibt im Fork unveraendert. Der gemeinsame Unterbau (Coordinator, Pipeline-Handler, Manager, Config Flow) wurde vollstaendig uebernommen, damit Fixes aus dem Fork per Diff portierbar bleiben.

## Tests

Die Test-Suite stammt aus Adaptive Cover Pro. Tests der entfernten Cover-Typen wurden entfernt; die Tests der gemeinsamen Infrastruktur laufen ueber Test-Stand-in-Policies weiter (siehe [tests/compat_policies.py](tests/compat_policies.py)).

```bash
python -m pytest -q
```
