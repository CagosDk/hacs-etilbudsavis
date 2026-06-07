# eTilbudsavis for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Synkroniser dine [eTilbudsavis](https://etilbudsavis.dk) indkøbslister med Home Assistant som todo-lister.

## Funktioner

- **Fuld synkronisering** — varer fra eTilbudsavis-appen vises automatisk i HA inden for 60 sekunder
- **Tilføj varer fra HA** — skriv `3x Mælk` for at tilføje 3 stk., eller blot `Mælk` for 1 stk.
- **Omdøb varer** — rediger et varenavn i HA og det opdateres i eTilbudsavis
- **Slet varer** — fjern enkelt- eller flere varer ad gangen
- **Sæt kryds** — afkrydsning synkroniseres øjeblikkeligt til eTilbudsavis
- **Antal** — vises som `3x Mælk` direkte i listevisningen
- **Noter** — eTilbudsavis-noter (f.eks. "ikke øko") vises i parentes bag varenavnet: `1x Mælk (ikke øko)`
- **Butiksnavn** — tilknyttet butik vises under varen
- **Udløbne tilbud** — varer med et udløbet tilbud markeres tydeligt: `UDLØBET!!! 1x Mozzarellaost`
- **Flere lister** — tilføj og synkroniser flere indkøbslister fra samme konto
- **Re-login** — hvis sessionen udløber vises automatisk en ny login-dialog i HA

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

For at tilføje flere lister bagefter: gentag trin 1–5 med samme e-mailadresse.

## Brug fra Home Assistant

| Handling | Sådan gør du |
|---|---|
| Tilføj vare | Skriv varenavnet i feltet — fx `Mælk` eller `3x Mælk` |
| Tilføj med antal | Skriv `{antal}x {navn}` — fx `2x Smør` |
| Omdøb vare | Rediger varenavnet direkte i HA |
| Slet vare | Marker og slet fra HA |
| Afkryds vare | Sæt flueben — synkroniseres til eTilbudsavis |

> **Bemærk:** Butik, noter og antal fra eTilbudsavis-appen er skrivebeskyttede i HA — de vises, men kan ikke redigeres herfra.

## Versionshistorik

### v1.2.0
- Antal (`3x Mælk`), noter (`(ikke øko)`) og butiksnavn vises i todo-listen
- Udløbne tilbud markeres med `UDLØBET!!!`
- Antal kan angives fra HA ved at skrive `{N}x {navn}`

### v1.1.0
- Understøttelse af flere indkøbslister pr. konto
- Re-auth flow: automatisk ny login-dialog når sessionen udløber
- Omdøbning af varer fra HA

### v1.0.0
- Første udgivelse: synkronisering af én indkøbsliste som HA todo-entitet

## Bemærk

Denne integration bruger eTilbudsavis' interne API og er ikke officielt støttet af Tjek/eTilbudsavis. API'et kan ændre sig uden varsel.
