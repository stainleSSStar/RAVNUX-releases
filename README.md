# RAVNUX

Minimalistyczny system **x86_64 oparty na Arch Linux**, z XFCE na XLibre, Fish i własnym purpurowo-różowym motywem. Repozytorium zawiera konfigurację obrazu live, instalator systemu i proces budowania ISO. Projekt jest wstępny: pomyślna kompilacja nie oznacza przetestowania sprzętu ani instalacji.

**Instrukcja krok po kroku po uruchomieniu ISO: [GUIDE_PL.md](docs/GUIDE_PL.md)**. Jest też dostępna offline przez `ravnux-guide` oraz menu aplikacji.

## Co zawiera system

- Linux, oficjalne firmware Arch, mikrokod Intel/AMD, firmware SOF dla układów audio.
- XFCE na X11 z serwerem XLibre (gałąź stable): jeden panel, menedżer plików, ustawienia, terminal, powiadomienia i zarządzanie energią. Kompozytor domyślnie wyłączony.
- Fish jako powłoka użytkownika; Bash pozostaje zależnością systemu i służy do wykonywania skryptów.
- PipeWire + WirePlumber, obsługa ALSA i aplikacji PulseAudio, kontrola głośności i mikrofonu.
- NetworkManager, Wi-Fi, Bluetooth, montowanie nośników USB oraz uwierzytelnianie administracyjne.
- Mesa: otwarte sterowniki grafiki Intel/AMD oraz Nouveau dla obsługiwanych kart NVIDIA. Bez własnościowego sterownika NVIDIA i pakietów AUR.
- LightDM, własny motyw GTK/Xfwm, ciemne purpurowe tło i różowo-purpurowy terminal/Fish. Domyślna tapeta to cyberpunkowe miasto z purpurowymi neonami; logo to różowa litera R na purpurowym tle. Oba pliki są dostarczane na ISO oraz w systemie docelowym, bez pobierania przy logowaniu.

Bez preinstalowanej przeglądarki, pakietu biurowego, gier, sklepu z aplikacjami, helpera AUR, serwera SSH i środowiska programistycznego. Pakiety `packages/system.txt` stanowią zestaw docelowy; pacman instaluje także ich wymagane zależności. GRUB/efibootmgr oraz ewentualnie btrfs-progs są dodawane przez instalator jako narzędzia rozruchu/filesystemu.

To Arch rolling release korzystający z repozytoriów **core/extra** i dodatkowego **xlibre-stable**, bez testing i beta. Brak mechanizmu automatycznego aktualizowania systemu. Budowanie w różnych dniach może pobrać różne wersje pakietów; nie jest to zamrożony ani bitowo powtarzalny obraz.

## Pobranie ISO z GitHub

Otwórz **Actions → Build RAVNUX ISO → Run workflow** i zaznacz `build_iso`. Push i pull request uruchamiają walidację źródeł oraz przygotowanie profilu; pełna budowa ISO wymaga ręcznego uruchomienia. Opcja `vm_tests` dodatkowo uruchamia testy rozruchu BIOS i UEFI; wydanie oznaczone jako wstępne (prerelease) oznacza, że testy VM nie przeszły lub nie zostały uruchomione.

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

Instalator wymaga internetu i **wcześniej przygotowanych, pustych partycji**. Sam nie partycjonuje i nie formatuje dysku. Obsługuje zwykły root ext4 albo btrfs, bez LUKS/LVM, RAID i automatycznego dual boot. Użyj osobnej, dedykowanej partycji EFI: instalator zapisuje standardowy loader UEFI `EFI/BOOT/BOOTX64.EFI`, bez modyfikowania NVRAM.

Zalecany prosty układ GPT/UEFI:

| Partycja | Rozmiar | Typ/system plików | Montowanie w instalatorze |
| --- | --- | --- | --- |
| EFI | 1 GiB | EFI System Partition / FAT32 | `/mnt/boot/efi` |
| Root | Reszta dysku; proponowane co najmniej 30 GiB | Linux filesystem / ext4 | `/mnt` |

Osobna partycja `/home` i swap nie są wymagane. Obecny instalator oczekuje pustego root, więc najprościej pozostawić `/home` jako katalog na root. Można później skonfigurować plik swap; hibernacja wymaga dodatkowej konfiguracji. Zamiast ext4 obsługiwany jest też btrfs. Przy BIOS/GPT potrzebna jest dodatkowa partycja BIOS boot o wielkości 1–2 MiB, bez systemu plików i bez montowania, zamiast EFI.

Przykład po przygotowaniu partycji (nazwy urządzeń dopasuj do sprzętu):

```sh
sudo mount /dev/nvme0n1p2 /mnt
sudo mkdir -p /mnt/boot/efi
sudo mount /dev/nvme0n1p1 /mnt/boot/efi
sudo ravnux-install --hostname ravpc --username bystander --timezone Europe/Warsaw
```

Root musi być pusty; `lost+found` i katalog `boot` są dozwolone. EFI musi być zamontowane jako FAT32. Skrypt pokazuje urządzenie docelowe i wymaga wpisania `INSTALL`. Następnie instaluje pakiety, konfiguruje system, pyta o hasło użytkownika i instaluje GRUB. Po instalacji:

```sh
sudo umount -R /mnt
sudo reboot
```

Usuń nośnik live. Logowanie do systemu zainstalowanego wymaga hasła; sudo również. Nie są kopiowane uprawnienia ani autologowanie sesji live. Domyślny język interfejsu to angielski, locale polskie jest także wygenerowane; strefa czasowa domyślnie Europe/Warsaw.

Dla BIOS zamontuj root, ewentualnie osobne `/boot`, i dodaj `--bios-disk /dev/sda` z nazwą całego dysku zawierającego root. Na GPT potrzebna jest wcześniej przygotowana partycja BIOS boot. Przy przerwaniu instalacji skrypt kończy pracę z błędem i nie cofa zapisanych plików; napraw konfigurację ręcznie lub przygotuj ponownie pusty root przed ponowieniem.

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
- `scripts/install.sh` — instalacja na zamontowany root.
- `scripts/vm-smoke.py` — test sesji live w VM BIOS/UEFI.
- `.github/workflows/iso.yml` — walidacja CI, ręczna budowa ISO, opcjonalne testy VM i publikacja wydania w repozytorium wydań.

Kod i oryginalne grafiki motywu: MIT. Pakiety Arch i szablony Archiso zachowują własne licencje. Projekt nie jest oficjalnym wydaniem Arch Linux.

## Grafiki RAVNUX

- `overlay/common/usr/share/pixmaps/ravnux-logo.png` — różowa litera R na purpurowym tle; ikona menu aplikacji i domyślna ikona użytkownika na ekranie logowania.
- `overlay/common/usr/share/backgrounds/ravnux/cyberpunk-city.jpg` — domyślna tapeta pulpitu i ekranu logowania, generowana panorama miasta.

Tapeta jest ustawiana przy pierwszym uruchomieniu pulpitu użytkownika. Późniejszy wybór własnej tapety pozostaje zachowany. Grafiki zostały wygenerowane przy użyciu wbudowanego generatora obrazów. Prompty: `docs/artwork-prompts.md`.
