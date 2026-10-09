# RAVNUX — postęp prac

Aktualizacja: 2026-10-09.

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
| 3 | Ozdobne logo R ze złotymi wzorami | Porównanie odzyskanej grafiki z GitHubem, kontrola integracji, zapis | Gotowe |
| 4 | Budowanie i CI | Przegląd nbd, testu VM, konsoli szeregowej i workflow, zapis | Gotowe; CI zaliczone |
| 5 | Budowa ISO | Udany build konkretnego commita, zapis przebiegu i artefaktu | Gotowe; ISO na wydaniu v2026.10.08-r14 |
| 6a | Rozruch BIOS | Test VM i zapis wyniku | Gotowe; PASS w run 34 |
| 6b | Rozruch UEFI | Test VM i zapis wyniku | Gotowe; PASS w run 34 |
| 6c | Instalacja | Instalacja na pustym dysku VM i start z dysku | Gotowe dla BIOS (run 44); instalacja UEFI nieprzetestowana |
| 7 | Instrukcja i wydanie | Przewodnik zgodny z przetestowanym ISO, suma kontrolna i publikacja | Oczekuje |

## Następny krok: etap 7 — instrukcja i wydanie

Etap 6c zakończony dla BIOS: instalacja na pustym dysku VM, start z dysku
i weryfikacja zalogowanego użytkownika przechodzą w CI (wydanie
`v2026.10.09-r44` oznaczone latest, VM boot tests passed, Install test
passed). Opcjonalnie: wariant instalacji UEFI. Następnie etap 7:
przewodnik zgodny z przetestowanym ISO, suma kontrolna, publikacja.

## Odzyskane zmiany i ich stan

- Budowanie, CI, test VM i konfiguracja konsoli: sprawdzone i zapisane w etapie 4.
- Dokumentacja: `README.md`, `docs/GUIDE_PL.md`, `docs/artwork-prompts.md`.
- Logo: `overlay/common/usr/share/pixmaps/ravnux-logo.png` — właściwa ozdobna wersja zapisana i potwierdzona na GitHubie w etapie 3.

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

- Etap 3: ukończony. Użytkownik wgrał gotowy PNG w commicie
  `0834a411bdb65137f535fd2caf8de032f0204a93`. GitHub potwierdza blob
  `6a071f0b5c209bb43ef061cedd0f2ff4cdf7dee5`, identyczny z odzyskanym logo.
  Grafika: różowe R na purpurowym tle ze złotymi ornamentami, 1254x1254 RGB.
  SHA256: `41ad8a1dd956756ac076d1e5af0430e4508f89f118408553a98d415b2be24bd0`.
  PNG sprawdzony przez Pillow; referencje LightDM i ikony przewodnika zgodne.
  Kontrola źródeł i przygotowanego profilu `python3 scripts/check.py` zaliczona.
  `build.sh --prepare-only` potwierdził identyczne kopie logo w live i osadzonym
  root-overlay; rzeczywista komenda cp instalatora zachowała identyczny PNG.
  Test przygotowania używał wcześniejszego profilu jako szablonu releng,
  a nie świeżego upstream Archiso. Nie budowano ISO ani nie testowano GUI.
  Skrypty build/install i ukończone etapy 1–2 pozostały bez zmian.
  Grafikę przesłano jako plik, bez Base64 w czacie lub argumentach narzędzi.

