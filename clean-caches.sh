#!/usr/bin/env bash
#
# clean-caches.sh — Recursively delete tool cache directories.
#
# Removes every directory named in `delete_these` from a target directory
# (default: the current directory) and all subdirectories beneath it. Prefers
# `fd` for speed and transparently falls back to `find` when `fd` is absent.
#
# Usage:
#   ./clean-caches.sh [DIRECTORY]            Delete caches under DIRECTORY (or cwd).
#   ./clean-caches.sh --dry-run [DIRECTORY]  Show what would be deleted; delete nothing.
#   ./clean-caches.sh --install              Symlink onto PATH; offer to fix PATH if needed.
#   ./clean-caches.sh --install --add-to-path  ...fix PATH without asking (non-interactive).
#   ./clean-caches.sh --install --system     ...into /usr/local/bin (uses sudo).
#   ./clean-caches.sh --help                 Show usage.
#
# Output convention: matching paths go to stdout; status messages and prompts go
# to stderr, so `./clean-caches.sh --dry-run 2>/dev/null` prints a clean list.

set -euo pipefail

# --- Configuration ---------------------------------------------------------
# Directory names to remove. Matched as exact basenames, at any depth.
delete_these=(
    .mypy_cache
    .pytest_cache
    .pixi
    .ruff_cache
)

prog=${0##*/}

# Filled in by compute_path_fix.
PATH_FIX_KIND=""   # file | fish | unknown
PATH_FIX_FILE=""   # shell startup file when kind=file

# --- Small error helpers ---------------------------------------------------
# Usage/syntax error: message + usage on stderr, exit 2.
err() { printf '%s: %s\n\n' "$prog" "$1" >&2; usage >&2; exit 2; }
# Runtime error: message on stderr, exit with given code (default 1).
die() { printf '%s: %s\n' "$prog" "$1" >&2; exit "${2:-1}"; }

usage() {
    cat <<EOF
Usage: $prog [OPTION]... [DIRECTORY]

Recursively delete these directories, starting from DIRECTORY
(default: the current directory):
  ${delete_these[*]}

Options:
  -n, --dry-run     List what would be deleted, then exit without deleting.
                    With --install, show what the install would do.
      --install     Symlink this script (as '${prog%.*}') into the best writable
                    directory on your PATH. If that directory is not already on
                    PATH, you will be asked whether to add it (interactive
                    shells only; declined automatically when non-interactive).
      --add-to-path With --install: add the directory to PATH without asking.
                    Use this for non-interactive runs (scripts, CI).
      --system      With --install: install into /usr/local/bin instead, which
                    is on the default PATH. Uses sudo unless run as root.
  -h, --help        Show this help and exit.

Uses 'fd' when available (faster), otherwise falls back to 'find'.
EOF
}

# --- fd detection ----------------------------------------------------------
# Echo the name of a usable fd binary, or nothing. On Debian/Ubuntu the program
# is installed as 'fdfind'. We confirm via --version because on some systems an
# unrelated tool (fdclone) is also called 'fd'.
detect_fd() {
    local candidate
    for candidate in fd fdfind; do
        if command -v "$candidate" >/dev/null 2>&1 \
           && "$candidate" --version 2>/dev/null | grep -Eq '^fd(find)? [0-9]'; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

# --- Install helpers -------------------------------------------------------
# Is $1 a directory currently on $PATH? (normalises trailing slashes)
dir_on_path() {
    local target="${1%/}" entry found=1 IFS=:
    set -f
    for entry in $PATH; do
        [[ -z "$entry" ]] && entry=.        # empty PATH element == cwd
        if [[ "${entry%/}" == "$target" ]]; then found=0; break; fi
    done
    set +f
    return "$found"
}

# Can we write into $1, creating it (and any missing parents) if needed?
dir_usable() {
    local d="$1" p
    if [[ -d "$d" ]]; then
        [[ -w "$d" ]]
    elif [[ -e "$d" ]]; then
        return 1                            # exists but is not a directory
    else
        p="$d"                              # walk up to deepest existing ancestor
        while [[ ! -e "$p" ]]; do
            local parent; parent=$(dirname -- "$p")
            [[ "$parent" == "$p" ]] && break
            p="$parent"
        done
        [[ -d "$p" && -w "$p" ]]
    fi
}

# Inspect $SHELL and set PATH_FIX_KIND / PATH_FIX_FILE.
compute_path_fix() {
    local shell_base
    shell_base=$(basename -- "${SHELL:-}" 2>/dev/null || true)
    case "$shell_base" in
        zsh)
            PATH_FIX_KIND="file"; PATH_FIX_FILE="$HOME/.zshrc" ;;
        bash)
            PATH_FIX_KIND="file"
            if [[ "$(uname -s 2>/dev/null || true)" == Darwin ]]; then
                PATH_FIX_FILE="$HOME/.bash_profile"   # macOS Terminal = login shell
            else
                PATH_FIX_FILE="$HOME/.bashrc"
            fi ;;
        fish)
            PATH_FIX_KIND="fish"; PATH_FIX_FILE="" ;;
        *)
            PATH_FIX_KIND="unknown"; PATH_FIX_FILE="" ;;
    esac
}

