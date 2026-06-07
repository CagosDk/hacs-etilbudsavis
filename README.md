# eTilbudsavis for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Synkroniser dine [eTilbudsavis](https://etilbudsavis.dk) indkøbslister med Home Assistant som todo-lister.

## Funktioner

- **Fuld synkronisering** — varer fra eTilbudsavis-appen vises automatisk i HA inden for 60 sekunder
- **Antal** — vises som `3x Mælk` i listevisningen
- **Noter** — eTilbudsavis-noter vises i parentes: `1x Mælk (øko)`
- **Butiksnavn** — tilknyttet butik vises under varen
- **Udløbne tilbud** — markeres tydeligt: `UDLØBET!!! 1x Mozzarellaost`
- **Afkrydsning** — synkroniseres øjeblikkeligt til eTilbudsavis
- **Tilføj varer** — skriv `Mælk` eller `3x Mælk` for at angive antal
- **Omdøb og slet** — ændringer sendes øjeblikkeligt til eTilbudsavis
- **Flere lister** — synkroniser flere indkøbslister fra samme konto
- **Re-login** — automatisk ny login-dialog hvis sessionen udløber

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

For at tilføje flere lister: gentag opsætningen med samme e-mailadresse.

## Brug fra Home Assistant

| Handling | Sådan gør du |
|---|---|
| Tilføj vare | Skriv `Mælk` eller `3x Mælk` for at angive antal |
| Omdøb vare | Rediger varenavnet direkte i HA |
| Slet vare | Marker og slet fra HA |
| Afkryds vare | Sæt flueben — synkroniseres til eTilbudsavis |

> **Bemærk:** Butik, noter og antal fra eTilbudsavis-appen er skrivebeskyttede — de vises i HA, men kan ikke redigeres herfra.

## Versionshistorik

### v1.2.0
- Antal, noter og butiksnavn vises i todo-listen
- Udløbne tilbud markeres med `UDLØBET!!!`
- Antal kan angives fra HA ved at skrive `{N}x {navn}`

### v1.1.0
- Flere indkøbslister pr. konto
- Automatisk re-login når sessionen udløber
- Omdøbning af varer fra HA

### v1.0.0
- Første udgivelse

## Bemærk

Denne integration bruger eTilbudsavis' interne API og er ikke officielt støttet af Tjek/eTilbudsavis. API'et kan ændre sig uden varsel.
