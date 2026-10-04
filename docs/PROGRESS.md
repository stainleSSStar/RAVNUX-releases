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
| 1 | Klucze XLibre | Przegląd poprawki, testy keyring, zapis zmian | Następny |
| 2 | Ochrona partycji EFI | Przegląd instalatora, test odrzucenia zajętej EFI, zapis | Oczekuje |
| 3 | Ozdobne logo R ze złotymi wzorami | Porównanie odzyskanej grafiki z GitHubem, kontrola integracji, zapis | Oczekuje |
| 4 | Budowanie i CI | Przegląd nbd, testu VM, konsoli szeregowej i workflow, zapis | Oczekuje |
| 5 | Budowa ISO | Udany build konkretnego commita, zapis przebiegu i artefaktu | Oczekuje |
| 6a | Rozruch BIOS | Test VM i zapis wyniku | Oczekuje |
| 6b | Rozruch UEFI | Test VM i zapis wyniku | Oczekuje |
| 6c | Instalacja | Instalacja na pustym dysku VM i start z dysku | Oczekuje |
| 7 | Instrukcja i wydanie | Przewodnik zgodny z przetestowanym ISO, suma kontrolna i publikacja | Oczekuje |

## Następny krok: etap 1

Przejrzeć odzyskane zmiany w:
- `overlay/common/usr/local/bin/ravnux-keyring-init`;
- `tests/test_keyring.py`;
- powiązanej walidacji w `scripts/check.py`.

Porównać je z bieżącym main, uruchomić testy dotyczące kluczy
i zapisać wyłącznie sprawdzone zmiany tego etapu.
Nie nadpisywać historii repozytorium lokalnym snapshotem.

## Pozostałe odzyskane zmiany do późniejszego sprawdzenia

- Instalator i testy: `scripts/install.sh`, `tests/test_installer.py`.
- Budowanie: `scripts/build.sh`, `packages/live.txt`, `.github/workflows/iso.yml`.
- Nowy test: `scripts/vm-smoke.py`.
- Konfiguracja konsoli: `overlay/live/etc/systemd/system/serial-getty@ttyS0.service.d/`.
- Dokumentacja: `README.md`, `docs/GUIDE_PL.md`, `docs/artwork-prompts.md`.
- Logo: `overlay/common/usr/share/pixmaps/ravnux-logo.png` — obecność lokalnego pliku nie potwierdza wysłania właściwej wersji.

## Zapis wykonania

- Etap 0: odnaleziono kopie robocze, sprawdzono listę niewysłanych zmian
  i zapisano ten plan. W tym etapie nie uruchamiano testów kodu ani budowania ISO.
