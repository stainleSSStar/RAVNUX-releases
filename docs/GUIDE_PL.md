# RAVNUX — od startu ISO do testów po instalacji

Ta instrukcja dotyczy NOWEGO ISO z XLibre. Starsze ISO trzeba zbudować ponownie.
Najprostsza ścieżka: komputer x86_64, UEFI, pusty dysk testowy, root ext4.
Wyłącznie w sesji live instrukcja jest dostępna offline z menu aplikacji „RAVNUX — test and installation guide” albo komendą `ravnux-guide` (wyjście klawiszem q).

## 1. Uruchom ISO i otwórz terminal

W menu boot wybierz zwykły wpis RAVNUX. Po uruchomieniu powinien pojawić się XFCE i konto live `ravnux`, bez pytania o hasło.

Otwórz Terminal z menu z ikoną R. Domyślna powłoka to Fish. Żeby wszystkie poniższe bloki działały dokładnie tak samo, wpisz:

```sh
bash
```

Dalsze polecenia wpisuj w tym terminalu. Po pierwszym uruchomieniu zainstalowanego systemu również wpisz `bash` przed blokami z tej instrukcji.

## 2. Sprawdź, czy uruchomiony jest właściwy system i XLibre

```sh
cat /etc/os-release
printf 'Sesja: %s\n' "$XDG_SESSION_TYPE"
pacman -Q xlibre-xserver xlibre-input-libinput
xdpyinfo | grep -i vendor
```

Oczekiwane: RAVNUX, sesja `x11`, dwa pakiety XLibre i vendor zawierający `XLibre`.
Sprawdź też brak starego serwera:

```sh
pacman -Q xorg-server
```

Oczekiwany błąd „package 'xorg-server' was not found” — tutaj oznacza poprawny wynik. Biblioteki libX11 i narzędzia o nazwach `xorg-*` mogą pozostać: są klientami X11, a serwerem jest XLibre.

## 3. Podłącz internet

Z kablem Ethernet najpierw wpisz:

```sh
nmcli device status
getent hosts archlinux.org
curl -I --max-time 15 https://archlinux.org
```

Powinno być połączenie `connected`, adresy IP domeny i odpowiedź HTTP.
Jeśli używasz Wi-Fi:

```sh
nmtui
```

Wybierz „Activate a connection”, swoją sieć i wpisz hasło. Wyjdź z nmtui, potem powtórz `getent` oraz `curl` powyżej.

Sprawdź datę i synchronizację:

```sh
timedatectl status
```

Jeżeli data jest błędna, przed instalacją doprowadź zegar do właściwej daty; pobieranie HTTPS i podpisy pakietów wymagają poprawnego czasu.

## 4. Przetestuj pulpit, grafikę i wejście

```sh
xrandr --query
lspci -k
```

Sprawdź ręcznie:

- Czy widzisz purpurowe miasto, różowe logo R, panel i purpurowo-różowy terminal.
- Czy mysz, klawiatura, touchpad, scroll i klawisze głośności/jasności działają.
- Czy okna da się przesuwać, maksymalizować i zamykać.
- Czy rozdzielczość i drugi monitor działają w Settings → Display.
- Czy menu aplikacji, Thunar i ustawienia działają bez zawieszeń.

Kompozytor XFWM jest domyślnie włączony. Panel ma lekko przezroczyste tło, terminal 90% krycia, a okna subtelne cienie. Jeśli sterownik sprawia problemy, wyłącz go w Settings → Window Manager Tweaks → Compositor. Nie jest potrzebny osobny kompozytor.

## 5. Przetestuj dźwięk i mikrofon

```sh
wpctl status
pavucontrol
```

W pavucontrol wybierz właściwe wyjście, profil karty oraz mikrofon. Wyłącz wyciszenie. Zamknij okno i uruchom test głośników:

```sh
speaker-test -D default -c 2 -t wav -l 1
```

Oczekiwane: komunikaty/dźwięk lewego i prawego kanału. Jeżeli program nie kończy się lub chcesz go przerwać, użyj Ctrl+C.

Nagraj 5 sekund mikrofonu, mówiąc do niego:

```sh
arecord -D default -f S16_LE -r 48000 -c 1 -d 5 "$HOME/ravnux-mic.wav"
aplay -D default "$HOME/ravnux-mic.wav"
```

Powinieneś usłyszeć nagranie. Jeśli mikrofon albo wyjście jest błędne, zmień je w pavucontrol i powtórz test. Sprawdź także słuchawki, HDMI i Bluetooth, jeśli ich używasz.

## 6. Bluetooth, USB i usypianie

```sh
systemctl status bluetooth --no-pager
bluetoothctl list
lsusb
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS,MODEL
```

Parowanie przetestuj przez aplikację Bluetooth Manager. Włóż pendrive i otwórz go w Thunarze; sprawdź odczyt oraz bezpieczne odmontowanie.

Na laptopie sprawdź jasność, zasilanie z baterii i zamknięcie pokrywy. Usypianie testuj po zapisaniu wyników:

```sh
systemctl suspend
```

Wybudź komputer i powtórz krótki test obrazu, sieci i dźwięku. Niektóre maszyny wirtualne nie udostępniają usypiania ani Bluetooth — te próby zostaw do realnego sprzętu.

## 7. Zapisz raport z sesji live

