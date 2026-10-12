# RAVNUX

Minimalistyczny system **x86_64 oparty na Arch Linux**, z XFCE na XLibre, Fish i własnym purpurowo-różowym motywem. Repozytorium zawiera konfigurację obrazu live, instalator systemu i proces budowania ISO. Projekt jest wstępny: pomyślna kompilacja nie oznacza przetestowania sprzętu ani instalacji.

**Instrukcja krok po kroku po uruchomieniu ISO: [GUIDE_PL.md](docs/GUIDE_PL.md)**. W sesji live jest też dostępna offline przez `ravnux-guide` oraz menu aplikacji. Instrukcja i instalatory nie trafiają na dysk.

## Co zawiera system

- Linux, oficjalne firmware Arch, mikrokod Intel/AMD, firmware SOF dla układów audio.
- XFCE na X11 z serwerem XLibre (gałąź stable): jeden panel, menedżer plików, ustawienia, terminal, powiadomienia i zarządzanie energią. Wbudowany kompozytor XFWM jest włączony: cienie okien, subtelna przezroczystość panelu i terminala.
- Fish jako powłoka użytkownika; Bash pozostaje zależnością systemu i służy do wykonywania skryptów.
- PipeWire + WirePlumber, obsługa ALSA i aplikacji PulseAudio, kontrola głośności i mikrofonu.
- NetworkManager, Wi-Fi, Bluetooth, montowanie nośników USB oraz uwierzytelnianie administracyjne.
- Mesa/OpenGL: otwarte sterowniki grafiki Intel/AMD oraz Nouveau dla obsługiwanych kart NVIDIA. Bez własnościowego sterownika NVIDIA, dodatkowych sterowników Vulkan i pakietów AUR.
- LightDM, własny motyw GTK/Xfwm, ciemne purpurowe tło i różowo-purpurowy terminal/Fish. Domyślna tapeta to cyberpunkowe miasto z purpurowymi neonami; logo to różowa litera R na purpurowym tle. Oba pliki są dostarczane na ISO oraz w systemie docelowym, bez pobierania przy logowaniu.

Bez preinstalowanej przeglądarki, pakietu biurowego, gier, sklepu z aplikacjami, helpera AUR, serwera SSH i środowiska programistycznego. Pakiety `packages/system.txt` stanowią zestaw docelowy; pacman instaluje także ich wymagane zależności. GRUB, przy UEFI efibootmgr, oraz ewentualnie btrfs-progs są dodawane przez instalator jako narzędzia rozruchu/filesystemu.

To Arch rolling release korzystający z repozytoriów **core/extra** i dodatkowego **xlibre-stable**, bez testing i beta. Brak mechanizmu automatycznego aktualizowania systemu. Budowanie w różnych dniach może pobrać różne wersje pakietów; nie jest to zamrożony ani bitowo powtarzalny obraz.

## Pobranie ISO z GitHub

Otwórz **Actions → Build RAVNUX ISO → Run workflow** i zaznacz `build_iso`. Push i pull request uruchamiają walidację źródeł oraz przygotowanie profilu; pełna budowa ISO wymaga ręcznego uruchomienia. Opcja `vm_tests` dodatkowo uruchamia testy rozruchu BIOS i UEFI, a opcja `install_test` — interaktywną instalację na pustym dysku oraz start z dysku w BIOS i UEFI; wydanie oznaczone jako wstępne (prerelease) oznacza, że któryś z tych testów nie przeszedł lub nie został uruchomiony.

Po udanej budowie ISO wraz z sumą `SHA256SUMS`, listami pakietów i logami budowy/VM jest publikowane jako wydanie w publicznym repozytorium wydań: **https://github.com/stainleSSStar/RAVNUX-releases/releases**. Publikacja używa sekretu `RELEASE_TOKEN` i działa również wtedy, gdy testy VM nie przeszły — wtedy dołączone logi wskazują przyczynę. Artefakty Actions w prywatnym repozytorium źródłowym pozostają ograniczone limitem darmowego planu (500 MB), dlatego ISO (ok. 1,6 GB) nie może być artefaktem i jest dostarczane wyłącznie przez repozytorium wydań.

ISO obsługuje UEFI x86_64 oraz BIOS. Secure Boot nie jest skonfigurowany. Obraz jest dla zwykłych komputerów x86_64, nie dla Apple Silicon.

## Budowanie samodzielne

Na Arch Linux, jako administrator, z aktualnym spójnym zestawem pakietów i działającymi mirrorami:

```sh
sudo pacman -S --needed archiso python git
git clone https://github.com/stainleSSStar/RAVNUX.git
cd RAVNUX
sudo bash scripts/build.sh
```

Wynik: `out/ravnux-*.iso`. `bash scripts/build.sh --prepare-only` składa i sprawdza sam profil bez pobierania pakietów ani tworzenia ISO; nie wymaga roota. Przed kolejnym budowaniem przenieś lub usuń wygenerowane `work/`, `profile/` i `out/`. Skrypt nie usuwa ich automatycznie, aby chronić wcześniejsze wyniki. Potrzebny jest internet, kilkanaście GB wolnego miejsca i możliwość używania mount/loop. Mac nie jest natywnym hostem tego procesu; workflow używa oficjalnego kontenera Arch na Linuxie.

