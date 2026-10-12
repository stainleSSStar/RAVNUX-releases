# RAVNUX — instrukcja użytkownika

RAVNUX to minimalny system x86_64 oparty na Arch Linux, z pulpitem XFCE,
Fish i ciemnym motywem w kolorach purpury i różu.

Ta instrukcja jest dostępna wyłącznie na live ISO przez `ravnux-guide`
lub menu aplikacji → „RAVNUX — user guide” (po polsku „instrukcja użytkownika”).
Nie jest kopiowana do systemu na dysku. Jeśli chcesz ją zachować,
przed restartem skopiuj plik `/usr/share/ravnux/guide-pl.md` na własny nośnik.

Nawigacja: strzałki / Page Up / Page Down — przewijanie; / — szukanie;
n — następny wynik; g — początek; G — koniec; q — zamknięcie instrukcji.
Polecenia wykonuj w drugim oknie terminala albo po zamknięciu instrukcji.

## 1. Najkrótsza droga do instalacji

1. Uruchom ISO, najlepiej w trybie UEFI, i poczekaj na pulpit.
2. Połącz się z internetem przez ikonę sieci albo `nmtui`.
3. Otwórz Terminal z menu z ikoną R i wpisz `sudo ravnux-install`.
4. Wybierz dysk i podaj nazwę komputera, użytkownika oraz strefę czasową.
5. Sprawdź podsumowanie, potwierdź skasowanie dysku i rozpoczęcie instalacji.
6. Ustaw hasło konta. Po zakończeniu wybierz restart i wyjmij nośnik live.
7. Zaloguj się swoim nowym kontem.

**Kreator usuwa wszystkie dane i partycje z wybranego dysku.**
Jeżeli chcesz zachować istniejący system lub pliki na tym dysku,
nie potwierdzaj kasowania. Przed instalacją wykonaj kopię potrzebnych danych.

## 2. Co przygotować

- Komputer Intel/AMD x86_64. Obraz nie jest przeznaczony dla Apple Silicon.
- Dysk docelowy o pojemności co najmniej 32 GiB, przeznaczony w całości na RAVNUX.
- Działające połączenie z internetem: instalator pobiera pakiety z repozytoriów.
- Nazwę komputera, nazwę konta i hasło, które ustawisz podczas instalacji.

ISO obsługuje UEFI i BIOS. Aby zainstalować system w UEFI, wybierz w menu
rozruchowym komputera wpis USB oznaczony UEFI. Secure Boot musi być wyłączony.
Jeśli komputer uruchomi ISO w BIOS, kreator przygotuje instalację BIOS.
Tryb jest wykrywany automatycznie i wyświetlany przed wyborem dysku.

Nie musisz sam tworzyć ani formatować partycji. Kreator robi to po potwierdzeniu.
Nie tworzy szyfrowania, LVM, RAID, dual boot, osobnego `/home` ani swapu.
Hibernacja wymaga późniejszej konfiguracji.

## 3. Sesja live i internet

Live loguje automatycznie konto `ravnux`; sudo nie wymaga w niej hasła.
Pliki zapisane w katalogu domowym i zmiany ustawień live znikną po restarcie.
Instalator nie przenosi Twoich plików z live do nowego konta na dysku.

Ethernet zwykle łączy się automatycznie. Wi-Fi wybierz z ikony sieci w panelu.
Możesz też otworzyć tekstowe ustawienia sieci:

```sh
nmtui
```

Wybierz „Activate a connection”, swoją sieć i wpisz hasło.
Wyjdź do terminala przed uruchomieniem instalatora.
Po instalacji może być potrzebne ponowne połączenie z Wi-Fi:
profile sieciowe z sesji live nie są kopiowane na dysk.

Domyślna powłoka to Fish. Polecenia z tej instrukcji możesz wpisywać bezpośrednio
w terminalu; nie wymagają przełączania na Bash.

## 4. Kreator instalacji krok po kroku

Uruchom z terminala w sesji live:

```sh
sudo ravnux-install
```

Polecenie bez argumentów otwiera interaktywny kreator. Możesz także użyć
`sudo ravnux-setup` — to ten sam kreator.

### Wybór dysku

Kreator pokazuje nazwy dysków, pojemność, model i sposób podłączenia.
Wpisz ścieżkę całego dysku, np. `/dev/nvme0n1` lub `/dev/sda`.
Nazwy są przykładami: wybieraj na podstawie modelu i pojemności swojego urządzenia.
Partycja taka jak `/dev/nvme0n1p2` nie jest całym dyskiem.

Dyski zamontowane, aktywny swap, urządzenia tylko do odczytu i aktywne
mapowania LVM/LUKS/RAID zostaną odrzucone. Dotyczy to także zamontowanego
nośnika, z którego działa live ISO. Kreator nie odmontowuje ich automatycznie.

### Nazwa komputera, konto i strefa czasowa

- „Computer name”: nazwa komputera, domyślnie `ravpc`; użyj liter, cyfr i myślników.
- „Username”: Twoje konto, np. `bystander`; użyj małych liter i cyfr,
  zacznij od litery. Nazwy `root` i `ravnux` są zarezerwowane.
- „Timezone”: domyślnie `Europe/Warsaw`; Enter zachowuje wartość domyślną.

### Potwierdzenia i zapis na dysk

