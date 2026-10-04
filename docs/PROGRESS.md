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
| 3 | Ozdobne logo R ze złotymi wzorami | Porównanie odzyskanej grafiki z GitHubem, kontrola integracji, zapis | Następny |
| 4 | Budowanie i CI | Przegląd nbd, testu VM, konsoli szeregowej i workflow, zapis | Oczekuje |
| 5 | Budowa ISO | Udany build konkretnego commita, zapis przebiegu i artefaktu | Oczekuje |
| 6a | Rozruch BIOS | Test VM i zapis wyniku | Oczekuje |
| 6b | Rozruch UEFI | Test VM i zapis wyniku | Oczekuje |
| 6c | Instalacja | Instalacja na pustym dysku VM i start z dysku | Oczekuje |
| 7 | Instrukcja i wydanie | Przewodnik zgodny z przetestowanym ISO, suma kontrolna i publikacja | Oczekuje |

## Następny krok: etap 3

Porównać odzyskane logo R ze złotymi wzorami z plikiem na GitHubie:
`overlay/common/usr/share/pixmaps/ravnux-logo.png`.
Sprawdzić wygląd i integrację z pulpitem oraz instalacją; zapisać właściwą grafikę
i wynik kontroli. Nie zastępować gotowej grafiki bez potrzeby.
Bazować na bieżącym main, zachowując ukończone poprawki kluczy i ochrony EFI.

## Pozostałe odzyskane zmiany do późniejszego sprawdzenia

- Budowanie: `scripts/build.sh`, `packages/live.txt`, `.github/workflows/iso.yml`, `scripts/check.py` (walidacja nbd należy do etapu 4).
- Nowy test: `scripts/vm-smoke.py`.
- Konfiguracja konsoli: `overlay/live/etc/systemd/system/serial-getty@ttyS0.service.d/`.
- Dokumentacja: `README.md`, `docs/GUIDE_PL.md`, `docs/artwork-prompts.md`.
- Logo: `overlay/common/usr/share/pixmaps/ravnux-logo.png` — obecność lokalnego pliku nie potwierdza wysłania właściwej wersji.

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
