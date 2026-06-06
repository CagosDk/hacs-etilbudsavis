# eTilbudsavis for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Synkroniser din [eTilbudsavis](https://etilbudsavis.dk) indkøbsliste med Home Assistant som en todo-liste.

## Funktioner

- Vis din indkøbsliste i Home Assistant
- Tilføj og fjern varer
- Sæt kryds ved indkøbte varer
- Opdateres automatisk hvert 5. minut

## Installation via HACS

1. Åbn HACS i Home Assistant
2. Gå til **Integrations** → **Custom repositories**
3. Tilføj `https://github.com/CagosDk/hacs-etilbudsavis` som **Integration**
4. Find og installer **eTilbudsavis**
5. Genstart Home Assistant

## Opsætning

1. Gå til **Indstillinger → Enheder & tjenester → Tilføj integration**
2. Søg efter **eTilbudsavis**
3. Indtast din e-mailadresse
4. Bekræft med engangskoden du modtager på mail
5. Vælg indkøbsliste (hvis du har flere)

## Bemærk

Denne integration bruger eTilbudsavis' interne API og er ikke officielt støttet af Tjek/eTilbudsavis.
