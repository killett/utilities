import datetime as dt
import numpy as np
import pandas as pd

import emmykit as ek

# Record exact time that this script starts running
start_time = dt.datetime.now()

###############################
# Tests of parse_timezone()
###############################

print(f"{ek.parse_timezone('UTC') = }")       # → UTC+00:00
print(f"{ek.parse_timezone('UTC+5') = }")     # → UTC+05:00
print(f"{ek.parse_timezone('GMT-2:30') = }")  # → UTC−02:30
print(f"{ek.parse_timezone('UTC+5h30m') = }") # → UTC+05:30
print(f"{ek.parse_timezone('GMT+3') = }")     # → UTC+03:00
print(f"{ek.parse_timezone('UTC-8h') = }")    # → UTC−08:00

# parse_timezone edge cases
print(f"{ek.parse_timezone('Z') = }")               # → UTC+00:00
print(f"{ek.parse_timezone('utc') = }")             # case-insensitive
print(f"{ek.parse_timezone('GMT+0000') = }")        # colonless offset
print(f"{ek.parse_timezone('GMT+00:00') = }")
print(f"{ek.parse_timezone('UTC-0530') = }")
print(f"{ek.parse_timezone('utc+5h') = }")
print(f"{ek.parse_timezone('gmt-4H15M') = }")       # mixed case, unit letters
print(f"{ek.parse_timezone('+2') = }")              # bare +H
print(f"{ek.parse_timezone('-11:45') = }")          # high negative offset
print(f"{ek.parse_timezone('EST') = }")             # abbreviation → America/New_York
print(f"{ek.parse_timezone('cSt') = }")             # ambiguous CST → America/Chicago
print(f"{ek.parse_timezone('Asia/Kolkata') = }")    # IANA
try:
    print(ek.parse_timezone('Mars/Phobos'))
except Exception as e:
    print(f"Expected error for invalid zone: {e!r}")

###############################
# Tests of parse_datetime()
###############################

print(f"{ek.parse_datetime('2021-03-31T12:00:00Z') = }")       # → 2021-03-31 12:00:00+00:00
print(f"{ek.parse_datetime('2021-03-31T12:00:00+05:30') = }")  # → 2021-03-31 12:00:00

print(f"{ek.parse_datetime('Jan 1, 2021') = }")  # → 2021-01-01 00:00:00+00:00
print(f"{ek.parse_datetime('31 Mar 2021 12:00:00') = }")

# ISO8601 parsing (aware vs naive)
print(f"{ek.parse_datetime('2021-03-31T12:00:00Z') = }")
print(f"{ek.parse_datetime('2021-03-31T12:00:00+05:30') = }")
print(f"{ek.parse_datetime('2021-03-31T12:00:00-08:00', timezone='PST') = }")
print(f"{ek.parse_datetime('20210331T143000Z') = }")     # compact
print(f"{ek.parse_datetime('2021-03-31 14:30:00') = }")  # naive → attach UTC

# Ordinals, commas, dots, slashes
print(f"{ek.parse_datetime('5th Jan, 2021') = }")
print(f"{ek.parse_datetime('23rd.Feb.2022 08:15') = }")
print(f"{ek.parse_datetime('31/12/1999 23:59:59') = }")
print(f"{ek.parse_datetime('12/31/1999 12:59 PM') = }")  # US format'
print(f"{ek.parse_datetime('2021/03/31 12:00:00') = }")  # slashes

# Month name full/abbr, fuzzy
print(f"{ek.parse_datetime('March 5th 2020 7pm') = }")
print(f"{ek.parse_datetime('Tue, 25 Jun 2025 14:00:00 GMT') = }")  # RFC-2822

# Decimal year
print(f"{ek.parse_datetime(2002.291,              timezone='UTC') = }")
print(f"{ek.parse_datetime('2002.29178082191777', timezone='UTC') = }")

# NOW
print(f"{ek.parse_datetime('NOW') = }")
print(f"{ek.parse_datetime('NOW', timezone='PST') = }")

# Unix timestamps
unix = 1_615_529_600  # 2021-03-13T12:00:00Z
print(f"{ek.parse_datetime(unix,        format_str='seconds') = }")
print(f"{ek.parse_datetime(unix * 1000, format_str='milliseconds') = }")

