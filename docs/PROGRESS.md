# RAVNUX — postęp prac

Aktualizacja: 2026-10-04.

## Zasady kontynuacji

- Jeden mały etap na odpowiedź. Większy etap dzielić na podetapy.
- Na początku odczytać ten plik i bieżący stan repozytorium.
- Sprawdzać tylko zakres potrzebny do aktualnego etapu, bez powtarzania całego audytu.
- Każdy etap zakończyć zapisem zmian na GitHubie i aktualizacją tego pliku: commit, testy, ograniczenia, następny krok.
- Rozróżniać zmiany lokalne, zapisane na GitHubie i sprawdzone w uruchomionym ISO.
- Nie publikować lokalnych ścieżek ani danych dostępowych.

## Potwierdzony punkt wyjścia

Sprawdzony commit bazowy: `7fa45459e907f5cb5bcb6cab806600bef5b7dfb5`.

Repozytorium zawiera skrypty budowania i instalacji, konfigurację XLibre,
grafikę, polski przewodnik i testy źródeł.
Odnaleziono niewysłane poprawki z poprzednich sesji.
Pełne zbudowanie i rozruch finalnego ISO nie są jeszcze potwierdzone.

## Etapy

| Etap | Zakres | Warunek zakończenia | Stan |
| --- | --- | --- | --- |
| 0 | Uporządkowanie pracy | Plan zapisany w repozytorium | Gotowe |
| 1 | Klucze XLibre | Przegląd poprawki, testy keyring, zapis zmian | Gotowe |
| 2 | Ochrona partycji EFI | Przegląd instalatora, test odrzucenia zajętej EFI, zapis | Gotowe |
| 3 | Ozdobne logo R ze złotymi wzorami | Porównanie odzyskanej grafiki z GitHubem, kontrola integracji, zapis | Gotowe |
| 4 | Budowanie i CI | Przegląd nbd, testu VM, konsoli szeregowej i workflow, zapis | Gotowe; CI zaliczone |
| 5 | Budowa ISO | Udany build konkretnego commita, zapis przebiegu i artefaktu | Oczekuje |
| 6a | Rozruch BIOS | Test VM i zapis wyniku | Oczekuje |
| 6b | Rozruch UEFI | Test VM i zapis wyniku | Oczekuje |
| 6c | Instalacja | Instalacja na pustym dysku VM i start z dysku | Oczekuje |
| 7 | Instrukcja i wydanie | Przewodnik zgodny z przetestowanym ISO, suma kontrolna i publikacja | Oczekuje |

## Następny krok: etap 5

Etap 4 zapisany na main w commicie `6c1cb87152f16593a90cc74e1aa8ed2284b6f48a`.
Walidacja GitHub Actions zaliczona: źródła, testy oraz przygotowanie profilu
na zainstalowanym pakiecie Archiso w oficjalnym kontenerze Arch Linux.
Następnie etap 5: ręczna budowa ISO konkretnego commita.

## Odzyskane zmiany i ich stan

- Budowanie, CI, test VM i konfiguracja konsoli: sprawdzone i zapisane w etapie 4.
- Dokumentacja: `README.md`, `docs/GUIDE_PL.md`, `docs/artwork-prompts.md`.
- Logo: `overlay/common/usr/share/pixmaps/ravnux-logo.png` — właściwa ozdobna wersja zapisana i potwierdzona na GitHubie w etapie 3.

## Zapis wykonania

- Etap 0: odnaleziono kopie robocze, sprawdzono listę niewysłanych zmian
  i zapisano ten plan. W tym etapie nie uruchamiano testów kodu ani budowania ISO.

- Etap 1: ukończony w commicie `f6dfad14b3ae58faaa73f2280f4c58eab0a9b9a6`.
  Helper obsługuje oddzielny docelowy magazyn kluczy przez `--gpgdir`.
  Instalator inicjalizuje go, dodaje klucze Arch i zweryfikowany klucz XLibre
  przed `pacstrap -K`, bez kopiowania prywatnego klucza środowiska live.
  Sprawdzono zgodność kolejności z kodem upstream:
  https://github.com/archlinux/arch-install-scripts/blob/master/pacstrap.in .
  Testy: 11/11 zaliczonych (w tym 5 dotyczących kluczy); walidacja źródeł
  `python scripts/check.py` zaliczona. Prawdziwy GPG potwierdził fingerprint
  dołączonego klucza: `0C92313001CFCA27627B9098B97F7C613F359424`.
  Testy obejmują niewłaściwy fingerprint, osobny keyring, błąd GPG
  i zatrzymanie przed podpisaniem przy błędzie importu.
  Ograniczenie: wywołania pacman-key w testach są symulowane;
  pełna instalacja i test ISO pozostają w etapach 5–6.

