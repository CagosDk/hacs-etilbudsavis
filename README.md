# eTilbudsavis for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Synkroniser din [eTilbudsavis](https://etilbudsavis.dk) indkøbsliste med Home Assistant som en todo-liste.

## Funktioner

- Vis din indkøbsliste i Home Assistant
- Tilføj og fjern varer direkte fra HA
- Sæt kryds ved indkøbte varer (synkroniseres til eTilbudsavis)
- Automatisk opdatering hvert minut

> **Bemærk:** Opdateringer fra eTilbudsavis-appen eller websitet vises i Home Assistant inden for **op til 60 sekunder**. Ændringer fra Home Assistant sendes øjeblikkeligt til eTilbudsavis.

## Installation via HACS

1. Åbn HACS i Home Assistant
2. Gå til **Integrationer** → **Brugerdefinerede repositories**
3. Tilføj `https://github.com/CagosDk/hacs-etilbudsavis` som **Integration**
4. Find og installer **eTilbudsavis**
5. Genstart Home Assistant fuldstændigt

## Opsætning

1. Gå til **Indstillinger → Enheder & tjenester → Tilføj integration**
2. Søg efter **eTilbudsavis**
3. Indtast din e-mailadresse — du modtager en 6-cifret engangskode
4. Indtast koden fra din e-mail
5. Vælg hvilke indkøbslister du vil synkronisere

## Bemærk

Denne integration bruger eTilbudsavis' interne API og er ikke officielt støttet af Tjek/eTilbudsavis. API'et kan ændre sig uden varsel.