- Etap 4: wykonany lokalnie na bazie `e603c00907b6b5b92de8ca9cd298c27ad6d0f5ad`.
  Dodano nbd do pakietów live; upstream hook archiso_pxe_nbd wymaga nbd-client.
  Przygotowanie profilu nie wymaga roota, odrzuca stare katalogi i dowiązania
  work/profile/out, sprawdza szablony i SOURCE_DATE_EPOCH przed zapisem.
  Nie używa stałego katalogu tymczasowego; zachowuje wyłącznie konfigurację
  initramfs i szablony startowe upstream, a nie użytkowników/usługi ratunkowe.
  Dodano konsolę szeregową do SYSLINUX, systemd-boot i szablonów GRUB;
  serial-getty czeka na utworzenie użytkownika live.
  Test VM ma limity czasu, KVM/TCG, buforowanie konsoli, jawne odrzucanie
  xorg-server/xf86-input-libinput, logi błędów i raport dopiero po sukcesie.
  Polecenia do VM są przesyłane jako tekst, bez Base64.
  Workflow oddziela walidację od ręcznej budowy ISO i opcjonalnych testów VM.
  Zachowuje logi również po błędzie; shell Bash z pipefail zachowuje wynik
  budowania przy tee. Nie publikuje wydania; uprawnienia contents pozostają read.
  README opisuje aktualny sposób budowania i testowania.
  Testy: 31/31 zaliczonych bez pominięć; kontrola źródeł i profilu zaliczona;
  składnia Python, YAML workflow i poleceń Bash zaliczona.
  Przygotowanie profilu sprawdzono na pobranych szablonach tekstowych upstream
  Archiso `723da192226e1c9d5def9168f13332793c82a85e`.
  Lokalnie użyto pobranych szablonów tekstowych. Następnie GitHub Actions
  potwierdził przygotowanie profilu na pełnym zainstalowanym pakiecie Archiso.
  Nie budowano ISO ani nie uruchomiono prawdziwych VM.
  Testy jednostkowe przygotowania używają kontrolowanego szablonu releng;
  testy logiki gościa VM symulują programy systemowe.
  Użytkownik zatwierdził zapis zmian do main 2026-10-04.
  Commit kodu: `6c1cb87152f16593a90cc74e1aa8ed2284b6f48a`.
  GitHub Actions: https://github.com/stainleSSStar/RAVNUX/actions/runs/37196053888 .
  Job validate zakończony sukcesem, wszystkie jego kroki zaliczone.
  Job iso pominięty zgodnie z ręcznym trybem budowania; etap 4 nie buduje ISO.
  Etap 5 nie został rozpoczęty.