- Etap 2: ukończony w commicie `f0b1fcb50e8ac8223390043d1f1e5ed565c4031a`.
  Instalator odrzuca niepusty ESP, istniejące pliki w katalogu boot
  oraz dowiązania symboliczne boot/efi. Błąd odczytu katalogu przerywa
  instalację zamiast udawać pusty katalog. Kontrola odbywa się przed zapisami.
  Testy: 17/17 zaliczonych, bez pominięć; `python scripts/check.py` zaliczony.
  Sprawdzono istniejący loader EFI, loader Microsoft, ukryty plik EFI,
  plik GRUB, pliki istniejącego systemu, błąd odczytu, dowiązanie EFI
  i przejście kontroli dla pustego celu.
  Testy uruchamiają rzeczywistą funkcję walidacji instalatora na katalogach
  tymczasowych; nie wymagają tworzenia urządzeń blokowych.
  Pełny rozruch i instalacja na dysku VM nadal pozostają w etapach 5–6.

- Etap 3: ukończony. Użytkownik wgrał gotowy PNG w commicie
  `0834a411bdb65137f535fd2caf8de032f0204a93`. GitHub potwierdza blob
  `6a071f0b5c209bb43ef061cedd0f2ff4cdf7dee5`, identyczny z odzyskanym logo.
  Grafika: różowe R na purpurowym tle ze złotymi ornamentami, 1254x1254 RGB.
  SHA256: `41ad8a1dd956756ac076d1e5af0430e4508f89f118408553a98d415b2be24bd0`.
  PNG sprawdzony przez Pillow; referencje LightDM i ikony przewodnika zgodne.
  Kontrola źródeł i przygotowanego profilu `python3 scripts/check.py` zaliczona.
  `build.sh --prepare-only` potwierdził identyczne kopie logo w live i osadzonym
  root-overlay; rzeczywista komenda cp instalatora zachowała identyczny PNG.
  Test przygotowania używał wcześniejszego profilu jako szablonu releng,
  a nie świeżego upstream Archiso. Nie budowano ISO ani nie testowano GUI.
  Skrypty build/install i ukończone etapy 1–2 pozostały bez zmian.
  Grafikę przesłano jako plik, bez Base64 w czacie lub argumentach narzędzi.

- Etap 4: wykonany lokalnie na bazie `e603c00907b6b5b92de8ca9cd298c27ad6d0f5ad`.
  Dodano nbd do pakietów live; upstream hook archiso_pxe_nbd wymaga nbd-client.
  Przygotowanie profilu nie wymaga roota, odrzuca stare katalogi i dowiązania
  work/profile/out, sprawdza szablony i SOURCE_DATE_EPOCH przed zapisem.
  Nie używa stałego katalogu tymczasowego; zachowuje wyłącznie konfigurację
  initramfs i szablony startowe upstream, a nie użytkowników/usługi ratunkowe.
  Dodano konsolę szeregową do SYSLINUX, systemd-boot i szablonów GRUB;
  serial-getty czeka na utworzenie użytkownika live.
  Test VM ma limity czasu, KVM/TCG, buforowanie konsoli, jawne odrzucanie
  xorg-server/xf86-input-libinput, logi błędów i raport dopiero po sukcesie.
  Polecenia do VM są przesyłane jako tekst, bez Base64.
  Workflow oddziela walidację od ręcznej budowy ISO i opcjonalnych testów VM.
  Zachowuje logi również po błędzie; shell Bash z pipefail zachowuje wynik
  budowania przy tee. Nie publikuje wydania; uprawnienia contents pozostają read.
  README opisuje aktualny sposób budowania i testowania.
  Testy: 31/31 zaliczonych bez pominięć; kontrola źródeł i profilu zaliczona;
  składnia Python, YAML workflow i poleceń Bash zaliczona.
  Przygotowanie profilu sprawdzono na pobranych szablonach tekstowych upstream
  Archiso `723da192226e1c9d5def9168f13332793c82a85e`.
  Lokalnie użyto pobranych szablonów tekstowych. Następnie GitHub Actions
  potwierdził przygotowanie profilu na pełnym zainstalowanym pakiecie Archiso.
  Nie budowano ISO ani nie uruchomiono prawdziwych VM.
  Testy jednostkowe przygotowania używają kontrolowanego szablonu releng;
  testy logiki gościa VM symulują programy systemowe.
  Użytkownik zatwierdził zapis zmian do main 2026-10-04.
  Commit kodu: `6c1cb87152f16593a90cc74e1aa8ed2284b6f48a`.
  GitHub Actions: https://github.com/stainleSSStar/RAVNUX/actions/runs/37196053888 .
  Job validate zakończony sukcesem, wszystkie jego kroki zaliczone.
  Job iso pominięty zgodnie z ręcznym trybem budowania; etap 4 nie buduje ISO.
  Etap 5 nie został rozpoczęty.