Skrypt kopiuje szablony rozruchowe z zainstalowanego `archiso`, zachowuje jego initramfs, ale usuwa zestaw ratunkowy upstreamu. Następnie dodaje wyłącznie pakiety RAVNUX, konfigurację wspólną i dodatki live. `out/live-packages.txt` podaje faktyczne wersje pakietów obrazu, a `build-host-packages.txt` wersje narzędzi kompilacji.

## Sesja live

Po starcie automatycznie loguje się użytkownik `ravnux` z Fish i XFCE. Wyłącznie w sesji live ma sudo bez hasła. Root jest zablokowany. Terminal otworzysz z menu aplikacji. Sieć skonfigurujesz przez ikonę NetworkManager lub `nmtui`; Wi-Fi możesz skonfigurować przez `nmcli`. Dźwięk przez ikonę głośności lub `pavucontrol`.

## Instalacja na dysk

Uruchom ISO w UEFI (zalecane) lub BIOS, podłącz internet przez NetworkManager / `nmtui` i otwórz terminal:

```sh
sudo ravnux-install
```

Bez argumentów uruchamia interaktywny kreator `ravnux-setup`. Pyta o cały dysk docelowy, nazwę komputera, konto i strefę czasową. Przed pierwszym zapisem pokazuje dysk i wymaga dokładnego potwierdzenia `ERASE /dev/...`. **Kreator usuwa wszystkie dane i partycje na wybranym dysku. Nie obsługuje dual boot ani szyfrowania/LVM/RAID.** Blokuje dyski zamontowane, swap, urządzenia tylko do odczytu i aktywne mapowania; nie odmontowuje ich automatycznie. Wymaga co najmniej 32 GiB i internetu.

Tryb uruchomienia ISO decyduje o instalacji bootloadera:

| Tryb | Układ GPT | Bootloader |
| --- | --- | --- |
| UEFI x86_64 | EFI 1 GiB FAT32 + reszta ext4 | GRUB, `EFI/BOOT/BOOTX64.EFI`, bez zmiany NVRAM |
| BIOS | BIOS boot 2 MiB bez filesystemu + reszta ext4 | GRUB na całym wybranym dysku |

Po formatowaniu kreator uruchamia właściwy instalator, który ponownie pokazuje partycję root i wymaga `INSTALL`. Następnie pobiera pakiety i pyta o hasło konta. Po sukcesie odmontowuje partycje i pyta o restart. Nie restartuje automatycznie. Po błędzie zatrzymuje pracę i pozostawia stan do diagnostyki; zapisanych danych nie cofa.

### Tryb dla wcześniej przygotowanych partycji

Wywołanie z argumentami zachowuje dotychczasowy tryb: nie partycjonuje ani nie formatuje. Root musi być pustą zwykłą partycją ext4/btrfs (dopuszczalne `lost+found` i `boot`), a UEFI wymaga osobnej pustej EFI FAT32. Przykład po samodzielnym przygotowaniu partycji — dopasuj nazwy urządzeń:

```sh
sudo mount /dev/nvme0n1p2 /mnt
sudo mkdir -p /mnt/boot/efi
sudo mount /dev/nvme0n1p1 /mnt/boot/efi
sudo ravnux-install --hostname ravpc --username bystander --timezone Europe/Warsaw
sudo umount -R /mnt
sudo reboot
```

Dla BIOS zamontuj tylko root i dodaj `--bios-disk /dev/sda` z nazwą całego dysku zawierającego root; na GPT przygotuj także partycję BIOS boot. Uruchomienie ISO w BIOS nie tworzy instalacji UEFI ani odwrotnie.

Po restarcie usuń nośnik live. Zainstalowany system wymaga hasła do logowania i sudo. Pozostają wyłącznie podstawa systemu, firmware i otwarte sterowniki grafiki, sieć, Bluetooth, dźwięk, XFCE, Fish i motyw; bez przeglądarki, edytora, narzędzi instalacji i `ravnux-guide`. Wymagane zależności pacmana nadal są instalowane. Guide, narzędzia testowe i edytor są wyłącznie na ISO. Osobna partycja `/home` i swap nie są tworzone; swap/hibernację możesz skonfigurować później. Domyślny interfejs jest angielski, locale polskie jest wygenerowane, a strefa domyślna to Europe/Warsaw.

## Weryfikacja i testy sprzętowe

```sh
python3 scripts/check.py
sudo python3 -m unittest discover -s tests -v
```

Serwer `xorg-server` i sterownik `xf86-input-libinput` zostały zastąpione przez `xlibre-xserver` i `xlibre-input-libinput`. Klucz podpisujący XLibre jest dołączony i sprawdzany według pełnego fingerprintu `0C92313001CFCA27627B9098B97F7C613F359424`. Podpisy pakietów pozostają wymagane. Klienci i biblioteki X11 mogą zachować nazwy `xorg-*`/`libX*`; nie są serwerem Xorg.