# units since custom epoch
print(f"{ek.parse_datetime(100,  format_str='seconds since 2020-01-01') = }")
print(f"{ek.parse_datetime(1500, format_str='milliseconds since Jan 1 2020') = }")
print(f"{ek.parse_datetime(15,   format_str='sidereal days after March 3rd, 2020') = }")
print(f"{ek.parse_datetime(3.7,  format_str='megaseconds since Jan 1 2020') = }")
print(f"{ek.parse_datetime(500,  format_str='synodic months after 06/09/1980') = }")
print(f"{ek.parse_datetime(500,  format_str='synodic months after 09/1980') = }")
print(f"{ek.parse_datetime(1000, format_str='hours since J2000') = }")

# format_str “units since epoch”
print(f"{ek.parse_datetime(365,  format_str='days since 2020-01-01') = }")
print(f"{ek.parse_datetime(2,    format_str='weeks since 2021-01-01') = }")
try:
    ek.parse_datetime(10,        format_str='lightyears since 2000-01-01')
except Exception as e:
    print(f"Expected invalid unit error: {e!r}")

# date-only vs datetime.datetime
d     = dt.date(    2021, 7, 4)
dtobj = dt.datetime(2021, 7, 4, 16, 30)
print(f"{ek.parse_datetime(d, timezone='America/Los_Angeles') = }")
print(f"{ek.parse_datetime(dtobj, timezone='UTC') = }")

# Ordinal days
print(f"{ek.parse_datetime('2021-176') = }")  # 176th day of 2021 → June 25, 2021
print(f"{ek.parse_datetime('2021-365') = }")  # 365th day of 2021 → December 31, 2021
print(f"{ek.parse_datetime('2021-001') = }")  # 001st day of 2021
print(f"{ek.parse_datetime('2021 32')  = }")   # 32nd day of 2021 → February 1, 2021

# Julian and Modified Julian Dates
print(f"{ek.parse_datetime('JD 2459396.5') = }")  # Julian Date 
print(f"{ek.parse_datetime('2459396.5', format_str='JD') = }")  # Julian Date without prefix
print(f"{ek.parse_datetime('MJD 59396.0') = }")  # Modified Julian Date
print(f"{ek.parse_datetime('59396.0', format_str='MJD') = }")  # MJD without prefix
print(f"{ek.parse_datetime('JD 2451545.0') = }")  # J2000 epoch
print(f"{ek.parse_datetime('MJD 51544.0') = }")  # MJD for J2000 epoch

print(f"{ek.parse_datetime('J2000') = }")  # J2000 epoch → January 1, 2000, 11:58:55.816 UTC
print(f"{ek.parse_datetime('J2000', timezone='PST') = }")  # J2000 in PST timezone
print(f"{ek.parse_datetime('UNIX') = }")
print(f"{ek.parse_datetime('UNIX', timezone='AWST') = }")  # Unix epoch in Western Australia Standard Time

# numpy.datetime64 & pandas.Timestamp
np_dt = np.datetime64('2021-08-15T20:45:00')
pd_ts = pd.Timestamp( '2021-09-10 13:20')
print(f"{ek.parse_datetime(np_dt,    timezone='EST') = }")
print(f"{ek.parse_datetime(pd_ts,    timezone='Europe/Berlin') = }")
not_naive = ek.parse_datetime(np_dt, timezone='EST')
print(f"{not_naive = }")  # Should be timezone-aware
print(f"{ek.parse_datetime(not_naive, timezone='naive') = }")  # Convert to naive datetime

print(f"{ek.parse_datetime('2021') = }")     # Just a year → January 1, 2021
print(f"{ek.parse_datetime('2021-12') = }")  # Just a year and month → December 1, 2021

# Invalid strings
for bad in ['notadate', '32 Feb 2021', '2021-13-01']:
    try:
        print(ek.parse_datetime(bad))
    except Exception as e:
        print(f"Correctly failed on {bad!r}: {e!r}")

# Out-of-range JD/MJD
for bad in ['JD -2445.0', 'MJD -5144.0']:
    try:
        print(ek.parse_datetime(bad))
    except Exception as e:
        print(f"Correctly failed on out-of-datetime-range JD/MJD: {bad!r}: {e!r}")

# Record the end time and calculate duration
end_time = dt.datetime.now()
duration = end_time - start_time
print(f"Script ran for {duration.total_seconds()} seconds.")

# assert parse_datetime('JD 2459396.5') == datetime(2021, 3, 31, 0, 0, tzinfo=timezone.utc)
# assert parse_datetime('MJD 59396.0') == datetime(2021, 3, 31, 0, 0, tzinfo=timezone.utc)
# assert parse_datetime('2025-176') == datetime(2025, 6, 25, tzinfo=timezone.utc)
# assert parse_datetime('44 BC')   # → year =  -43  → Jan 1 –0043 (or via Astropy)
# assert parse_datetime('37 CE')   # → year =   37  → Jan 1 0037