# Advise how to add $1 to PATH by hand (declined / non-interactive / unknown).
warn_path() {
    printf '%s is not on your PATH. Add it (then restart your shell), e.g.:\n' "$1" >&2
    # The $PATH below is printed literally; it is advice for the user to paste.
    # shellcheck disable=SC2016
    printf '  echo '\''export PATH="%s:$PATH"'\'' >> ~/.zshrc   # zsh; ~/.bashrc for bash\n' "$1" >&2
    printf 'or re-run with --add-to-path to do it automatically.\n' >&2
}

# Remind the user to refresh the current shell's command cache so a just-linked
# command is found by name / tab-completion without opening a new shell. Keyed
# to the shell (zsh: rehash, bash: hash -r), not the OS.
rehash_hint() {
    local shell_base
    shell_base=$(basename -- "${SHELL:-}" 2>/dev/null || true)
    case "$shell_base" in
        zsh)  printf 'Run: rehash   (or open a new terminal) so your shell finds it now.\n' >&2 ;;
        bash) printf 'Run: hash -r  (or open a new terminal) so your shell finds it now.\n' >&2 ;;
        *)    printf 'Open a new terminal so your shell finds it now.\n' >&2 ;;
    esac
}

# Append a PATH entry for $1 to PATH_FIX_FILE (idempotent).
write_path_entry() {
    local dir="$1" rcfile="$PATH_FIX_FILE"
    if [[ -f "$rcfile" ]] && grep -qF -- "\"$dir:" "$rcfile"; then
        printf 'PATH entry for %s already present in %s\n' "$dir" "$rcfile" >&2
    else
        {
            printf '\n# Added by %s --install\n' "$prog"
            # The $PATH below must stay literal so the shell expands it at startup.
            # shellcheck disable=SC2016
            printf 'export PATH="%s:$PATH"\n' "$dir"
        } >> "$rcfile" || die "could not write to $rcfile"
        printf 'Added %s to PATH in %s\n' "$dir" "$rcfile" >&2
    fi
    printf 'Restart your shell or run:  source %s\n' "$rcfile" >&2
}

# Dry-run description of the PATH step for $1.
path_fix_dry() {
    local dir="$1"
    compute_path_fix
    case "$PATH_FIX_KIND" in
        file)
            if [[ "$add_to_path_flag" == true ]]; then
                printf 'Would add %s to PATH in %s\n' "$dir" "$PATH_FIX_FILE" >&2
            elif [[ -t 0 ]]; then
                printf 'Would ask whether to add %s to PATH in %s\n' "$dir" "$PATH_FIX_FILE" >&2
            else
                warn_path "$dir"
            fi ;;
        fish)
            printf 'Would suggest: fish_add_path %s\n' "$dir" >&2 ;;
        *)
            warn_path "$dir" ;;
    esac
}

# After install: if $1 is not on PATH ($2 != true), fix it (--add-to-path),
# prompt (interactive), or advise. $3 is "apply" or "dry".
handle_path() {
    local dir="$1" onp="$2" mode="$3" reply
    [[ "$onp" == true ]] && return 0
    if [[ "$mode" == dry ]]; then
        path_fix_dry "$dir"
        return 0
    fi
    compute_path_fix
    case "$PATH_FIX_KIND" in
        fish)
            printf 'To add %s to PATH in fish, run:  fish_add_path %s\n' "$dir" "$dir" >&2
            return 0 ;;
        unknown)
            warn_path "$dir"
            return 0 ;;
    esac
    # PATH_FIX_KIND == file
    if [[ "$add_to_path_flag" == true ]]; then
        write_path_entry "$dir"
    elif [[ -t 0 ]]; then                   # interactive terminal: ask
        printf 'Add %s to your PATH by editing %s? [y/N] ' "$dir" "$PATH_FIX_FILE" >&2
        read -r reply || reply=""
        case "$reply" in
            [Yy]|[Yy][Ee][Ss]) write_path_entry "$dir" ;;
            *) printf 'Left PATH unchanged. Re-run with --add-to-path to add it later.\n' >&2 ;;
        esac
    else                                    # non-interactive: never block; advise
        warn_path "$dir"
    fi
}

