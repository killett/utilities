import logging

import emmykit as ek


def main() -> None:
    """Main function to run the country detection."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    country = ek.detect_country(force_wtfismyip=False)
    logging.info(f"Detected country: {country}")


if __name__ == "__main__":
    main()
