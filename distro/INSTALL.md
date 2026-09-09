# Installing the WBS Toolkit — agent runbook

**You are the installer.** The person reading your messages is the *owner*. Assume they are
not technical: they do not know what a shell, a PATH, a package manager, or a runtime is,
and they should not have to learn. Your job is to get them from "nothing" to "a working WBS
project" without ever making them understand the machinery.

This document is for you, not for them. Never paste it at them. Never show them this file's
headings, step numbers, or jargon. Translate everything into plain language.

---

## What you are installing, and who runs it

The WBS Toolkit is different from a typical app install: there is no server and nothing to
open in a browser. It is a small Python command (`wbs.sh`) that **you — the coding agent —
run yourself**, inside a project, while you plan and build it. The owner never types a
`wbs.sh` command themselves; they talk to you, and you drive the tool.

That means the "installation" the owner needs to see through has two separate parts:

1. **The runtime this document covers:** git, Python 3.10+, and ideally `uv`. That's the
   whole dependency list — no API keys, no accounts, no sign-in.
2. **You, running as their coding agent, need to already be set up** (Claude Code or Codex,
   installed and signed in) — because you are the one who will use the toolkit afterward.
   If you're reading this at all, that part is already true.

---

## Rules of engagement

**1. One instruction at a time.** Give one copy/paste block, wait for them to report back,
then move on. Never hand over a wall of five commands.

**2. Every command goes in a copy/paste box** with a plain-language sentence before it
saying what it does, and a plain-language sentence after saying what they should see.

Say it like this:

> This installs the piece the work planner runs on. Copy the line below, paste it into the
> black window, and press Enter. It will take about a minute and print a lot of text —
> that's normal. Tell me when it stops and gives you a fresh line to type on.

**3. Never show them a raw error.** If a command fails, read the error yourself, fix it, and
tell them in one sentence what you're doing: "That needed one more piece — installing it
now, one more paste and we're past it."

**4. Fix, do not defer.** Do not tell the owner "you may need to install X." Detect it, and
either fix it in the same breath or hand them the one command that fixes it. Never finish
with a caveat list. Never leave a known-broken install and call it done.

**5. If you cannot fix it yourself, ask precisely.** Some things need the owner's password
or an administrator prompt, and you cannot type those. When you hit one, hand them the exact
command, tell them a password prompt will appear, and warn them that **the password will not
show any characters as they type — that is normal, not a broken keyboard.**

**6. Never invent a step.** Everything you need is in this document. If reality diverges
from it, say so plainly and stop rather than improvising.

---

## Step 0 — Ask which computer

This is your first question. Ask exactly this, and nothing else:

> Quick first question: are you on a Mac, or on Windows?

- **Mac** → go to **Track A**.
- **Windows** → go to **Track B**.
- If they don't know: ask if the machine has an Apple logo on it. Apple logo → Mac.

Do not ask about versions, chips, terminals, or anything else yet. You will detect all of
that yourself.

---

# Track A — macOS

## A1. Open the terminal

> I need you to open a program called Terminal. Press `Command` and the `Space bar` at the
> same time, type the word `terminal`, and press Enter. A window with plain text in it will
> open. That's where everything goes.

If they say a black-and-white text window is open, continue.

## A2. Check what's already there

```sh
echo "macOS: $(sw_vers -productVersion)"; \
echo "git: $(git --version 2>/dev/null || echo MISSING)"; \
echo "python3: $(python3 --version 2>/dev/null || echo MISSING)"; \
echo "uv: $(uv --version 2>/dev/null || echo MISSING)"
```

> This just looks around and tells me what's already on your machine. It changes nothing.
> Paste the whole thing, press Enter, then copy everything it prints back to me.

Read the report yourself. Then handle only what's missing:

| Line says | What to do |
|---|---|
| `git: MISSING` | A3 |
| `python3: MISSING` or a version below `3.10` | A4 |
| `uv: MISSING` | A5 (optional but recommended — see why below) |
| everything present | skip to A6 |

**macOS ships a `python3`, but it can be old or a stub that prints a App Store prompt
instead of running.** Read the version line carefully: `Python 3.9.6` is too old,
`Python 3.13.2` is fine.

## A3. Install git (only if missing)

git ships with Apple's developer command line tools.

```sh
xcode-select --install
```