# Resolve this script to a real file path, even when invoked by bare name
# (PATH lookup) or through a symlink (one hop, which covers a prior install).
resolved_self() {
    local src="$0" tgt dir found
    if [[ "$src" != */* ]]; then
        found=$(command -v -- "$src" 2>/dev/null || true)
        [[ -n "$found" ]] && src="$found"
    fi
    if [[ -L "$src" ]]; then
        tgt=$(readlink "$src" 2>/dev/null || true)
        case "$tgt" in
            /*) src="$tgt" ;;
            ?*) src="$(dirname -- "$src")/$tgt" ;;
        esac
    fi
    dir=$(cd -P -- "$(dirname -- "$src")" 2>/dev/null && pwd -P) || return 1
    printf '%s/%s\n' "$dir" "$(basename -- "$src")"
}

install_self() {
    local script_path base link_name mode
    script_path=$(resolved_self) || die "cannot determine script location."
    [[ -f "$script_path" ]] || die "script file not found at: $script_path"
    base=$(basename -- "$script_path")
    link_name="${base%.*}"; [[ -n "$link_name" ]] || link_name="$base"
    mode="apply"; [[ "$dry_run" == true ]] && mode="dry"

    local chosen="" on_path=false sudo_prefix=""

    if [[ "$system_flag" == true ]]; then
        chosen="/usr/local/bin"
        on_path=true; dir_on_path "$chosen" || on_path=false
        if [[ "$(id -u)" -eq 0 ]]; then
            sudo_prefix=""
        elif command -v sudo >/dev/null 2>&1; then
            sudo_prefix="sudo"
        else
            die "--system needs sudo (not found) or running as root."
        fi
    else
        local os; os=$(uname -s 2>/dev/null || echo unknown)
        local -a candidates=()
        if [[ "$(id -u)" -eq 0 ]]; then
            candidates+=(/usr/local/bin /usr/bin)
        else
            [[ -n "${HOME:-}" ]] && candidates+=("$HOME/.local/bin" "$HOME/bin")
            case "$os" in
                Darwin) candidates+=(/opt/homebrew/bin /usr/local/bin) ;;
                *)      candidates+=(/usr/local/bin) ;;
            esac
        fi
        [[ ${#candidates[@]} -gt 0 ]] || die "no candidate install directories for this system."

        local dir
        for dir in "${candidates[@]}"; do
            if dir_on_path "$dir" && dir_usable "$dir"; then chosen="$dir"; on_path=true; break; fi
        done
        if [[ -z "$chosen" ]]; then
            for dir in "${candidates[@]}"; do
                if dir_usable "$dir"; then chosen="$dir"; on_path=false; break; fi
            done
        fi
        if [[ -z "$chosen" ]]; then
            printf '%s: no writable install directory found. Tried:\n' "$prog" >&2
            printf '  %s\n' "${candidates[@]}" >&2
            die "create one (e.g. mkdir -p ~/.local/bin), put it on PATH, or use --system."
        fi
    fi

    local link_path="$chosen/$link_name"

    # Refuse to clobber anything that is not already our own link. This runs
    # before the dry-run gate, so it passes $mode through to handle_path.
    if [[ -L "$link_path" ]]; then
        local cur; cur=$(readlink "$link_path" 2>/dev/null || true)
        if [[ "$cur" == "$script_path" ]]; then
            printf 'Already installed: %s -> %s\n' "$link_path" "$script_path" >&2
            handle_path "$chosen" "$on_path" "$mode"
            if [[ "$dry_run" != true && "$on_path" == true ]]; then rehash_hint; fi
            return 0
        fi
        die "$link_path already exists (link to $cur); remove it or install elsewhere."
    elif [[ -e "$link_path" ]]; then
        die "$link_path already exists and is not a symlink; refusing to overwrite."
    fi

    if [[ "$dry_run" == true ]]; then
        if [[ -n "$sudo_prefix" ]]; then
            printf 'Would install (with sudo): %s -> %s\n' "$link_path" "$script_path" >&2
        else
            printf 'Would install: %s -> %s\n' "$link_path" "$script_path" >&2
        fi
        handle_path "$chosen" "$on_path" dry
        return 0
    fi

    if [[ ! -d "$chosen" ]]; then
        $sudo_prefix mkdir -p -- "$chosen" || die "could not create $chosen"
    fi
    if [[ ! -x "$script_path" ]]; then
        chmod +x -- "$script_path" 2>/dev/null \
            || printf '%s: note: could not chmod +x %s; do so manually if needed.\n' "$prog" "$script_path" >&2
    fi
    $sudo_prefix ln -s -- "$script_path" "$link_path" || die "failed to create symlink $link_path"
    printf 'Installed: %s -> %s\n' "$link_path" "$script_path" >&2
    handle_path "$chosen" "$on_path" apply
    if [[ "$on_path" == true ]]; then rehash_hint; fi
}

# --- Search backend (uses globals: fd_bin, search_root) --------------------
collect_targets() {
    local name
    for name in "${delete_these[@]}"; do
        if [[ -n "$fd_bin" ]]; then
            # fd skips hidden AND .gitignored paths by default; caches are both,
            # so --hidden --no-ignore are mandatory. --glob = exact basename.
            "$fd_bin" --glob --type directory --hidden --no-ignore \
                      --print0 -- "$name" "$search_root"
        else
            # -prune keeps find from descending into a match (it is about to go).
            find "$search_root" -type d -name "$name" -prune -print0
        fi
    done
}

# --- Parse arguments -------------------------------------------------------
dry_run=false
do_install=false
add_to_path_flag=false
system_flag=false
target=""
have_target=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)   dry_run=true ;;
        --install)      do_install=true ;;
        --add-to-path)  add_to_path_flag=true ;;
        --system)       system_flag=true ;;
        -h|--help)      usage; exit 0 ;;
        --)             shift; break ;;
        -*)             err "unknown option: $1" ;;
        *)              [[ "$have_target" == true ]] && err "too many arguments (one DIRECTORY allowed)"
                        target="$1"; have_target=true ;;
    esac
    shift
done
while [[ $# -gt 0 ]]; do                    # positionals after '--'
    [[ "$have_target" == true ]] && err "too many arguments (one DIRECTORY allowed)"
    target="$1"; have_target=true; shift
done

# --- Install mode ----------------------------------------------------------
if [[ "$do_install" == true ]]; then
    [[ "$have_target" == true ]] && err "--install does not take a DIRECTORY argument"
    if install_self; then exit 0; else exit 1; fi
fi
[[ "$add_to_path_flag" == true ]] && err "--add-to-path is only valid with --install"
[[ "$system_flag" == true ]]      && err "--system is only valid with --install"

# --- Resolve target directory ----------------------------------------------
search_root="."
if [[ "$have_target" == true ]]; then
    [[ -e "$target" ]] || die "no such file or directory: $target" 2
    [[ -d "$target" ]] || die "not a directory: $target" 2
    # Canonicalise (this also resolves a symlinked directory) so that fd and
    # find search the same real location.
    search_root=$(cd -P -- "$target" 2>/dev/null && pwd -P) \
        || die "cannot access directory: $target" 2
fi

# --- Select search backend -------------------------------------------------
fd_bin=$(detect_fd || true)
if [[ -n "$fd_bin" ]]; then
    printf 'Searching with %s.\n' "$fd_bin" >&2
elif command -v find >/dev/null 2>&1; then
    printf 'fd not found; searching with find.\n' >&2
else
    die "neither fd nor find is available."
fi

# --- Collect matches into an array (NUL-safe: spaces/newlines) -------------
targets=()
while IFS= read -r -d '' path; do
    targets+=("$path")
done < <(collect_targets)

if [[ ${#targets[@]} -eq 0 ]]; then
    printf 'Nothing to delete.\n' >&2
    exit 0
fi

# --- Report, then act ------------------------------------------------------
if [[ "$dry_run" == true ]]; then
    printf 'Would delete %d path(s):\n' "${#targets[@]}" >&2
else
    printf 'Deleting %d path(s):\n' "${#targets[@]}" >&2
fi
# Path list on stdout, normalised for readability (strip leading ./ and any
# trailing /). The array keeps verbatim paths for the actual removal.
for path in "${targets[@]}"; do
    display=${path#./}; display=${display%/}
    printf '%s\n' "$display"
done
if [[ "$dry_run" != true ]]; then
    # rm -rf tolerates already-removed paths, so a nested same-name directory
    # (deleted with its parent) is handled without error.
    rm -rf -- "${targets[@]}"
fi