Kontrole źródeł weryfikują składnię Bash, XML, format konfiguracji, zestaw pakietów i oddzielenie sesji live od systemu docelowego. Proces budowania dodatkowo sprawdza dostępność wszystkich żądanych pakietów w bazie pacmana i buduje ISO. Nie zastępuje to testu bootowania ani instalacji.

Po zbudowaniu ISO można sprawdzić sesję live w QEMU na Linuxie z pakietami `qemu-system-x86` i `ovmf`:

```sh
python3 scripts/vm-smoke.py out/*.iso
```

Domyślnie testowane są BIOS i UEFI; `--mode bios` lub `--mode uefi` wybiera jeden tryb. Na hostach, gdzie KVM zawiesza gościa (spotykane na runnerach CI), użyj `--no-kvm`, aby wymusić TCG. Skrypt zapisuje logi konsoli/QEMU oraz raport `out/VM-TESTS.txt` dopiero po sukcesie wszystkich wybranych testów. Weryfikuje XFCE/XLibre, usługi, grafiki i instalator w sesji live. Nie przeprowadza instalacji na dysku.

Do testu instalacji na Linuxie z pakietem `qemu-system-x86` (wymaga roota w QEMU przez KVM; test działa też w CI):

```sh
python3 scripts/vm-install.py out/*.iso
```

Skrypt testuje domyślnie BIOS i UEFI (`--mode bios` / `--mode uefi` wybiera jeden tryb). Dla każdego trybu uruchamia ISO z pustym dyskiem 36 GiB i przechodzi interaktywny kreator: wybór dysku, dane konta, potwierdzenia `ERASE` i `INSTALL`, hasło i odmowa restartu. Następnie uruchamia system z dysku, loguje się i sprawdza usługi oraz brak guide i instalatorów. Wymaga `qemu-system-x86` i `ovmf`. Konsola szeregowa (kernel i `serial-getty@ttyS0`) jest włączana w systemie docelowym wyłącznie przez test. Logi trafiają do `out/vm-install-*.log`, a raport `out/VM-INSTALL-TESTS.txt` jest zapisywany tylko po sukcesie wszystkich wybranych trybów. Nie testuje szyfrowania, dual boot ani rzeczywistego sprzętu.

Przed uznaniem obrazu za gotowy sprawdź:

1. Start UEFI i BIOS w maszynie wirtualnej; później na rzeczywistym sprzęcie.
2. XFCE, panel, terminal, Fish, motyw, skalowanie i wiele monitorów.
3. Ethernet, Wi-Fi, Bluetooth, USB i montowanie nośników.
4. Dźwięk głośników/słuchawek/HDMI, mikrofon (`wpctl status`, `pavucontrol`).
5. Uśpienie, wybudzenie, jasność, touchpad i klawisze multimedialne.
6. Instalację na pusty dysk, restart, logowanie i `sudo` z hasłem.
7. Brak autologowania, użytkownika live i narzędzi instalacyjnych w systemie docelowym.

Firmware i sterowniki otwarte pokrywają wiele urządzeń, ale nie wszystkie. Konkretne modele NVIDIA, Broadcom i inne nietypowe urządzenia mogą potrzebować osobnych sterowników. Ich dobór pozostaje do testów na docelowym sprzęcie.

## Struktura

- `packages/system.txt` — pakiety systemu docelowego.
- `packages/live.txt` — dodatkowe narzędzia obecne tylko na ISO.
- `overlay/common/` — motyw i ustawienia obu środowisk.
- `overlay/live/` — konto live, autologowanie i inicjalizacja kluczy pacmana.
- `docs/GUIDE_PL.md` — gotowe polecenia i oczekiwane wyniki testów/instalacji.
- `scripts/build.sh` — składanie profilu i kompilacja ISO przez Archiso.
- `scripts/install.sh` — instalacja na zamontowany root; bez argumentów otwiera kreator.
- `scripts/install-wizard.sh` — interaktywne przygotowanie całego dysku UEFI/BIOS.
- `scripts/vm-smoke.py` — test sesji live w VM BIOS/UEFI.
- `scripts/vm-install.py` — test instalacji na pustym dysku VM i startu z dysku.
- `.github/workflows/iso.yml` — walidacja CI, ręczna budowa ISO, opcjonalne testy VM/instalacji i publikacja wydania w repozytorium wydań.

Kod i oryginalne grafiki motywu: MIT. Pakiety Arch i szablony Archiso zachowują własne licencje. Projekt nie jest oficjalnym wydaniem Arch Linux.

## Grafiki RAVNUX

- `overlay/common/usr/share/pixmaps/ravnux-logo.png` — różowa litera R na purpurowym tle; ikona menu aplikacji i domyślna ikona użytkownika na ekranie logowania.
- `overlay/common/usr/share/backgrounds/ravnux/cyberpunk-city.jpg` — domyślna tapeta pulpitu i ekranu logowania, generowana panorama miasta.

Tapeta jest ustawiana przy pierwszym uruchomieniu pulpitu użytkownika. Późniejszy wybór własnej tapety pozostaje zachowany. Grafiki zostały wygenerowane przy użyciu wbudowanego generatora obrazów. Prompty: `docs/artwork-prompts.md`.