```sh
mkdir -p "$HOME/ravnux-test"
uname -a > "$HOME/ravnux-test/kernel.txt"
pacman -Q > "$HOME/ravnux-test/packages.txt"
lspci -k > "$HOME/ravnux-test/pci.txt"
lsusb > "$HOME/ravnux-test/usb.txt"
xrandr --query > "$HOME/ravnux-test/displays.txt"
wpctl status > "$HOME/ravnux-test/audio.txt"
nmcli device status > "$HOME/ravnux-test/network.txt"
systemctl --failed --no-pager > "$HOME/ravnux-test/failed-units.txt"
sudo journalctl -b --no-pager > "$HOME/ravnux-test/journal.txt"
```

Skopiuj katalog `ravnux-test` na drugi nośnik przez Thunar. Dane w sesji live znikną po restarcie. Pliki mogą zawierać nazwy urządzeń/sieci — przejrzyj je przed udostępnieniem.

## 8. Interaktywna instalacja na cały dysk

Wyjdź z instrukcji klawiszem q lub otwórz drugi terminal. Podłącz internet i uruchom:

```sh
sudo ravnux-install
```

To otwiera kreator CLI (`sudo ravnux-setup` uruchamia ten sam kreator). **Cały wybrany dysk zostanie skasowany. Nie używaj tej ścieżki do dual boot ani zachowania istniejących danych.** Wymagane minimum: 32 GiB. Dysk live USB, zamontowane partycje, aktywny swap, urządzenia tylko do odczytu i mapowania LVM/LUKS/RAID zostaną odrzucone.

1. Wskaż cały dysk na podstawie rozmiaru i modelu, np. `/dev/nvme0n1`.
2. Wpisz nazwę komputera, nazwę użytkownika i strefę czasową (domyślna Europe/Warsaw). `root` i `ravnux` są zarezerwowane.
3. Sprawdź podsumowanie. Dopiero wpisanie dokładnego `ERASE /dev/...` pozwala skasować dysk.
4. Kreator utworzy GPT. Dla UEFI: EFI 1 GiB FAT32 i root ext4; dla BIOS: BIOS boot 2 MiB i root ext4. Sam je sformatuje i zamontuje.
5. Właściwy instalator pokaże root: wpisz `INSTALL`, aby rozpocząć pobieranie pakietów.
6. Ustaw hasło konta, wpisując je dwukrotnie.
7. Po komunikacie sukcesu kreator odmontuje system i zapyta o restart. Wyjmij nośnik live podczas restartu.

Aby zainstalować UEFI, uruchom ISO w UEFI. Secure Boot nie jest skonfigurowany. Na maszynie uruchomionej w BIOS kreator instaluje BIOS. Nie tworzy szyfrowania ani swapu; dodatkowe aplikacje doinstalujesz samodzielnie.

Po błędzie nie restartuj od razu: zapisz komunikat i sprawdź `/mnt`. Nie ma automatycznego cofania zmian. Kolejna próba kreatora od początku ponownie kasuje cały wybrany dysk.

Instalację na wcześniej przygotowanych pustych partycjach nadal obsługuje `ravnux-install` z argumentami; patrz [README — instalacja na dysk](../README.md#instalacja-na-dysk). Ten tryb nie formatuje i nie partycjonuje.

## 9. Test po instalacji

Otwórz terminal i wpisz `bash`, potem:

```sh
cat /etc/os-release
printf 'Powłoka użytkownika: '
getent passwd "$USER" | cut -d: -f7
pacman -Q xlibre-xserver xlibre-input-libinput
systemctl --failed --no-pager
nmcli device status
wpctl status
sudo -k
sudo true
```

Oczekiwane: RAVNUX, `/usr/bin/fish`, pakiety XLibre, działająca sieć i dźwięk oraz pytanie sudo o hasło. Polecenie `bash` zmienia tylko bieżącą powłokę; nie zmienia domyślnego Fish.

Sprawdź brak konta i przywilejów live:

```sh
if getent passwd ravnux; then echo 'BŁĄD: konto live zostało w systemie'; else echo 'OK: brak konta live'; fi
if test -e /etc/sudoers.d/10-ravnux-live; then echo 'BŁĄD: sudo live zostało w systemie'; else echo 'OK: brak sudo live'; fi
```

Powtórz test dźwięku/mikrofonu i ręczne testy pulpitu. `lspci`, `lsusb` i `xdpyinfo` są dodatkowymi narzędziami ISO; nie muszą być zainstalowane na dysku. `ravnux-guide`, pozycja menu instrukcji i instalatory nie są kopiowane na dysk. Testy `speaker-test` i `arecord` wymagają doinstalowania `alsa-utils`; w systemie pozostaje panel dźwięku i pavucontrol.

Na końcu zmień tapetę w ustawieniach, wyloguj się i zaloguj — własny wybór powinien pozostać. Wykonaj pełne wyłączenie i ponowne uruchomienie komputera.

## Gdy nie pojawia się pulpit

Na nowym ISO przejdź do konsoli przez Ctrl+Alt+F2, zaloguj się jako `ravnux` bez hasła i wpisz:

```sh
sudo systemctl status ravnux-live-setup lightdm --no-pager
sudo journalctl -b -u lightdm --no-pager
sudo journalctl -b -k --no-pager
```

Nie kasuj sterowników na ślepo. Zapisz błąd i model GPU. Na zainstalowanym systemie logujesz się swoim kontem i hasłem; usługa `ravnux-live-setup` nie jest tam obecna.

## Źródła konfiguracji XLibre

- https://xlibre-arch.github.io/ — repozytorium stable i podpisy pakietów.
- https://packages.xlibre.net/arch/stable/x86_64/ — binarne pakiety XLibre dla Arch.
- https://wiki.archlinux.org/title/Installation_guide — partycje i podstawy instalacji Arch.
