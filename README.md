# Adaptive Pergola

Adaptive Pergola ist eine Home-Assistant-Custom-Integration fuer Pergolen mit verstellbaren Lamellen. Die Integration berechnet aus Sonnenstand, Pergola-Geometrie und Wetterbedingungen einen Zielwinkel beziehungsweise Stellwert fuer den Lamellenaktor.

Das Projekt ist bewusst auf reale Pergola-Mechanik ausgelegt:

- 3D-Projektion von Sonne auf Boden und Hauswand
- getrennte Modellierung von Lamellenachse, Pergola-Ausrichtung und Oeffnungsrichtung
- mehrere Tracking-Strategien fuer Licht, Schatten oder einen Kompromiss dazwischen
- Wetter-Override fuer Wind, Regen und weitere Sperrsensoren
- Manual Override mit Zeitfenster, Reset-Button und Statussensor

## Funktionen

- Tracking-Modi `max_light`, `max_shade` und `balanced`
- Ausgabe als Cover-Tilt, Cover-Position oder Number/Input-Number
- nichtlineare Aktuatorabbildung mit offenem Zwischenpunkt
- Schutzlogik fuer Pergola-Flaeche, zusaetzliche Schutzflaeche und optionale Hauswand
- Config Flow fuer Einrichtung direkt in Home Assistant

## Installation mit HACS

1. Oeffne HACS in Home Assistant.
2. Gehe zu den benutzerdefinierten Repositories.
3. Fuege `https://github.com/jrhubott/adaptive-pergola` als Repository vom Typ `Integration` hinzu.
4. Suche nach `Adaptive Pergola` und installiere die Integration.
5. Starte Home Assistant neu.
6. Richte die Integration ueber `Einstellungen > Geraete & Dienste > Integration hinzufuegen` ein.

## Manuelle Installation

1. Kopiere den Ordner [custom_components/adaptive_pergola](custom_components/adaptive_pergola) nach `config/custom_components/adaptive_pergola` deiner Home-Assistant-Instanz.
2. Starte Home Assistant neu.
3. Fuege `Adaptive Pergola` in den Integrationen hinzu.

## Konfiguration

Im Config Flow definierst du:

- Ziel-Entitaet und Aktuator-Modus
- Pergola-Geometrie und Lamellenkinematik
- Hausanbindung und zusaetzliche Schutzflaechen
- Wettergrenzen und Sicherheitsposition
- Manual-Override-Dauer, Schwellwert und Reset-Verhalten

Die Kernlogik lebt in [custom_components/adaptive_pergola/engine.py](custom_components/adaptive_pergola/engine.py), die Laufzeitsteuerung in [custom_components/adaptive_pergola/coordinator.py](custom_components/adaptive_pergola/coordinator.py) und der Setup-Dialog in [custom_components/adaptive_pergola/config_flow.py](custom_components/adaptive_pergola/config_flow.py).

## Tracking-Strategien

- `max_light`: folgt der realen Sonnenhoehe bis zur definierten Offenlage.
- `max_shade`: setzt auf `max_light + 90°`, begrenzt durch den maximalen Fahrwinkel.
- `balanced`: startet mit `max_light` und wechselt auf Beschattung, wenn Sonne zu tief eindringt oder die Hauswand trifft.

## Ausgangsmodi

- `cover.set_cover_tilt_position`
- `cover.set_cover_position`
- `number.set_value` beziehungsweise `input_number.set_value`

## Demo und Entwicklung

Im Ordner [config/configuration.yaml](config/configuration.yaml) liegt eine direkt testbare Demo-Konfiguration.

Start:

```bash
./scripts/develop
```

## Tests

- [tests/test_engine.py](tests/test_engine.py)
- [tests/test_config_flow.py](tests/test_config_flow.py)
- [tests/test_integration.py](tests/test_integration.py)

Letzter verifizierter Lauf:

```bash
'/Users/sgrebe/ownCloud/Persönlich/Code/adaptive-cover-pro/.venv/bin/python' -m pytest tests/test_config_flow.py tests/test_integration.py -q
```
