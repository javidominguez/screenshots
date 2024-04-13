# Ohjattu kuvakaappaus

Tämä lisäosa tarjoaa ohjatun toiminnon kuvakaappauksen ottamiseen koko näytöstä tai tietyistä alueista, kuten objekteista, ikkunoista jne. Se aktivoidaan Print Screen -näppäimellä, joka on standardinäppäimistöissä tavallisesti ensimmäinen F12-näppäimen oikealla puolella olevassa kolmen näppäimen ryhmässä. Jos haluat käyttää toista näppäintä, voit määrittää sen NVDA:n Asetukset-alivalikon Näppäinkomennot-kohdasta.

Kun ohjattu toiminto on käynnistetty, aktiivisen objektin ympärille luodaan virtuaalinen suorakulmio ja näppäinkomentokerros aktivoidaan, jolloin käytössä ovat seuraavat toiminnot:

### Komennot

* F1: Näyttää peruskomentojen ohjeen. Kahdesti painettaessa avataan tämä asiakirja.

#### Suorakulmion tiedot

Numeroilla 1-7 saa seuraavia tietoja:

* 1: Ylävasemman ja alaoikean kulman koordinaatit.
* 2: Suorakulmion mitat (leveys kertaa korkeus).
* 3: Viiteobjekti.
* 4: Viiteobjektin kattama alue suorakulmiosta.
* 5: Ilmoittaa, onko osa viiteobjektista suorakulmion ulkopuolella.
* 6: Ilmoittaa, ylittääkö suorakulmio etualalla olevan aktiivisen ikkunan rajat.
* 7: Suorakulmion kattama alue näytöstä.

Väli-näppäin lukee kaikki nämä tiedot peräkkäin.

#### Objektin valinta

Viiteobjekti on näytöllä oleva objekti, joka on rajattu suorakulmiolla. Aluksi tämä objekti on järjestelmän aktiivinen objekti, mutta jokin muu voidaan valita seuraavilla näppäimillä:

* Ylänuoli: Rajaa nykyisen objektin säilön.
* F: Rajaa aktiivisen objektin.
* N: Rajaa navigointiobjektin kohdalla olevan objektin.
* W: Rajaa aktiivisen ikkunan.
* M: Rajaa hiiriosoittimen alla olevan objektin.
* S: Rajaa koko näytön.

Muutokset perutaan alanuolinäppäimellä.

#### Suorakulmion koko

Suorakulmion kokoa voi muuttaa seuraavilla näppäimillä:

* Vaihto+Nuolinäppäimet siirtävät vasenta yläkulmaa:
* Vaihto+Ylä- tai alanuoli siirtää yläreunaa.
* Vaihto+Vasen tai oikea nuoli siirtää vasenta reunaa.
* Ctrl+Nuolinäppäimet siirtävät oikeaa alakulmaa:
* Ctrl+Ylä- tai alanuoli siirtää alareunaa.
* Ctrl+Vasen tai oikea nuoli siirtää oikeaa reunaa.
* Ctrl+Vaihto+Ylänuoli laajentaa suorakulmiota siirtäen kaikkia neljää reunaa ulospäin.
* Ctrl+Vaihto+Alanuoli kutistaa suorakulmiota siirtäen kaikkia neljää reunaa sisäänpäin.

Siirtämisen pikselimäärää voi muuttaa Page up- ja Page down -näppäimillä sekä asetuksissa.

Viiteobjekti saattaa muuttua suorakulmion kokoa muutettaessa. Lisäosa yrittää aina valita objektin, joka on keskellä etualalla ja joka kattaa suuremman alueen suorakulmiosta. Objektin muutoksista ilmoitetaan niiden tapahtuessa.

#### Tekstintunnistus

R-näppäimen painaminen tunnistaa suorakulmiossa olevan tekstin. Tämä ei välttämättä toimi kaikissa tilanteissa, esimerkiksi jos suorakulmio on liian pieni tai jos Bluetooth Audio -lisäosa on asennettu (tämä on harvinainen yhteensopimattomuus).

#### Kuvakaappauksen ottaminen

Enter-näppäin ottaa kuvakaappauksen suorakulmiolla rajatusta näytön alueesta, tallentaa sen tiedostoon ja poistuu komentokerroksesta.

Vaihto+Enter-näppäin avaa valintaikkunan, jossa voit valita, minne kuvakaappaus tallennetaan sen sijaan, että se tallennettaisiin automaattisesti oletussijaintiin.

Esc-näppäin peruuttaa ja poistuu komentokerroksesta.

### Asetukset

NVDA:n asetuksissa on mahdollista määrittää seuraavat asetukset:

* Kansio, jonne tiedostot tallennetaan. Oletuksena käyttäjän Tiedostot-kansio.
* Kuvatiedoston muoto.
* Suurennetaanko otettu kuvakaappaus vai ei. Mittakaava lasketaan suorakulmion ja näytön koon perusteella. Pienet kuvat suurennetaan enintään 4-kertaisiksi ja suuremmat vain näytön reunaan saakka.
* Tallennuksen jälkeen suoritettava toiminto ("älä tee mitään", "avaa kansio" tai "avaa tiedosto").
* Siirtämisen pikselimäärä.