# RAVNUX — od startu ISO do testów po instalacji

Ta instrukcja dotyczy NOWEGO ISO z XLibre. Starsze ISO trzeba zbudować ponownie.
Najprostsza ścieżka: komputer x86_64, UEFI, pusty dysk testowy, root ext4.
Instrukcja jest dostępna offline z menu aplikacji „RAVNUX — test and installation guide” albo komendą `ravnux-guide` (wyjście klawiszem q).

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

Kompozytor jest celowo wyłączony, dlatego brak efektów przezroczystości nie jest błędem.

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

## 8. Instalacja — tylko jeśli chcesz już zapisać system na dysku

Najpierw wyjdź z przeglądania tej instrukcji, jeśli otworzyłeś ją w `less` (q), albo użyj drugiego terminala. Zostań w Bash.

Sprawdź, czy ISO uruchomiono w UEFI:

```sh
test -d /sys/firmware/efi && echo UEFI || echo BIOS
```

Dalszy przykład jest wyłącznie dla UEFI. Dla wyniku BIOS uruchom ISO w UEFI albo użyj opisu BIOS w README.

Pokaż dyski i wybierz DYSK TESTOWY, nie pendrive z ISO:

```sh
lsblk -d -o NAME,SIZE,MODEL,TRAN
```

Potrzebujesz GPT i dwóch partycji:

| Partycja | Rozmiar | Format | Montowanie |
| --- | --- | --- | --- |
| EFI System Partition | 1 GiB | FAT32 | /mnt/boot/efi |
| Root | Reszta dysku, proponowane minimum 30 GiB | ext4 | /mnt |

Jeśli partycje są już przygotowane i puste, pomiń następny blok i przejdź do kroku 9.

### Utworzenie partycji na całym pustym dysku testowym

TEN BLOK KASUJE UKŁAD PARTYCJI I DANE NA WYBRANYM DYSKU. Wymaga wpisania jego ścieżki oraz osobnego potwierdzenia. Nie używaj go do dual boot ani dysku z danymi. Dysk musi być odmontowany i nie może mieć aktywnego swap.

Najpierw:

```sh
sudo -i
```

Teraz jesteś w Bash jako root. Wklej cały blok naraz:

```bash
prepare_test_disk() {
    test -d /sys/firmware/efi || { echo 'Uruchom ISO w UEFI.'; return 1; }
    read -r -p 'Dysk testowy, np. /dev/nvme0n1 lub /dev/sda: ' DISK
    [[ -b "$DISK" && "$(lsblk -dn -o TYPE "$DISK")" == disk ]] || { echo 'To nie jest cały dysk.'; return 1; }
    lsblk -o NAME,SIZE,MODEL,FSTYPE,MOUNTPOINTS "$DISK"
    if lsblk -n -o MOUNTPOINTS "$DISK" | grep -q '[^[:space:]]'; then
        echo 'Dysk ma zamontowane partycje lub swap. Przerywam.'
        return 1
    fi
    read -r -p "Aby skasować ten dysk, wpisz KASUJ $DISK: " CONFIRM
    [[ "$CONFIRM" == "KASUJ $DISK" ]] || { echo 'Anulowano.'; return 1; }
    parted -s "$DISK" mklabel gpt || return 1
    parted -s "$DISK" mkpart ESP fat32 1MiB 1025MiB || return 1
    parted -s "$DISK" set 1 esp on || return 1
    parted -s "$DISK" mkpart primary ext4 1025MiB 100% || return 1
    partprobe "$DISK" || return 1
    udevadm settle || return 1
    if [[ "$DISK" == *[0-9] ]]; then
        EFI="${DISK}p1"; ROOT="${DISK}p2"
    else
        EFI="${DISK}1"; ROOT="${DISK}2"
    fi
    mkfs.fat -F 32 "$EFI" || return 1
    mkfs.ext4 "$ROOT" || return 1
    printf 'EFI: %s\nROOT: %s\n' "$EFI" "$ROOT"
}
prepare_test_disk
```

Kontynuuj tylko jeśli oba formatowania zakończyły się powodzeniem. Funkcja niczego nie montuje i nie uruchamia instalacji. Nie wykonuj bloku drugi raz po zainstalowaniu systemu.

## 9. Zamontuj partycje

Jeżeli jesteś już root z poprzedniego kroku, zostań w tej powłoce. W przeciwnym razie uruchom `sudo -i`.

Wpisz ścieżki własnych partycji; przykłady to `/dev/nvme0n1p1` i `/dev/nvme0n1p2`:

```bash
read -r -p 'Partycja ROOT: ' ROOT
read -r -p 'Partycja EFI: ' EFI
mount "$ROOT" /mnt && mkdir -p /mnt/boot/efi && mount "$EFI" /mnt/boot/efi
findmnt -R /mnt
```

Oczekiwane: root ext4 w `/mnt`, EFI vfat w `/mnt/boot/efi`. Nie uruchamiaj instalatora po błędzie montowania.

## 10. Zainstaluj RAVNUX

```sh
ravnux-install --hostname ravpc --username bystander --timezone Europe/Warsaw
```

To gotowy przykład. Jeśli chcesz inną nazwę komputera albo konta, zmień `ravpc` i `bystander` przed wykonaniem.

1. Sprawdź wyświetlone urządzenie root.
2. Wpisz `INSTALL`.
3. Poczekaj na pobranie pakietów i konfigurację systemu.
4. Podaj dwukrotnie hasło konta `bystander`.
5. Kontynuuj dopiero po komunikacie `Installation complete`.

Repozytorium stable XLibre, podpisy pakietów, Fish, motyw i grafiki są konfigurowane automatycznie. Nie dopisuj repozytoriów ani kluczy ręcznie.

Jeżeli pojawi się błąd, NIE restartuj od razu — zapisz komunikat. Instalator nie cofa zapisanych plików. Ponowne uruchomienie wymaga pustego root albo ręcznej naprawy częściowej instalacji.

## 11. Odmontuj i uruchom system z dysku

```sh
umount -R /mnt && reboot
```

Wyjmij pendrive/odłącz ISO przy restarcie. Uruchom system z dysku, zaloguj się jako `bystander` swoim hasłem. Autologowanie i sudo bez hasła dotyczą wyłącznie sesji live.

## 12. Test po instalacji

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

Powtórz test dźwięku/mikrofonu i ręczne testy pulpitu. `lspci`, `lsusb` i `xdpyinfo` są dodatkowymi narzędziami ISO; nie muszą być zainstalowane na dysku. `ravnux-guide` pozostaje dostępne także po instalacji.

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