> This asks macOS to install Apple's developer tools, which include a piece the toolkit
> needs. A grey system window will pop up asking you to confirm — click **Install**, then
> **Agree**. It downloads in the background and can take five to ten minutes. Tell me when
> the pop-up says it's done.

When they report done, verify:

```sh
git --version
```

Expect something like `git version 2.39.5`. If the pop-up said the tools are *already
installed* but `git --version` still fails, that is the one macOS case worth escalating —
tell them their developer tools are damaged and the fix is `sudo rm -rf
/Library/Developer/CommandLineTools` followed by re-running `xcode-select --install`, and
that it will ask for their Mac password.

## A4. Install Python (only if missing or too old)

The cleanest fix is installing `uv` first — it can fetch and manage a modern Python for you,
with nothing separate to download. Skip straight to **A5**; it covers this case too.

If for some reason `uv` cannot be installed either, fall back to Apple's own installer
package: send them to **https://www.python.org/downloads/macos/**, have them download and
run the latest 3.x installer, then re-run the check in A2.

## A5. Install uv (recommended)

`uv` is what makes this painless: it runs the toolkit without the owner ever managing a
Python installation by hand, and it can install a modern Python on the fly if needed.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> This installs a small helper the planner uses to run itself cleanly. It prints a few
> lines and takes a few seconds.

Then have them **close the Terminal window and open a fresh one** (the old window cannot see
newly installed programs), and verify:

```sh
uv --version
```

Expect something like `uv 0.5.x`. If it still says missing in a *fresh* window, note it and
move on — `uv` is a nice-to-have. The toolkit falls back to plain `python3` automatically.

## A6. Install the WBS Toolkit

Ask where the project should live. Default to a folder named `my-project` in their home
directory, and do not make them choose a path if they have no opinion. If they're adding the
toolkit to a project that already exists, use that folder's path instead.

```sh
cd ~ && curl -fsSL https://raw.githubusercontent.com/coachlou/ambient-library/main/library/ambient-folder/bootstrap.sh | bash -s -- wbs-toolkit my-project
```

> This is the real one — it sets up the work planner inside a folder called `my-project` in
> your home directory. It'll print a list of files as it goes. Send me everything it prints.

Read the output. It ends with a `WBS:` line naming the launcher. Treat any line beginning
with `warn` as a failure to fix, not a note to pass along — see **Fixing a bad install**.

Go to **C1**.

---

# Track B — Windows

The toolkit's launcher and installer are Linux/Mac shell scripts, so on Windows it runs
inside WSL2 — a real Ubuntu Linux that Microsoft ships as a standard Windows feature.

**WSL2 is a requirement on Windows, not a fallback.** There is no native-Windows path; do
not try to build one. B1 walks through installing it if it is absent, and converting it if
the machine has the older WSL1.

**Never explain WSL2 to the owner.** To them it is "a Linux window that Windows comes with,"
and after setup it is just "the Ubuntu window." Nothing more.

## B1. Set up the Linux window (WSL2)

### B1a. Check what they already have

> Windows needs one component switched on. Microsoft includes it — we may just need to turn
> it on, or you may already have it.
>
> 1. Click the Start button and type `powershell`.
> 2. **Right-click** on *Windows PowerShell* in the results and choose **Run as
>    administrator**. A window will ask "do you want to allow this app to make changes" —
>    click **Yes**.
> 3. A blue window opens. Paste this in and press Enter, then send me everything it prints:

```powershell
wsl --status; wsl --list --verbose
```

> This only looks around and reports back. It changes nothing.

Read the output yourself and pick exactly one row:

| What you see | Meaning | Go to |
|---|---|---|
| `'wsl' is not recognized...` | WSL is not installed at all | **B1b** |
| An error mentioning *no installed distributions*, or an empty list | WSL is on, no Linux installed | **B1c** |
| A list with a distro at `VERSION  2` | Already correct | **B1e** |
| A list with a distro at `VERSION  1` | WSL1 — must be converted | **B1d** |
| Any mention of *WSL 1* as the default version | Default is wrong | **B1d** |

If the list shows several distros, prefer an Ubuntu one at VERSION 2. Tell the owner which
name you picked and use that name consistently from here on.

### B1b. Install WSL2 from scratch

```powershell
wsl --install
```

> That downloads and switches on the Linux component. When it finishes it will tell you to
> restart your computer. **Restart it.** Tell me once you're back and logged in.

