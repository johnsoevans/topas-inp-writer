# toReel_v1.py
#
# Will read .xyd files output from a TOPAS v7 or v8 analysis in Reel format
# If there is a results.txt file present in the folder it will put the Reel metadata at the top of the file
# If no results.txt then a standard text file is written for other plotting programs
#
# Assumes TOPAS writes out X, Y phase information without the background then determines background
# from ycalc_total - sum_of_phases_ycalc
#
# Assumes default heading names in results.txt but these can be changed
#
# Multiprocessing implemented
#
# JSOE & ABB May 2026
#
# 10/6/2026
#   Robust column naming system added (tth, Y_obs, Y_calc, Y_res)
#   Optional SigmaYobs handling (only used for .xye output, never written elsewhere)
#   Phases now read with X,Y and matches to the main tth grid as Get(phase_ycalc) can have different X range
#   Improved robustness of df's

import sys
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial
from io import StringIO


# =========================
# User settings, defaults normally ok
# =========================
resultsFile = 'results.txt'
filename_reel_col = 'filename_reel'
filename_col = 'filename'
temperature_col = 'Temperature'
lam_col = 'lam'
r_wp_col = 'r_wp'
correct_background = True # assumes background is everything that is not an outputted Get(phase_ycalc)
write_background_subtracted = False # optionally create background subtracted xy or xye file
background_subtracted_directory = 'data_background_subtracted'
background_offset = 10 # add to all data to avoid negative values 
delete_xyd = True # normally true set to false for debugging
input_suffix = '.xyd'
processed_suffix = '.xyy'

# =========================
# Column label helpers just in case; best to use standard labels in TOPAS
# =========================
def standardize_columns(df):
    """
    Standardise TOPAS / Reel column naming into consistent internal format:
    tth, Y_obs, Y_calc, Y_res, Background, SigmaYobs (optional)
    """

    rename_map = {}
    for c in df.columns:
        c_clean = str(c).strip().lower()
        # 2-theta axis
        if c_clean in ["x", "tth", "2theta", "two_theta"]:
            rename_map[c] = "tth"
        # observed intensity
        elif c_clean in ["yobs", "y_observed", "iobs"]:
            rename_map[c] = "Y_obs"
        # calculated intensity
        elif c_clean in ["ycalc", "y_calculated", "icalc"]:
            rename_map[c] = "Y_calc"
        # residuals (if already present)
        elif c_clean in ["yobs-ycalc", "residual", "y_res"]:
            rename_map[c] = "Y_res"
        # background
        elif c_clean == "background":
            rename_map[c] = "Background"
        # uncertainties (used only for background-subtracted xye output)
        elif c_clean in ["sigmayobs", "sigyobs"]:
            rename_map[c] = "SigmaYobs"

    return df.rename(columns=rename_map)


def strip_output_only_columns(df):
    """
    Ensure internal-only columns (e.g. SigmaYobs) are never written to main outputs.
    """
    return df.drop(columns=["SigmaYobs"], errors="ignore")


# =========================
# Main entry
# =========================
def main():

    if len(sys.argv) < 2:
        print("Usage: python toReel_v1.py <directory_name>")
        return

    directory = sys.argv[1]

    if not os.path.isdir(directory):
        print(f"Directory not found: {directory}")
        return

    if write_background_subtracted:
        os.makedirs(background_subtracted_directory, exist_ok=True)

    results_df = load_results_file()
    xyd_files = find_xyd_files(directory)

    if not xyd_files:
        print("No .xyd files found.")
        return

    # multiprocessing setup
    num_workers = max(1, cpu_count() - 1)
    func = partial(process_file, results_df=results_df)

    with Pool(processes=num_workers) as pool:
        results = list(tqdm(
            pool.imap(func, xyd_files, chunksize=10),
            total=len(xyd_files),
            desc="Processing .xyd files"
        ))

    # summary at end
    print("\nSummary of to_Reel run:")
    print(f"Number workers used: {num_workers}")
    print(f"Processed files: {results.count('done')}")
    print(f"Skipped files:   {results.count('skipped')}")
    print(f"Total files:     {len(xyd_files)}")


# =========================
# Load results (results.txt) containing refined parameters
# =========================
def load_results_file():

    if not os.path.exists(resultsFile):
        print(f"WARNING: {resultsFile} not found. Continuing without metadata.")
        return None

    try:
        return pd.read_csv(resultsFile, sep=r"\s+")
    except Exception as e:
        print(f"Error reading {resultsFile}: {e}")
        return None


# =========================
# Find .xyd files to process
# =========================
def find_xyd_files(directory):

    files = []
    for f in os.listdir(directory):
        if f.endswith(input_suffix):
            files.append(os.path.join(directory, f))
    return files


# =========================
# Process a single .xyd file
# =========================
def process_file(filepath, results_df):

    stem = os.path.splitext(os.path.basename(filepath))[0]

    base_df, phase_data = parse_xyd(filepath)

    # enforce internal naming convention immediately
    base_df = standardize_columns(base_df)

    result = combine_data(stem, base_df, phase_data)
    if result is None:
        return "skipped"

    combined_df = result

    metadata_lines = []
    if results_df is not None:
        metadata_lines = build_metadata(results_df, stem)

    output_path = os.path.join(
        os.path.dirname(filepath),
        stem + processed_suffix
    )

    write_output(output_path, metadata_lines, combined_df)

    # optional cleanup
    if delete_xyd:
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"WARNING: Could not delete {filepath}: {e}")

    return "done"


