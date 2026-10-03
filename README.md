# RAVNUX

Minimalistyczny system **x86_64 oparty na Arch Linux**, z XFCE, Fish i własnym purpurowo-różowym motywem. Repozytorium zawiera konfigurację obrazu live, instalator systemu i proces budowania ISO. Projekt jest wstępny: pomyślna kompilacja nie oznacza przetestowania sprzętu ani instalacji.

## Co zawiera system

- Linux, oficjalne firmware Arch, mikrokod Intel/AMD, firmware SOF dla układów audio.
- XFCE na X11: jeden panel, menedżer plików, ustawienia, terminal, powiadomienia i zarządzanie energią. Kompozytor domyślnie wyłączony.
- Fish jako powłoka użytkownika; Bash pozostaje zależnością systemu i służy do wykonywania skryptów.
- PipeWire + WirePlumber, obsługa ALSA i aplikacji PulseAudio, kontrola głośności i mikrofonu.
- NetworkManager, Wi-Fi, Bluetooth, montowanie nośników USB oraz uwierzytelnianie administracyjne.
- Mesa: otwarte sterowniki grafiki Intel/AMD oraz Nouveau dla obsługiwanych kart NVIDIA. Bez własnościowego sterownika NVIDIA i pakietów AUR.
- LightDM, własny motyw GTK/Xfwm, ciemne purpurowe tło i różowo-purpurowy terminal/Fish. Bez zewnętrznych tapet ani pobieranych motywów.

Bez preinstalowanej przeglądarki, pakietu biurowego, gier, sklepu z aplikacjami, helpera AUR, serwera SSH i środowiska programistycznego. Pakiety `packages/system.txt` stanowią zestaw docelowy; pacman instaluje także ich wymagane zależności. GRUB/efibootmgr oraz ewentualnie btrfs-progs są dodawane przez instalator jako narzędzia rozruchu/filesystemu.

To Arch rolling release korzystający wyłącznie z repozytoriów **core/extra**, bez testing. Brak mechanizmu automatycznego aktualizowania systemu. Budowanie w różnych dniach może pobrać różne wersje pakietów; nie jest to zamrożony ani bitowo powtarzalny obraz.

## Pobranie ISO z GitHub

Otwórz **Actions → Build RAVNUX ISO**. Po udanym wykonaniu pobierz artefakt `RAVNUX-x86_64-…`. Archiwum zawiera ISO, `SHA256SUMS` i listy pakietów. Obraz powstaje po zmianach kodu w `main`; można też uruchomić **Run workflow**. Artefakty są przechowywane przez 14 dni. W prywatnym repozytorium pobieranie wymaga zalogowania, a kompilacje mogą zużywać limit GitHub Actions.

ISO obsługuje UEFI x86_64 oraz BIOS. Secure Boot nie jest skonfigurowany. Obraz jest dla zwykłych komputerów x86_64, nie dla Apple Silicon.

## Budowanie samodzielne

Na Arch Linux, jako administrator, z aktualnym spójnym zestawem pakietów i działającymi mirrorami:

```sh
sudo pacman -S --needed archiso python git
git clone https://github.com/stainleSSStar/RAVNUX.git
cd RAVNUX
sudo bash scripts/build.sh
```

Wynik: `out/ravnux-*.iso`. Przed kolejnym pełnym budowaniem przenieś lub usuń wygenerowane `work/` i `profile/`. Skrypt nie usuwa ich automatycznie. Potrzebny jest internet, kilkanaście GB wolnego miejsca i możliwość używania mount/loop. Mac nie jest natywnym hostem tego procesu; workflow używa oficjalnego kontenera Arch na Linuxie.

Skrypt kopiuje szablony rozruchowe z zainstalowanego `archiso`, zachowuje jego initramfs, ale usuwa zestaw ratunkowy upstreamu. Następnie dodaje wyłącznie pakiety RAVNUX, konfigurację wspólną i dodatki live. `out/live-packages.txt` podaje faktyczne wersje pakietów obrazu, a `build-host-packages.txt` wersje narzędzi kompilacji.

## Sesja live

Po starcie automatycznie loguje się użytkownik `ravnux` z Fish i XFCE. Wyłącznie w sesji live ma sudo bez hasła. Root jest zablokowany. Terminal otworzysz z menu aplikacji. Sieć skonfigurujesz przez ikonę NetworkManager lub `nmtui`; Wi-Fi możesz skonfigurować przez `nmcli`. Dźwięk przez ikonę głośności lub `pavucontrol`.

## Instalacja na dysk

Instalator wymaga internetu i **wcześniej przygotowanych, pustych partycji**. Sam nie partycjonuje i nie formatuje dysku. Obsługuje zwykły root ext4 albo btrfs, bez LUKS/LVM, RAID i automatycznego dual boot. Użyj osobnej, dedykowanej partycji EFI: instalator zapisuje standardowy loader UEFI `EFI/BOOT/BOOTX64.EFI`, bez modyfikowania NVRAM.

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
python3 -m unittest discover -s tests -v
```

Kontrole źródeł weryfikują składnię Bash, XML, format konfiguracji, zestaw pakietów i oddzielenie sesji live od systemu docelowego. Proces budowania dodatkowo sprawdza dostępność wszystkich żądanych pakietów w bazie pacmana i buduje ISO. Nie zastępuje to testu bootowania ani instalacji.

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
- `scripts/build.sh` — składanie profilu i kompilacja ISO przez Archiso.
- `scripts/install.sh` — instalacja na zamontowany root.
- `.github/workflows/iso.yml` — automatyczne budowanie ISO.

Kod i oryginalne grafiki motywu: MIT. Pakiety Arch i szablony Archiso zachowują własne licencje. Projekt nie jest oficjalnym wydaniem Arch Linux.