**If it says `wsl` is not a recognized command even now**, their Windows is too old for the
one-line installer. Check the version:

```powershell
winver
```

WSL2 needs Windows 11, or Windows 10 version 2004 / build 19041 or higher. If they are
below that, the honest answer is that their Windows needs updating first — send them to
Settings → Windows Update, and stop until that is done. Do not attempt the legacy manual
WSL install with a non-technical owner; it is a six-step registry-and-reboot dance and it
is not worth it.

After the restart, go to **B1e**.

### B1c. Install Ubuntu (WSL is on, but there is no Linux)

```powershell
wsl --set-default-version 2
```

```powershell
wsl --install -d Ubuntu
```

> This installs Ubuntu itself. It downloads for a few minutes.

Go to **B1e**.

### B1d. Convert an existing WSL1 install to WSL2

Set the default first so anything installed later is correct:

```powershell
wsl --set-default-version 2
```

Then convert their existing distro, replacing `Ubuntu` with the exact name from the list in
B1a if it differs:

```powershell
wsl --set-version Ubuntu 2
```

> This upgrades your existing Linux to the newer version. **It can take ten or twenty
> minutes and will look stuck partway through — leave it alone and let it finish.** Tell me
> when it says the conversion is complete.

Then confirm it actually took:

```powershell
wsl --list --verbose
```

The distro must now show `VERSION  2`. If it still shows `1`, the conversion failed — the
usual cause is the virtualization problem below.

Go to **B1e**.

### B1e. Open Ubuntu and create the Linux account

> Click Start, type `ubuntu`, and open it.
>
> The first time it runs it sets itself up for a couple of minutes, then asks you to create a
> username and password. Use anything you'll remember — this is separate from your Windows
> login. **When you type the password, nothing at all will appear on screen. That's normal —
> it's still working. Type it and press Enter.** It'll ask you to type it a second time to
> confirm.
>
> Tell me when you see a line ending in a `$` sign.

If it opens straight to a `$` with no setup, the account already exists and that is fine.

**From here on, every command goes in the Ubuntu window, not PowerShell.** State this
plainly once, and if a later command behaves strangely, first confirm which window they
pasted into — mixing them up is the single most common Windows failure.

### B1f. When WSL will not install at all

**If any of the above fails with a virtualization error**, the machine has hardware
virtualization disabled in its BIOS. You cannot fix that from software. Tell the owner
plainly that their computer has a setting switched off that only they can change, that it
requires going into the machine's start-up settings, and that it varies by manufacturer —
they should search their PC model plus "enable virtualization in BIOS," or ask whoever
supports their computer. Do not attempt to walk them through a BIOS blind.

Two other real causes worth recognising before you blame the BIOS: a virtual machine that
does not pass virtualization through to the guest, and a corporate laptop where an
administrator has blocked WSL by policy. In both cases the owner cannot fix it alone — say
so and stop rather than looping.

## B2. Check and install the Ubuntu essentials

Unlike macOS, a fresh Ubuntu has almost none of this. Check first:

```sh
echo "git: $(git --version 2>/dev/null || echo MISSING)"; \
echo "curl: $(command -v curl 2>/dev/null || echo MISSING)"; \
echo "python3: $(python3 --version 2>/dev/null || echo MISSING)"; \
echo "uv: $(uv --version 2>/dev/null || echo MISSING)"
```

> This just looks around and reports back. It changes nothing.

Then install whatever is missing:

```sh
sudo apt update && sudo apt install -y git curl python3
```

> This installs the missing pieces. It will ask for the password you just created for Ubuntu
> — **the password stays invisible as you type it.** Then it prints a few screens of text
> for a minute or two.

## B3. Install uv (recommended)

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> This installs a small helper the planner uses to run itself cleanly. It prints a few lines
> and takes a few seconds.

Then have them close the Ubuntu window and open a fresh one, and verify:

```sh
uv --version
```

If it still says missing in a *fresh* window, note it and move on — the toolkit falls back
to plain `python3`.

## B4. Install the WBS Toolkit

**It must live inside the Ubuntu home folder, never in `/mnt/c/`.** Windows drives mounted
into Linux have different file permissions and are dramatically slower, and git behaves
incorrectly on them. `cd ~` handles this; do not let the owner talk you into a Windows path
like `C:\Users\...`.

