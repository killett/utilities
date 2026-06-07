from __future__ import annotations

import sys
import argparse
import logging
from pathlib import Path

import emmykit as ek

__version__: str = "0.1.1"


class Options:
    """Class that has all global options in one place."""

    def __init__(self) -> None:
        """Initialize the Options class with default values."""
        self.my_name:             str = Path(sys.argv[0]).stem
        self.log_mode:            int = logging.INFO     # Use -debug to switch to DEBUG.
        self.args: argparse.Namespace = argparse.Namespace()

        # Concrete, user-tunable defaults:
        self.timeout_per_step:  float =   2.5  # seconds per individual check
        self.min_timeout:       float =   0.5  # minimum seconds per check
        self.retries:             int =   1    # overall retries for the combined check
        self.min_retries:         int =   0    # minimum retries
        self.workers:             int =   6    # thread pool size for parallel attempts
        self.min_workers:         int =   1    # minimum threads
        self.include_ipv6:       bool = False  # attempt IPv6 endpoints too
        self.strict:             bool = False  # require HTTP probe OR (TCP+DNS), not just raw TCP
        self.ignore_proxies:     bool = False  # force direct HTTP (no env proxies)
        self.exit_code:          bool =  True  # set exit code 0/1 based on result


def parse_arguments(options: Options) -> None:
    """
    Parse command-line arguments.

    Args:
        options: Options object to store parsed arguments. Contains:
            - my_name           : Name of the program.
            - log_mode          : Logging mode (default is logging.INFO).
            - args              : Parsed arguments will be stored here.
            - timeout_per_step  : float; seconds timeout per individual check.
            - retries           : int; number of full-check retries.
            - workers           : int; thread pool size for parallel attempts.
            - include_ipv6      : bool; whether to include IPv6 connectivity checks.
            - strict            : bool; require stronger evidence of connectivity.
            - ignore_proxies    : bool; disable env proxies for HTTP probes.
            - exit_code         : bool; control non-zero exit when offline.

    Returns:
        None, but updates options.args with parsed arguments.

    Raises:
        SystemExit: If the '-v'/'--version' flag is provided (prints and exits).
        ValueError: If argument values are invalid.
    """
    parser = argparse.ArgumentParser(
        description=f"Check internet availability using multiple strategies. {options.my_name} v{__version__}"
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-debug", "--debug", action="store_true",
                        help="Enable debug logging.")
    parser.add_argument("-t", "--timeout", type=float, default=options.timeout_per_step,
                        help=f"Timeout (seconds) per individual check (default: {options.timeout_per_step}).")
    parser.add_argument("-r", "--retries", type=int, default=options.retries,
                        help=f"Number of full-check retries on failure (default: {options.retries}).")
    parser.add_argument("-w", "--workers", type=int, default=options.workers,
                        help=f"Thread pool size (default: {options.workers}).")
    parser.add_argument("--ipv6",    dest="ipv6", action="store_true",  default=options.include_ipv6,
                        help=f"Enable IPv6 checks (default: {options.include_ipv6}).")
    parser.add_argument("--strict", action="store_true",
                        help="Require stronger evidence: a successful HTTP probe OR (TCP + DNS).")
    parser.add_argument("--ignore-proxies", action="store_true",
                        help="Ignore HTTP(S) proxy environment variables during HTTP probes.")
    parser.add_argument("--no-exit-code", action="store_true",
                        help="Do not use exit status (always exit 0). Result still printed.")

    options.args = parser.parse_args()
    if options.args.debug:
        options.log_mode = logging.DEBUG

    # Update options from CLI
    if float(options.args.timeout) < options.min_timeout:
        logging.warning(f"requested timeout < minimum ({options.min_timeout}); bumping to {options.min_timeout}s")
    if int(options.args.retries) < options.min_retries:
        logging.warning(f"requested retries < minimum ({options.min_retries}); bumping to {options.min_retries}")
    if int(options.args.workers) < options.min_workers:
        logging.warning(f"requested workers < minimum ({options.min_workers}); bumping to {options.min_workers}")
    options.timeout_per_step = max(options.min_timeout, float(options.args.timeout))
    options.retries          = max(options.min_retries,   int(options.args.retries))
    options.workers          = max(options.min_workers,   int(options.args.workers))
    options.include_ipv6     =     bool(options.args.ipv6)
    options.strict           =     bool(options.args.strict)
    options.ignore_proxies   =     bool(options.args.ignore_proxies)
    options.exit_code        = not bool(options.args.no_exit_code)


def main() -> None:
    """
    Main function.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    options: Options = Options()
    parse_arguments(options)

    logging.basicConfig(level=options.log_mode,
                        format="%(asctime)s - %(levelname)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

    online: bool = ek.is_internet_available(
        timeout_per_step=options.timeout_per_step,
        retries=options.retries,
        workers=options.workers,
        include_ipv6=options.include_ipv6,
        strict=options.strict,
        ignore_proxies=options.ignore_proxies,
    )

    if online:
        logging.info("Internet is available.")
    else:
        logging.warning("Internet is NOT available!")

    logging.shutdown()

    # Optionally make the exit code reflect connectivity.
    if options.exit_code:
        sys.exit(0 if online else 1)


# Example of simulating a DNS blackhole to test timeout handling:
# import time, socket
# _orig_getaddrinfo = socket.getaddrinfo
# def _blackhole_getaddrinfo(*args, **kwargs):
#     # Simulate a slow resolver that takes forever, then fails.
#     time.sleep(100)  # <-- simulate the stall (tweak as desired)
#     raise socket.gaierror(socket.EAI_NONAME, "simulated DNS blackhole")
# socket.getaddrinfo = _blackhole_getaddrinfo
# t0 = time.perf_counter()
# try:
#     print("Trying to connect with DNS blackhole...")
#     print("result:", ek.is_internet_available(timeout_per_step=2.5, retries=0))
# finally:
#     # restore immediately so your REPL isn't cursed
#     socket.getaddrinfo = _orig_getaddrinfo
#     print("elapsed:", time.perf_counter() - t0, "s")

if __name__ == "__main__":
    main()