# =========================
# Parse .xyd file to Rietveld data (base_df) and phase contributions (phase_data)
# =========================
def parse_xyd(filepath):

    with open(filepath, "r") as f:
        lines = f.readlines()
    phase_data = {}

    # 1. locate END OF PHASE
    i = 0
    n = len(lines)
    data_block = []
    while i < n:
        line = lines[i].strip()
        if line.startswith("END OF PHASE"):
            i += 1
            break
        if line:
            data_block.append(line)
        i += 1

    # 2. Use first line of file to get header information
    header = data_block[0].split()
    data_lines = data_block[1:]

    # 3. build DataFrame and set names
    base_df = pd.read_csv(
        StringIO("\n".join(data_lines)),
        sep=r"\s+",
        header=None
    )
    base_df.columns = header  

    # 4. phase parsing
    while i < n:

        line = lines[i].strip()
        if not line:
            i += 1
            continue

        phase_name = line
        i += 1

        phase_tth = []
        phase_y = []

        while i < n:
            line = lines[i].strip()

            if line.upper().startswith("END"):
                i += 1
                break

            parts = line.split()

            if len(parts) >= 2:
                phase_tth.append(float(parts[0]))
                phase_y.append(float(parts[1]))

            i += 1

        phase_data[phase_name] = {
            "tth": np.array(phase_tth),
            "Y": np.array(phase_y)
        }

    return base_df, phase_data


# =========================
# Combine the Rietveld data (base_df) and phase contributions (phase_data)
# Do the background subtraction and optionally write out background subtracted observed data
# =========================
def combine_data(stem, base_df, phase_data):

    if "tth" not in base_df.columns:
        print(f"{stem}: missing tth column")
        return None

    # x = base_df["tth"].values

    phase_cols = []

    # Add in the phase contributions
    for name, phase in phase_data.items():

        phase_series = pd.Series(
            phase["Y"],
            index=np.round(phase["tth"], 8)
        )

        base_df[name] = (
            phase_series
            .reindex(np.round(base_df["tth"], 8), fill_value=0)
            .to_numpy()
        )

        phase_cols.append(name)


    # Subtract total_phases to create the Background
    if correct_background and phase_cols:

        total_phases = base_df[phase_cols].sum(axis=1)

        base_df["Background"] = base_df["Y_calc"] - total_phases
        for phase in phase_cols:
            base_df[phase] += base_df["Background"]


        # Write background-subtracted .xy or .xye files
        if write_background_subtracted:
            y_bkg_sub = base_df["Y_obs"] - base_df["Background"] + background_offset
            use_xye = False

            # only use xye if SigmaYobs exists and contains at least one non-zero value
            if "SigmaYobs" in base_df.columns:
                sigma = pd.to_numeric(base_df["SigmaYobs"], errors="coerce").fillna(0)
                if np.nanmax(sigma) > 0:
                    use_xye = True

            if use_xye:
                out = pd.DataFrame({
                    "tth": base_df["tth"],
                    "Y": y_bkg_sub,
                    "E": sigma
                })
                out.to_csv(
                    os.path.join(
                        background_subtracted_directory,
                        f"{stem}_bkg.xye"
                    ),
                    sep=" ",
                    index=False,
                    header=False
                )
            else:
                out = pd.DataFrame({
                    "tth": base_df["tth"],
                    "Y": y_bkg_sub
                })
                out.to_csv(
                    os.path.join(
                        background_subtracted_directory,
                        f"{stem}_bkg.xy"
                    ),
                    sep=" ",
                    index=False,
                    header=False
                )

    # remove ad done in write_output()
    # IMPORTANT: remove internal-only columns before writing anything
    #base_df = strip_output_only_columns(base_df)

    #return base_df, list(base_df.columns)
    return base_df

# =========================
# Build metadata from results.txt
# =========================
def build_metadata(df, stem):
    
    #use a strict match on filename_reel
    #rows = df[df[filename_reel_col].astype(str).str.contains(stem, na=False)]
    rows = df[df[filename_reel_col].astype(str) == stem]

    if rows.empty:
        print(f"WARNING: No matching results.txt row for '{stem}'")
        return []

    row = rows.iloc[0]
    if len(rows) > 1:
        print(f"WARNING: Multiple matches for {stem}")

    lines = []

    def is_numeric(value):
        try:
            float(value)
            return True
        except:
            return False

    def safe_get(col):
        if col in row.index and is_numeric(row[col]):
            return row[col]
        return "NA"

    # Required fields for Reel
    lines.append(str(row.get(filename_col, stem)))
    lines.append(f"R_wp: {safe_get(r_wp_col)}")
    lines.append(f"Wavelength (A): {safe_get(lam_col)}")
    lines.append(f"Temperature (K): {safe_get(temperature_col)}")

    # Read the metadata from results.txt
    skip_cols = {
        filename_col,
        filename_reel_col,
        r_wp_col,
        lam_col,
        temperature_col
    }

    for col in df.columns:
        if col in skip_cols:
            continue
        if col.startswith("esd_"):
            continue

        value = row[col]

        if is_numeric(value):
            lines.append(f"{col}: {value}")

    # --- footer (these are NOT part of metadata) ---
    lines.append("COMMENTS")
    lines.append("")
    lines.append("END OF HEADER")

    return lines


# =========================
# Write the output .xyy file
# =========================
def write_output(path, metadata_lines, df):

    #get rid of the SigmaYobs column before writing
    df = strip_output_only_columns(df)

    with open(path, 'w') as f:

        # metadata
        for line in metadata_lines:
            f.write(line + "\n")

        # headers
        f.write(" ".join(df.columns) + "\n")

        # data
        for _, row in df.iterrows():
            f.write(" ".join(map(str, row.values)) + "\n")


# =========================
# Execute script from here
# =========================
if __name__ == "__main__":
    main()