Kreator ponownie pokazuje wybrany dysk i plan instalacji.
Dopiero wpisanie dokładnego `ERASE` wraz z jego ścieżką pozwala go skasować,
np. `ERASE /dev/nvme0n1`. Każdy inny tekst anuluje operację.

Powstaje tablica partycji GPT oraz:

- UEFI: partycja EFI 1 GiB FAT32 i root ext4 na pozostałym miejscu;
- BIOS: partycja BIOS boot 2 MiB i root ext4 na pozostałym miejscu.

Następnie właściwy instalator pokazuje partycję root i prosi o `INSTALL`.
Na tym etapie partycje są już przygotowane i wcześniejsze dane zostały usunięte.
Wpisz `INSTALL`, aby rozpocząć pobieranie pakietów i konfigurację systemu.

Podaj hasło nowego konta dwukrotnie. Podczas wpisywania nie widać znaków — to normalne.
Poczekaj na zakończenie instalacji. Kreator odmontuje system i zapyta
„Restart now? [y/N]”. Wpisz `y`, aby uruchomić komputer ponownie,
albo Enter, aby pozostać w live. Wyjmij USB podczas restartu.

Jeżeli pojawi się błąd, zachowaj jego dokładny komunikat.
Instalator nie cofa zapisanych zmian. Ponowne uruchomienie kreatora i potwierdzenie
kasowania usunie cały wybrany dysk jeszcze raz.

Tryb zaawansowany dla własnych, wcześniej przygotowanych pustych partycji
opisuje `ravnux-install --help`. Wywołanie instalatora
z argumentami nie partycjonuje ani nie formatuje dysku.

## 5. Pierwsze logowanie i zawartość systemu

Na dysku logujesz się kontem utworzonym w kreatorze, z ustawionym hasłem.
Sudo pyta o hasło tego samego konta. Nie ma autologowania ani konta live `ravnux`.
Interfejs jest domyślnie angielski, a polskie locale również jest wygenerowane.

Zainstalowany system zawiera podstawę Arch Linux, kernel, firmware,
mikrokod CPU, otwarte sterowniki grafiki Mesa/XLibre, sieć i Wi-Fi,
Bluetooth, dźwięk PipeWire, pulpit XFCE, menedżer plików Thunar i terminal z Fish.
Wymagane zależności tych pakietów są instalowane automatycznie.

Przeglądarkę, edytor, aplikacje do pracy, gry, dodatkowe sterowniki Vulkan
lub własnościowy sterownik NVIDIA doinstalujesz według potrzeb.
Nie ma sklepu z aplikacjami ani helpera AUR.
Guide, kreator, narzędzia instalacji i dodatkowe narzędzia diagnostyczne live
nie są kopiowane na dysk. Brak `ravnux-guide` po instalacji jest zamierzony.

## 6. Aktualizacje i własne aplikacje

RAVNUX jest systemem rolling release opartym na Arch Linux.
Aktualizacje wykonujesz samodzielnie. Pełna aktualizacja systemu:

```sh
sudo pacman -Syu
```

Aby znaleźć pakiet, użyj wyszukiwania, np.:

```sh
pacman -Ss firefox
```

Aby zainstalować wybraną aplikację wraz z zależnościami, np. przeglądarkę:

```sh
sudo pacman -S --needed firefox
```

To przykłady, nie lista wymaganych aplikacji. Przed instalowaniem nowych pakietów
wykonaj pełną aktualizację. Nie używaj samego `pacman -Sy` do odświeżania baz
bez aktualizacji systemu. Czytaj komunikaty i podsumowanie transakcji pacmana.
Repozytorium stable XLibre i klucze podpisów są już skonfigurowane przez instalator.

## 7. Codzienne ustawienia pulpitu

- Tapeta: prawy przycisk na pulpicie → Desktop Settings → Background.
  Domyślna grafika znajduje się w `/usr/share/backgrounds/ravnux/cyberpunk-city.jpg`.
  Późniejszy wybór własnej tapety zostaje zachowany.
- Rozdzielczość, skalowanie i monitory: Settings → Display.
- Panel: prawy przycisk na panelu → Panel → Panel Preferences.
- Dźwięk i mikrofon: ikona głośności albo `pavucontrol`; wybierz wyjście,
  wejście i upewnij się, że nie są wyciszone.
- Bluetooth: Bluetooth Manager z menu aplikacji.
- Terminal: Edit → Preferences → Appearance; możesz zmienić font,
  kolory i przezroczystość.
- Kompozytor i cienie: Settings → Window Manager Tweaks → Compositor.
  Kompozytor XFWM jest domyślnie włączony. Możesz go wyłączyć w tym miejscu,
  jeśli chcesz zrezygnować z efektów.

Panel ma subtelnie przezroczyste tło, a terminal domyślnie 90% krycia.
Nie jest potrzebny dodatkowy kompozytor.

## 8. Gdzie wrócić po pomoc

Pobieranie ISO i kopii instrukcji (plik GUIDE_PL.md w zasobach wydania):
https://github.com/stainleSSStar/RAVNUX-releases/releases/latest

Składnia zarządzania pakietami:
https://man.archlinux.org/man/pacman.8.en

Ustawienia kompozytora XFCE:
https://docs.xfce.org/xfce/xfwm4/wmtweaks

Jeśli coś przestanie działać, zanotuj czynność, po której pojawił się problem,
i dokładny komunikat błędu. Diagnostykę CLI można wtedy dobrać do konkretnej
usterki; nie musisz wykonywać testów sprzętu ani zbierać raportów przed instalacją.
