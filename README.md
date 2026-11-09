# QuantumTest — Vedoy Code Scanner

QuantumTest er Vedoy Studios prosjekt for testing av webapper. Denne første kjørbare modulen skanner kildekode; AI-baserte brukertester er fortsatt planlagt.

## Bruk lokalt

Krever Python 3.10+ og ingen ekstra pakker. Kjør fra prosjektroten:

```bash
python3 scanner/scan.py /sti/til/prosjekt --output rapport.json
python3 scanner/scan.py /sti/til/prosjekt --format sarif --output rapport.sarif --fail-on medium
python3 -m unittest discover -s tests -v
```

## GitHub

Medfølgende workflow kjører ved push og pull request og kan startes manuelt. Rapporten ligger under Actions → kjøringen → Artifacts. Skanneren kan brukes i andre repoer etter checkout:

```yaml
permissions:
  contents: read
steps:
  - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
    with:
      persist-credentials: false
  - uses: leandervedoy/QuantumTest@<reviewed-commit-sha>
    with:
      path: '.'
      fail-on: none
      output: ${{ runner.temp }}/vedoy-scan.sarif
      exclude: |
        _vercel-static/*
        assets/vendor/*
```

Fest QuantumTest til en gjennomgått commit-SHA ved produksjonsbruk. `fail-on: none` lar en pilot rapportere funn uten å blokkere CI; en faktisk kjøre-/konfigurasjonsfeil gir fortsatt exit 2. Runneren må ha Python 3.10+ på PATH (ubuntu-latest har dette). SARIF kan lastes opp separat til GitHub Code Scanning der funksjonen er tilgjengelig; dette er ikke aktivert av denne workflowen. Vurder rapporter og artefakttilgang før opplasting.

## Regler

| ID | Nivå | Ser etter |
|---|---|---|
| QT001 | Høy | Privatnøkkelmarkører |
| QT002 | Høy | Enkelte GitHub- og AWS-nøkkelformater |
| QT003 | Høy | Mulige hardkodede hemmeligheter |
| QT004 | Middels | eval-kall |
| QT005 | Middels | HTML-injeksjonspunkter |
| QT006 | Høy | Deaktivert TLS-verifisering |
| QT007 | Middels | Shell-kjøring |
| QT008 | Middels | Potensielt utrygg deserialisering |

Dette er mønsterbaserte indikasjoner som må gjennomgås manuelt. Skanneren gjør ingen dataflytanalyse, avhengighetsskanning eller nettverkstesting og garanterer ikke at kode er sikker. Kommentarer og strenger kan gi falske positiver. Den kjører aldri prosjektets kode og sender ingen data over nettverket. Rapporter inneholder filnavn, linjer og faste beskrivelser, aldri kildekodelinjer eller nøkkelverdier fra kildekoden. Filnavn som ligner kjente hemmeligheter eller inneholder kontrolltegn holdes utenfor rapporten; vilkårlige sensitive filnavn kan ikke gjenkjennes med full sikkerhet, så rapporten må behandles som potensielt sensitiv.

`--exclude 'tests/*'` kan gjentas med rot-relative globmønstre. Actionens `exclude` tar ett mønster per linje. Vanlige bygge- og avhengighetsmapper hoppes over. Symlenker følges ikke. Filer over 1 MiB, binærfiler og ikke-UTF-8-filer hoppes over; JSON viser disse begrensningene i `skipped`. Utrygge filnavn holdes tilbake uten å vise stien. SARIF inneholder bare funn, så bruk JSON lokalt for å se utelatelser. Skanningen stopper med exit 2 ved mer enn 10 000 aktuelle filer, 128 MiB leste data, 5 000 treff eller 9 MiB rapport. Kun gjenkjente tekst-/kodefiltyper skannes. Ingen git-historikk skannes.

Exit-koder: 0 = ingen funn på valgt terskel, 1 = terskel nådd, 2 = kjøre-/konfigurasjonsfeil. Standard er høy; `none` slår av feil på funn. Rapporter bør lagres utenfor kildekoden. Ingen automatisk endring eller retting av kode.