```sh
cd ~ && curl -fsSL https://raw.githubusercontent.com/coachlou/ambient-library/main/library/ambient-folder/bootstrap.sh | bash -s -- wbs-toolkit my-project
```

> This is the real one — it sets up the work planner. Send me everything it prints.

Go to **C1**.

---

# Part C — Both platforms

## C1. Verify the install

```sh
cd ~/my-project && ls .aai .ailib/wbs-toolkit
```

Expect to see `.aai` and `.ailib/wbs-toolkit` listed without errors.

```sh
cd ~/my-project && bash wbs.sh --help
```

Expect a usage message listing commands like `init`, `next`, `start`, `done`. That message
is success, not an error.

## C2. Tell them what they have, and stop

Do not launch into how to plan or build a project. Installation is finished. Say something
close to:

> You're done — the work planner is installed in your project.
>
> From here, the way it works is: you tell me what you want built, I interview you to pin
> down the requirements, and I turn that into a plan of small, ordered pieces. Then I build
> each piece — writing the tests first, then the code — and check in with you at the points
> that matter.
>
> Whenever we come back to this, just tell me you want to keep going with the plan; I'll
> pick up right where we left off.
>
> Want me to start the interview now?

If they say yes, that is a separate conversation — start the requirements interview
yourself (the `wbs-prd` workflow) rather than reading any more of this document.

---

# Updating an existing install

Updating is the same command as installing. It refreshes the machinery and leaves all their
work and plan untouched.

```sh
cd ~/my-project && curl -fsSL https://raw.githubusercontent.com/coachlou/ambient-library/main/library/ambient-folder/bootstrap.sh | bash -s -- wbs-toolkit .
```

> This updates the work planner to the latest version. Your plan and progress are left
> exactly as they are.

What updates and what does not:

- **Refreshed:** `.ailib/` — the vendored toolkit. `wbs.sh` is rewritten too.
- **Never touched:** `.aai/` (settings) and `.wbs/` (the plan and its live status).

---

# Fixing a bad install

Work these yourself. Do not read this table out loud.

| Symptom | Cause | Fix |
|---|---|---|
| `warn  uv not found on PATH — install uv or ensure python3 has PyYAML` | `uv` missing and system `python3` lacks PyYAML | A5 / B3; or `python3 -m pip install pyyaml` if they truly cannot get `uv` |
| `no .aai/ above ... — install wbs-toolkit into a project first` | Running `wbs.sh` from the wrong folder | `cd` into the installed project first |
| `WBS runtime missing: expected .../app/wbs.py or vendored fallback` | Interrupted install | Re-run the installer for their platform |
| Windows: odd filesystem, permission or exec failures with no other explanation | Running on WSL1, not WSL2 | `wsl --list --verbose` in PowerShell; if VERSION is 1, convert per B1d |
| Windows: `'wsl' is not recognized` after `wsl --install` | Windows build too old for WSL2 | `winver`; needs Win11 or Win10 build 19041+. Windows Update first, then stop |
| Windows: nothing behaves as documented | Commands went into PowerShell instead of Ubuntu | Confirm which window; everything after B1 belongs in Ubuntu |
| `python3: command not found` on Windows/Ubuntu | Not yet installed | B2 |
| `curl: command not found` | Ubuntu missing curl | B2 |
| `git: command not found` | git missing | A3 / B2 |
| `install: refused — these paths already exist with different contents` | A previous half-install left conflicting files | Do **not** delete anything. Show the owner the listed paths and ask whether they installed here before. Only proceed once they confirm the folder is disposable. |
| `command not found` right after installing something | Shell has a stale PATH | Fresh terminal window, then retry. This resolves it the overwhelming majority of the time. |

**Two things you must never do to get past an error:** never delete a folder the owner did
not confirm is disposable, and never weaken or delete a `verify` command in `.wbs/tree.yaml`
to get `wbs.sh done` to pass — that gate is the point of the tool.

---

# Done means all of this

Do not tell the owner they are finished until every one of these is true. Verify them
yourself; do not ask the owner to confirm them.

1. `git --version` prints a version.
2. `python3 --version` prints 3.10 or higher (or `uv --version` prints a version, which
   covers this on its own).
3. `~/my-project/wbs.sh` exists.
4. `cd ~/my-project && bash wbs.sh --help` prints the usage message.
5. On Windows only: `wsl --list --verbose` shows the distro at `VERSION  2`, not 1.

If any one of these fails, you are not done. Fix it.
