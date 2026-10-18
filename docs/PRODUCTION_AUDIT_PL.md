# Ponowny audyt przed wdrożeniem — 2026-10-18

Punkt odniesienia: scalony `main` 4366253 oraz opublikowany obraz
`v2026.10.18-r64` (SHA-256
`868877fd63ce8a9cfa9eec54f0c21bac60598999bb79af33e6bb6691e1e6df72`).
Audyt opublikowanego ISO używa pobranego obrazu i `sha256sum -c`, a nie
nowego obrazu o zmienionej zawartości.

## Wykryte problemy i poprawki

1. **Stan degraded sesji live UEFI.** Logi r64 zawierają błędy
   `systemd-loop@…sr0.service`. To znany problem systemd 262: automatyczna
   analiza dysku oczekuje Discoverable Disk Image, podczas gdy Archiso ma
   squashfs wewnątrz ISO9660. Start systemu mimo tego się udaje.
   Wąska reguła udev dotyczy wyłącznie napędu optycznego z ISO9660 i blokuje
   zbędne żądanie tej automatycznej operacji. Nie maskuje usług, nie czyści
   listy błędów i nie trafia do systemu zainstalowanego na dysku.
   Źródło: https://github.com/systemd/systemd/issues/43605 .

2. **Sprawdzone podejrzenie utraty identyfikacji po aktualizacji.** Prawdziwa
   reinstalacja `filesystem` nie odtworzyła tego problemu: pakiet posiada
   `/usr/lib/os-release`, a zwykły plik RAVNUX w `/etc/os-release` został
   zachowany. Nie dodano więc zbędnego hooka ani helpera. Test regresji
   rzeczywistą transakcją pacmana pozostaje w CI i próbie aktualizacji VM.

3. **Brak dodatkowych pozycji menu EFI.** Usunięty w poprzednim audycie
   `efibootmgr` nie jest wymagany przez instalację `--no-nvram`, lecz używa go
   generator menu GRUB. Wrócił do zestawu instalowanego warunkowo przy UEFI.
   BIOS go nie potrzebuje; instalator nadal nie zapisuje wpisów rozruchu NVRAM.

4. **Fałszywie udany test odmontowania.** Test VM miał fallback `umount -Rl`.
   Usunięto go: zajęty root kończy próbę błędem i nie może dać raportu PASS.
   Kreator produkcyjny już wcześniej odmontowywał bez wymuszania.

5. **Niepełna weryfikacja zainstalowanego pulpitu.** Poprzedni test sprawdzał
   LightDM i logowanie szeregowe, ale nie logował się przez greeter. Nowy
   wykonuje rzeczywiste wpisanie loginu/hasła przez wirtualną klawiaturę,
   sprawdza XFCE, XLibre, motyw, jeden agent PolicyKit, autoryzację graficzną,
   blokowanie/odblokowanie ekranu, audio i sudo wymagające hasła.

6. **Aktualizacja i kolejny rozruch.** Próba uruchamia pełne `pacman -Syu`,
   reinstaluje `filesystem` oraz kernel, sprawdza branding, initramfs i składnię
   GRUB, po czym ponownie uruchamia dysk i ponawia logowanie do pulpitu.

7. **Publikacja niekompletnego latest.** Wcześniej release stawał się publiczny
   przed uploadem ISO. Teraz powstaje prywatny draft; publiczna publikacja
   następuje po wysłaniu wszystkich plików i lokalnej kontroli sumy ISO.
   Nieudany upload pozostawia draft, a błędna/pusta zawartość nie tworzy release.
   Status latest wymaga obu trybów live/instalacji i rozszerzonego audytu.

8. **Drobne konfiguracje.** Jawne `KEYMAP=us` usuwa ostrzeżenie initramfs o
   braku `/etc/vconsole.conf`. Katalog sudoers otrzymuje tryb 0750, a reguła
   wheel nadal 0440. Instrukcja podaje faktyczne krycie terminala: 88%.

9. **Wyścig inicjalizacji tapety.** W rzeczywistej instalacji XFCE zdążyło
   zapisać własną domyślną tapetę przed helperem RAVNUX. Helper traktował ją
   jak ustawienie użytkownika. Przed pierwszym znacznikiem inicjalizacji
   zastępuje teraz również domyślne obrazy z `/usr/share/backgrounds/xfce/`.
   Zachowuje własne zdjęcia użytkownika, a po inicjalizacji nie zmienia tapety.
   Test regresji obejmuje ten wyścig, a test instalacji kontroluje tapetę.

## Zakres i odtwarzalność testów

- Testy źródeł i regresji, prawdziwa reinstalacja pakietu w kontenerze Arch,
  kontrola składni reguły udev, przygotowanie aktualnego profilu Archiso.
- BIOS i UEFI live: brak usług systemowych w stanie failed, sieć, XFCE/XLibre,
  brak listenera SSH/TCP X11, agent PolicyKit i usługi audio.
- BIOS i UEFI na pustych dyskach VM: instalacja, odmontowanie bez lazy/force,
  prawdziwe logowanie LightDM, autoryzacja i blokada ekranu oraz test aktualizacji.
- Testy nie dodają pakietów do dystrybucji. Pillow/QEMU są narzędziami runnera.
  Na dysku VM instrumentacja testowa włącza konsolę szeregową i manualne pole
  nazwy użytkownika w greeterze; nie ustawia autologowania ani NOPASSWD.
- Zrzuty `vm-install-…-desktop.png` pochodzą z rzeczywistego zainstalowanego
  RAVNUX w QEMU. Nie są makietą ani podglądem widgetów Ubuntu.

Wynik audytu należy odczytywać z raportów dla konkretnego commitu/ISO.
Dotychczasowe PASS r64 dotyczyło węższego zestawu testów.
Nie jest to certyfikat braku wszystkich błędów lub luk bezpieczeństwa.

## Pozostałe ograniczenia

Testy VM nie potwierdzają działania fizycznego GPU, radia Wi-Fi/Bluetooth,
audio, USB ani suspend/resume na docelowej maszynie. Secure Boot, dual boot,
szyfrowanie i LVM nie są skonfigurowane przez instalator.

Ostrzeżenia o firmware niektórych wyspecjalizowanych kontrolerów nie oznaczają,
że każdy komputer będzie ich potrzebował. Pozostawiono minimalny zestaw i nie
instalowano w ciemno dodatkowych sterowników. Konkretne wymagania zależą od
sprzętu docelowego.

Testy rozszerzone korzystają z dysku SATA/AHCI w BIOS oraz NVMe w UEFI i emulowanego dźwięku Intel HDA. Klient PipeWire i pavucontrol uruchamiają stos audio przed kontrolą każdej usługi osobno; bezczynność przed aktywacją gniazda nie jest traktowana jako awaria. Instalacja wymaga dozwolonego dostępu do repozytoriów Arch Linux i XLibre.
