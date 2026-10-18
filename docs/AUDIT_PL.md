# Audyt RAVNUX — 2026-10-18

Zakres: skrypty budowania, instalator i kreator dysku, pakiety live/docelowe,
konfiguracja XFCE/Fish/LightDM, podpisy pakietów oraz workflow budowy i testów.
Testy nie stanowią gwarancji braku wszystkich błędów ani zgodności z każdym sprzętem.

## Poprawione problemy

- **Podwójny autostart PolicyKit:** pakiet `xfce4-session` dostarcza już
  `xfce-polkit-gnome-authentication-agent-1.desktop`. Usunięto dodatkowy wpis
  RAVNUX, który uruchamiał ten sam proces po raz drugi.
- **Kolizja nazwy konta:** nazwa istniejącego konta systemowego, np. `daemon`,
  przechodziła walidację, a `useradd` kończył instalację błędem dopiero po
  zapisaniu systemu. Oba wejścia instalatora sprawdzają teraz bazę kont;
  kreator robi to przed potwierdzeniem i formatowaniem dysku.
- **Duża lista właściwości XFCE:** `grep -q` mógł zamknąć potok przed końcem
  zapisu `printf`. Z `pipefail` dawało to fałszywy brak właściwości i mogło
  nadpisać własną tapetę/tryb obszarów roboczych. Odczyt konsumuje cały potok.
- **Nowy format ustawień terminala:** dostarczono natywny kanał Xfconf dla
  Terminala 1.2 oraz zgodny `terminalrc` dla starszych wersji. Kolory motywu
  GTK nie zastępują kolorów tekstu terminala; kursor ma jawny różowy kolor.
- **Kolor panelu:** `background-rgba` miał błędny typ string, co powodowało
  ostrzeżenie GLib i pomijanie ustawienia. Ustawiono cztery składowe double,
  zgodnie z formatem Xfconf dla koloru RGBA.
- **Niespójne kontrolki:** rozszerzono motyw o listy, pola, menu, przyciski,
  przełączniki, suwaki, stany nieaktywne, GTK4 i własne powiadomienia XFCE.
- **Magazyn Actions:** workflow próbował wysyłać całe ISO do artefaktów mimo
  opisanej dystrybucji przez Releases. Artefakty obejmują teraz tylko małe
  pliki diagnostyczne i podgląd pulpitu. Osobna opcja pozwala budować/testować
  ISO bez publikacji wydania. Publikacja jest blokowana, gdy którykolwiek
  wybrany test zakończy się błędem.

## Minimalizm bez utraty funkcji

`packages/system.txt` pozostaje listą funkcji systemu, a nie sztucznie skróconą
listą zależności. Usunięcie z niej np. `polkit`, `bluez` czy `udisks2` nie
zmniejszyłoby liczby pakietów na dysku — wróciłyby jako wymagane zależności.
Nie dodano silnika motywów, nowego kompozytora ani aplikacji do personalizacji.
Wszystkie zmiany wyglądu są plikami CSS/XML/konfiguracji.

Usunięto `efibootmgr` z dodatków live oraz z instalacji UEFI: RAVNUX używa
`grub-install --removable --no-nvram`, więc nie zapisuje wpisów NVRAM i nie
potrzebuje tego narzędzia. To rzeczywiste ograniczenie zestawu żądanego przez
instalator; dokładną końcową liczbę i rozmiar pakietów ustala pacman podczas
budowy. Nie utożsamiamy liczby wierszy manifestu z liczbą pakietów na dysku.

Zachowane celowo:

| Zestaw | Dlaczego pozostaje |
| --- | --- |
| `linux-firmware`, oba mikrokody, SOF | Jeden obraz obsługujący różne komputery Intel/AMD i audio |
| NetworkManager, applet, wpa_supplicant | Ethernet/Wi-Fi oraz konfiguracja graficzna i tekstowa |
| BlueZ, bluez-utils, Blueman | Parowanie, obsługa Bluetooth i narzędzia CLI |
| PipeWire/ALSA/Pulse/WirePlumber | Audio, mikrofon i zgodność aplikacji |
| pavucontrol i plugin panelu | Plugin daje szybką głośność; mikser także wejścia, profile i routing aplikacji |
| GVfs i udisks2 | Montowanie nośników z Thunara bez roota |
| xfce4-screensaver | Blokada sesji; nie zastępuje go kompozytor |
| XFWM | Kompozytor, dekoracje i przezroczystość bez dodatkowego Picoma |
| Narzędzia dyskowe i rozruchowe live | Instalacja ext4/btrfs, BIOS/UEFI i zachowane opcje menu rozruchu |

## Wygląd i aktualizacja

Tekst terminala: `#a6f28a`, tło: `#2b1238`, krycie: 88%. Fish używa zieleni
w zwykłym tekście, poleceniach i argumentach, różu/purpury w akcencie promptu,
a czerwieni w błędach. Kolory ANSI programów pozostają zachowane.

Wspólna paleta systemu: tło `#24152f`, powierzchnia `#301b3e`, pola `#180e24`,
zaznaczenie `#9d3ac2`, fokus `#f472b6`, tekst `#eadcf2`.

Nowe konta otrzymują ustawienia z `/etc/skel`. Istniejące konta zachowują
swoje prywatne ustawienia; podmiana źródeł nie zmienia automatycznie
zainstalowanego systemu. Motyw wybiera się przez Ustawienia → Wygląd oraz
Menedżer okien, a kolory/przezroczystość przez preferencje terminala.

## Weryfikacja

- `scripts/check.py`: składnia i struktura źródeł, rozdzielenie live/docelowego.
- Testy jednostkowe: także kolizje kont i duże listy ustawień tapety.
- CI Linux: pełny zestaw testów, rzeczywiste układy partycji na obrazach loop,
  przygotowanie profilu na aktualnym Archiso.
- `desktop-preview`: prawdziwe XFWM, panel, Thunar, terminal, GTK3 i powiadomienia
  pod Xvfb. Narzędzia renderowania nie są pakietami dystrybucji.
- Opcjonalna pełna budowa i testy VM BIOS/UEFI sprawdzają live, instalację oraz
  start z dysku. Test live sprawdza też wybrany motyw i konfigurację terminala.

Stan uruchomień CI i podglądów należy sprawdzać dla konkretnego commitu w PR.
Nie obejmują one rzeczywistych GPU, radia Wi-Fi/Bluetooth, uśpienia ani audio.
