"""What the user did after the first chat, read from the same conversation file.

Every file is one user + one astrologer, so these are outcomes with THAT astrologer:
  n_consults        consultations in the file
  return_min        minutes from the end of the first chat to the start of the second
  consults_7d       consultations started within 7 days of the first
  first_chat_min    length of the first chat in minutes
Note: every pair in this dataset has 5+ consultations, so there are no users who
never came back; the outcomes measure how much and how fast, not whether.
"""
import pandas as pd

START = "Consultation started"


def compute(path):
    df = pd.read_csv(path, dtype={"Message": str}).iloc[::-1].reset_index(drop=True)
    df["ts"] = pd.to_datetime(df["Date"] + " " + df["Time"])
    df = df.sort_values("ts", kind="stable").reset_index(drop=True)
    df["Message"] = df["Message"].fillna("")
    starts = df.loc[df["Message"].str.startswith(START), "ts"].tolist()
    if not starts:
        return {}
    first_end = df.loc[df["ts"] < starts[1], "ts"].max() if len(starts) > 1 else df["ts"].max()
    out = {
        "n_consults": len(starts),
        "first_chat_min": round((first_end - starts[0]).total_seconds() / 60, 1),
        "consults_7d": sum(s - starts[0] <= pd.Timedelta(days=7) for s in starts),
        "return_min": round((starts[1] - first_end).total_seconds() / 60, 1) if len(starts) > 1 else None,
    }
    return out