- Etap 5 (w toku): pierwszą budowę ISO wykonano 2026-10-08 ręcznym
  uruchomieniem workflow (run 37809364706) na commicie `ffd453d`
  z opcjami `build_iso=true` i `vm_tests=true`. Walidacja zaliczona (35 s).
  ISO zbudowane pomyślnie: `ravnux-2026.10.04-x86_64.iso`, 1,6 GB
  (SOURCE_DATE_EPOCH z daty commita). Wysyłka artefaktu Actions odrzucona:
  limit miejsca artefaktów na darmowym planie (500 MB) nie mieści obrazu.
  Test VM BIOS nie wystartował: QEMU zakończył się natychmiast
  (`bios: QEMU failed to start`); diagnostyka wymaga `out/vm-bios-qemu.log`,
  który nie został dostarczony z powodu braku artefaktu.
  Zmiany po tej budowie: workflow publikuje ISO jako wydanie w publicznym
  repozytorium `stainleSSStar/RAVNUX-releases` (sekret `RELEASE_TOKEN`),
  krok testów VM jest nieblokujący, logi budowy/VM są dołączane do wydania,
  wydanie bez zaliczonych testów VM jest oznaczane jako prerelease,
  a limit czasu VM podniesiono do 1800 s na wypadek powolnego TCG.
  README zaktualizowany o sposób pobrania ISO z repozytorium wydań.

  Druga budowa (run 37811625311, commit `e05222c`): ISO ponownie zbudowane;
  testy VM znów nie wystartowały (QEMU kończy się natychmiast w trybie BIOS,
  ten sam błąd co w pierwszej budowie). Publikacja wydania nie doszła do skutku:
  `gh release create` przerwał wysyłkę na pliku `vm-bios-serial.log` o rozmiarze
  0 B (API GitHub odrzuca puste pliki: `HTTP 400: Bad Content-Length`)
  i usunął wydanie. Artefakt Actions ponownie odrzucony limitem przydziału.
  Poprawki po drugiej budowie: wydanie tworzone jest najpierw bez plików,
  a zasoby dołączane pojedynczo z pominięciem pustych plików; błąd pojedyncznego
  zasobów nie usuwa wydania. `vm-smoke.py` wypisuje teraz wyjście QEMU
  w komunikacie błędu startu, dzięki czemu diagnostyka trafia do logu zadania.

  Trzecia budowa (run 37813175724, commit `559891b`): ISO zbudowane i opublikowane
  jako wydanie `v2026.10.08-r14` w repozytorium wydań: ISO 1 713 733 632 B,
  `SHA256SUMS`, listy pakietów i logi. Artefakt Actions nadal odrzucony limitem.
  Diagnostyka VM ustaliła przyczynę natychmiastowego kończenia QEMU:
  składnia `kvm:tcg` jest nieprawidłowa dla flagi `-accel` (dotyczy wyłącznie
  `-machine accel=`); host CI ma dostępny `/dev/kvm`, więc wybierana była
  zawsze błędna wartość. Poprawka: `-machine accel=kvm:tcg` z automatycznym
  odwrotom do TCG, gdy KVM niedostępne. Etap 5 (budowa ISO) uznany za ukończony;
  etapy 6a/6b oczekują na powtórny test VM.

  Czwarta budowa (run 37815082719, commit `155b176`): ISO zbudowane i opublikowane
  jako `v2026.10.08-r15`. Po poprawce akceleratora QEMU startuje i konsola
  szeregowa działa: menu ISOLINUX, załadowanie jądra i initramfs oraz pierwszy
  komunikat jądra są widoczne. Jądro gościa zatrzymuje się jednak po ok. 0,2 s
  (ostatnia linia: `virt/tdx: TDX not supported by the host platform`) i nie
  drukuje nic do upływu limitu czasu. Objaw wskazuje na zawieszanie gościa
  w zagnieżdżonym KVM hosta CI, a nie na błąd obrazu: łańcuch rozruchu ISO
  działa do momentu startu jądra. Poprawka: opcja `--no-kvm` w `vm-smoke.py`
  wymusza TCG (deterministyczna emulacja) i jest używana w workflow CI;
  lokalnie KVM pozostaje domyślne. Pętla oczekiwania na sesję XFCE wydłużona
  do 300 s ze względu na wolniejsze TCG. Artefakt Actions w tej budowie
  przeszedł (limit zwolnił się po przeliczeniu przydziału).

  Piąta budowa (run 37820665422, commit `feb3a1c`): ISO zbudowane i opublikowane
  jako `v2026.10.08-r18`; test VM w TCG kończy się tym samym objawem co w KVM:
  jądro drukuje `virt/tdx: TDX not supported by the host platform` i konsola
  milczy do upływu limitu. Analiza: komunikat TDX jest zwykłą informacją nowszych
  jąder Arch, wpisy rozruchowe zawierają `quiet`, a `console=tty0` jest ostatnie,
  więc komunikaty przestrzeni użytkownika trafiają tylko na ekran. Prawdziwa
  przyczyna braku `login:` na ttyS0: `serial-getty@ttyS0` nie był włączony —
  build.sh włącza jawnie tylko wybrane jednostki, a generator getty systemd
  nie uruchamia getty szeregowego, gdy ostatnią konsolą jest tty0. KVM hosta CI
  najprawdopodobniej działał poprawnie; poprzednie „zawieszenia” były normalnym
  rozruchem z zamkniętą konsolą szeregową. Poprawki: build.sh włącza
  `serial-getty@ttyS0` jawnie (konto live `ravnux` ma puste hasło, więc login
  szeregowy działa), workflow CI wraca do KVM z odwrotem do TCG; opcja `--no-kvm`
  pozostaje dostępna lokalnie.

  Szósta budowa (run 37825845995, commit `94bf12e`): ISO zbudowane i opublikowane
  jako `v2026.10.08-r19`; KVM działa (bez ostrzeżeń QEMU), ale `login:` na ttyS0
  nadal się nie pojawia w 30 minut. Ustalone dwie przyczyny: (1) dowiązanie
  włączające getty wskazywało na nieistniejący plik instancji
  `serial-getty@ttyS0.service` zamiast szablonu `serial-getty@.service`
  (kanoniczna forma `systemctl enable`); (2) konsola szeregowa była przed ostatnią,
  więc komunikaty initramfs/systemd trafiały wyłącznie na tty0 i serial nie
  pokazywał postępu rozruchu. Poprawki: dowiązanie wskazuje szablon, a kolejność
  konsol zmieniona na `console=tty0 console=ttyS0,115200` — /dev/console
  to ttyS0, dzięki czemu test VM widzi pełny rozruch i login; asercja w
  `scripts/check.py` zaktualizowana do nowej kolejności.

