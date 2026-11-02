# Install Saral — v0.3.0

Saral is a simple automation language. Files end in `.srl`, the command
is `saral`, and the interpreter needs only Python 3 (standard library
only). See README.md for the language, SPEC.md for the full spec, and
PROOF.md for test evidence.

## Status: NOT published yet — read this first

**As of this preparation, Saral has NOT been published anywhere.**
Nothing below that says "after push" works today. The one-command
download lines in the "After push" section will only work once the
new GitHub repo `Die-Another-Day/Saral` is created and pushed, and
that push is verified back from GitHub. Do not report Saral as
downloadable, installed by default, or live until that happens.

What is NOT available yet, even after that push:
- No PyPI package (`pip install saral` does not exist)
- No apt / Homebrew package
- No Windows installer / `.msi` / single binary
- No QEMU boot proof of Saral inside SecureOS (see SecureOS note below)

## Install today (LOCAL mode — works now)

From a Saral checkout (this folder), no sudo required:

```bash
./install.sh --local .
saral version
```

That installs to your home directory by default:
- binary: `~/.local/bin/saral` (launcher)
- code: `~/.local/lib/saral/saral.py`
- libraries: `~/.local/lib/saral/libs/`

If `~/.local/bin` is not on your PATH, the installer prints the exact
`export PATH=...` line to add, or you can run it directly as
`~/.local/bin/saral script.srl`.

System-wide install (needs root or sudo):

```bash
./install.sh --local . --system
```

That installs to `/usr/local/bin/saral` and
`/usr/local/lib/saral/` instead.

Any prefix:

```bash
./install.sh --local . --prefix /opt/my-prefix
```

## Install after push (GITHUB mode — NOT live yet)

Once `Die-Another-Day/Saral` is pushed to `main` and verified, this
will be the one-command install, exactly like downloading Python:

```bash
curl -fsSL https://raw.githubusercontent.com/Die-Another-Day/Saral/main/install.sh | sh -s -- --github
```

Or, equivalently, clone and install locally:

```bash
git clone https://github.com/Die-Another-Day/Saral.git
cd Saral
./install.sh --local .
```

The `--github` mode downloads only these files from the repo's
`main` branch: `saral.py`, `libs/*.py`, and
`libs/greet_bridge/greet.js` + `lib.json`. It does not download or
run anything else, and it collects no credentials.

Until the push happens, the `--github` command will fail with a 404.
That failure means "repo not published yet" — it is expected, and it
is not a bug in Saral.

## Windows

There is no Windows installer yet. On Windows with Python 3
installed, Saral already works from a checkout, without any installer:

```cmd
python saral.py examples\hello.srl
```

A future `.msi`/installer (like python.org's) is not built yet and
must not be claimed to exist.

## macOS / Linux without the installer

From a checkout, no install needed:

```bash
python3 saral.py examples/hello.srl
./saral examples/hello.srl
```

## Verify the install

```bash
saral version          # must print: Saral 0.3.0
saral list             # libraries actually installed, with verbs
saral check examples/hello.srl
```

## Uninstall

Remove the two paths for the prefix you used. Default user-local:

```bash
rm -rf ~/.local/bin/saral ~/.local/lib/saral
```

System install:

```bash
sudo rm -rf /usr/local/bin/saral /usr/local/lib/saral
```

## SecureOS default (not live yet)

Saral is prepared to be installed by default in SecureOS v4 (see the
SecureOS repo's `saral/` folder and the `setup-v4.sh` /
`build-image.sh` changes, prepared locally, not pushed). Until those
changes are pushed AND a new SecureOS image is built and booted,
Saral is NOT installed by default in the live OS, and the QEMU boot
proof of Saral-in-SecureOS remains unproven. The install simulation
in the preparation notes is not a boot proof.