- Siódma budowa (build 25, commit `5bed865`): ISO zbudowane, ale test VM BIOS
  nadal bez `login:`. Log szeregowy ujawnił przyczynę: `systemd-firstboot`
  ("Initial Setup") blokował konsolę pytaniem o strefę czasową. mkarchiso
  zapisuje `/etc/machine-id` jako `uninitialized`, więc każdy rozruch live
  spełnia `ConditionFirstBoot=yes`; upstream releng unika promptów, bo
  predefiniuje wszystkie ustawienia (/etc/localtime, locale.conf itd.).
  Poprawka (commit `a61ed10`): maska `systemd-firstboot.service` (dowiązanie
  do /dev/null) w overlay live oraz `/etc/localtime` → Europe/Warsaw
  (domyślna strefa instalatora) w overlay common; `scripts/check.py`
  asercje maski i dowiązania, test budowania kopiuje repozytorium
  z zachowaniem dowiązań symbolicznych (wcześniej `copytree` je rozwijał,
  co zamieniłoby maskę w zwykły pusty plik). Przed poprawką anulowano zbędny
  dispatch run 37948529642. Walidacja CI dla `a61ed10`: zaliczona.

- Ósma budowa (build 28, commit `a61ed10`): postęp — `login:` pojawia się,
  login szeregowy działa, `exec sudo bash` osiąga prompt roota; ale sonda
  gotowości wysłana natychmiast po `exec` zniknęła: sudo czyści kolejkę
  wejścia TTY przy tworzeniu sesji celu. Poprawka (commit `0dd392a`):
  vm-smoke czeka na prompt roota (`# `) przed wysłaniem sondy.

- Dziewiąta budowa (build 30, commit `0dd392a`): skrypt gościa uruchamia się,
  sesja XFCE/XLibre wstaje, ale fałszywy alarm "Unexpected package: xorg-server".
  Przyczyna: `pacman -Q` rozwiązuje również provides (query.c spada do
  `alpm_find_satisfier`), a `xlibre-xserver` provides `xorg-server`.
  Poprawka (commit `22e37cf`): porównanie z listą nazw z `pacman -Qq`;
  mock testu podaje listę zainstalowanych dla `-Qq`.

- Dziesiąta budowa (build 32, commit `22e37cf`): wszystkie kontrole gościa
  przechodzą (pakiety, usługi, zasoby, xdpyinfo), ale końcowy `printf
  RAVNUX_VM_OK` w kolejce wejścia za `sudo -u ravnux ... xdpyinfo` został
  wyczyszczony przez ten sam mechanizm sudo. Poprawka (commit `a31849c`):
  znacznik końcowy w tej samej linii co sudo (bash odczytuje całą linię
  przed wykonaniem); porażka xdpyinfo trafia do pułapki ERR przez `false`
  (łańcuch `&&` nie uruchamia set -e).

- Jedenasta budowa (build 34, commit `a31849c`): BIOS i UEFI PASS.
  VM-TESTS.txt: rozruch ISO, sesja XFCE, Xlibre, NetworkManager/LightDM/
  Bluetooth, logo, tapeta, instalator. Wydanie `v2026.10.09-r34`
  opublikowane jako latest (nie prerelease), z pełnymi logami BIOS/UEFI.
  Etapy 6a/6b uznane za ukończone.
  Ograniczenia: testy walidacyjne uruchamiane lokalnie na hoście ARM macOS
  pomijają testy wymagające roota/x86_64 (8 niepowodzeń środowiskowych);
  pełny pakiet 31 testów przechodzi na CI validate dla każdego commita.
  Nie przetestowano: instalacji na dysku (6c), sprzętu fizycznego.

- Etap 6c (BIOS): dodano `scripts/vm-install.py` — test instalacji w VM w CI:
  ISO startuje z pustym dyskiem 16 GB (MS-DOS + ext4, zgodnie z kontraktem
  instalatora), instalacja jest prowadzona przez konsolę szeregową
  (potwierdzenie INSTALL, hasło użytkownika), po czym system startuje
  z dysku i weryfikuje: hostname, NetworkManager, LightDM, logo i przewodnik
  na zalogowanym systemie. Na zainstalowanym systemie test włącza konsolę
  szeregową (argumenty kernela + serial-getty@ttyS0) wyłącznie na potrzeby
  weryfikacji bez monitora. Workflow: opcja `install_test`; krok zwalnia
  katalog roboczy archiso dla miejsca na dysku; wydanie jest oznaczane
  latest tylko, gdy test instalacji też przechodzi. Testy: 37/37 na CI
  validate (x86_64, root) dla każdego commita; lokalnie na ARM macOS
  8 testów środowiskowych pomija kontrolę root/x86_64.

  Budowy i naprawione wady (każda wykryta przez test CI, realna dla
  użytkowników):
  - build 36: instalator przerywał po pacstrap z „Unexpected Xorg server
    in target" — `pacman -Q xorg-server` rozwiązuje provides (xlibre-xserver
    provides xorg-server). Poprawka: porównanie nazw z `pacman -Qq`
    (commit `5725773`), asercja w check.py.
  - build 38: `umount /mnt` z „target is busy" — procesy gnupg docelowego
    keyringu trzymają pliki pod celem. Poprawka: `gpgconf --kill all`
    dla docelowego keyringa przed końcem instalatora (commit `0b0047f`);
    test ma awaryjną diagnostykę i leniwe odmontowanie.
  - build 40: weryfikacja końcowa padała na `hostname: command not found` —
    Arch wydzielił pakiet hostname, base go nie ciągnie. Poprawka: asercja
    zawartości `/etc/hostname` (commit `96b7862`).
  - build 42: sprawdzanie `/usr/local/bin/ravnux-install` na zainstalowanym
    systemie — to binarium istnieje tylko w overlay live. Poprawka:
    weryfikacja zasobów root-overlay (logo, przewodnik) (commit `47a2780`).

  Budowa 44 (run 37973584831, commit `47a2780`): instalacja BIOS na pusty
  dysk PASS; start z dysku PASS; VM-TESTS i VM-INSTALL-TESTS w załącznikach
  wydania `v2026.10.09-r44` (latest). Etap 6c uznany za ukończony dla BIOS.
  Ograniczenia: instalacja UEFI (przenośny fallback --removable --no-nvram),
  szyfrowanie, dual boot i sprzęt fizyczny pozostają nieprzetestowane;
  kreator systemd-firstboot na pierwszym rozruchu zainstalowanego systemu
  nie pojawił się (ustawienia hostname/locale/localtime są zdefiniowane),
  ale /etc/vconsole.conf nie istnieje — warto obserwować przy testach
  sprzętowych.
