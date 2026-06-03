# ------------------------------------------------------------
# Elmwood Place parcel address cleanup and possible rental screen
#
# This script was used for cleaning up parcel address fields,
# translating Hamilton County land use class codes into readable
# descriptions, and flagging parcels that may need rental review.
#
# The main idea is simple:
# - Keep the original parcel fields untouched.
# - Add cleaner working fields.
# - Compare street-level address to street-level address.
# - Do not compare a situs street address to a full mailing block.
# - Only screen parcels where the assessed land use suggests people
#   may live there.
#
# This is not meant to prove that a parcel is a rental.
# It creates a review flag.
# ------------------------------------------------------------

import arcpy
import re
from collections import Counter


# ------------------------------------------------------------
# Basic settings
# ------------------------------------------------------------

# Change this if the layer or feature class name is different.
# This can be the layer name from the ArcGIS Pro Contents pane
# or a full path to a feature class.
fc = "Elmwood_Jurisdiction_Clip2"


# ------------------------------------------------------------
# Source field names
#
# These need to be the real field names, not the aliases.
# ------------------------------------------------------------

# Land use class field
class_field = "CLASS"

# Situs / property address fields
situs_num_field = "ADDRNO"
situs_st_field = "ADDRST"
situs_suf_field = "ADDRSF"

# Owner address fields
owner_addr1_field = "OWNAD1"
owner_addr1a_field = "OWNAD1A"
owner_addr2_field = "OWNAD2"      # usually city/state/zip, not used in comparison

# Mailing address fields
mail_addr1_field = "MLADR1"
mail_addr1a_field = "MLADR1A"
mail_addr2_field = "MLADR2"       # usually city/state/zip, not used in comparison

# Delinquent taxes field
delq_taxes_field = "DELQ_TAXES"


# ------------------------------------------------------------
# New working fields created by this script
# ------------------------------------------------------------

class_desc_field = "CLASS_DESC"
live_at_field = "LIVE_AT_YN"

situs_std_field = "SITUS_STD"
owner_std_field = "OWNER_ST_STD"
mail_std_field = "MAIL_ST_STD"

situs_base_field = "SITUS_BASE"
owner_base_field = "OWNER_BASE"
mail_base_field = "MAIL_BASE"

addr_match_field = "ADDR_MATCH"
poss_rent_field = "POSS_RENT_YN"
addr_note_field = "ADDR_NOTE"


# ------------------------------------------------------------
# Hamilton County Auditor land use class descriptions
#
# These are assessment land use descriptions, not zoning.
# ------------------------------------------------------------

class_desc_lookup = {
    300: "INDUSTRIAL - VACANT LAND",
    320: "INDUSTRIAL - HEAVY MANUFACTURING",
    330: "INDUSTRIAL - MEDIUM MANUFACTURING",
    340: "INDUSTRIAL - LIGHT MANUFACTURING",
    350: "INDUSTRIAL - WAREHOUSE",
    370: "INDUSTRIAL - SMALL SHOP",
    399: "INDUSTRIAL - OTHER",

    400: "COMMERCIAL - VACANT LAND",
    401: "COMMERCIAL - APARTMENTS, 4 TO 19 UNITS",
    404: "COMMERCIAL - RETAIL WITH APARTMENTS OVER",
    406: "COMMERCIAL - RETAIL WITH STORAGE OVER",
    412: "COMMERCIAL - NURSING HOME / PRIVATE HOSPITAL",
    418: "COMMERCIAL - DAY CARE / PRIVATE SCHOOLS",
    420: "COMMERCIAL - SMALL DETACHED RETAIL",
    429: "COMMERCIAL - OTHER RETAIL STRUCTURES",
    430: "COMMERCIAL - RESTAURANT, CAFETERIA OR BAR",
    431: "COMMERCIAL - OFFICE WITH APARTMENTS OVER",
    439: "COMMERCIAL - OTHER FOOD SERVICES",
    442: "COMMERCIAL - MEDICAL CLINICS & OFFICES",
    444: "COMMERCIAL - BANKS",
    453: "COMMERCIAL - CAR WASH",
    455: "COMMERCIAL - GARAGES",
    456: "COMMERCIAL - PARKING GARAGES / LOTS",
    465: "COMMERCIAL - LODGE HALL / AMUSEMENT PARKS",
    480: "COMMERCIAL - WAREHOUSE",
    489: "COMMERCIAL - UTILITY",
    499: "COMMERCIAL - OTHER STRUCTURES",

    500: "RESIDENTIAL - VACANT LAND",
    508: "RESIDENTIAL - STREET",
    510: "RESIDENTIAL - SINGLE FAMILY",
    520: "RESIDENTIAL - TWO FAMILY DWELLINGS",
    530: "RESIDENTIAL - THREE FAMILY DWELLINGS",
    599: "RESIDENTIAL - OTHER STRUCTURES",

    610: "PUBLICLY OWNED - STATE OF OHIO",
    620: "PUBLICLY OWNED - HAMILTON COUNTY",
    630: "PUBLICLY OWNED - TOWNSHIPS",
    640: "PUBLICLY OWNED - MUNICIPALITIES",
    645: "PUBLICLY OWNED - METROPOLITAN HOUSING AUTHORITY",
    650: "PUBLICLY OWNED - BOARD OF EDUCATION",
    660: "PUBLICLY OWNED - PARK DISTRICT",
    680: "PUBLICLY OWNED - CHARITIES, HOSPITALS & RETIREMENT HOMES",
    685: "PUBLICLY OWNED - PUBLIC WORSHIP",

    840: "PUBLIC UTILITIES - RAILROADS, USED IN OPERATIONS"
}


# ------------------------------------------------------------
# Land use classes included in the living-use screen
#
# These are the classes I wanted to keep in the possible rental
# review group. This does not mean every parcel here has a dwelling.
# It just means the land use class is relevant enough to review.
# ------------------------------------------------------------

living_use_classes = {
    "COMMERCIAL - APARTMENTS, 4 TO 19 UNITS",
    "COMMERCIAL - OFFICE WITH APARTMENTS OVER",
    "COMMERCIAL - RETAIL WITH APARTMENTS OVER",
    "RESIDENTIAL - OTHER STRUCTURES",
    "RESIDENTIAL - SINGLE FAMILY",
    "RESIDENTIAL - THREE FAMILY DWELLINGS",
    "RESIDENTIAL - TWO FAMILY DWELLINGS",
    "RESIDENTIAL - VACANT LAND"
}


# ------------------------------------------------------------
# Small helper functions
# ------------------------------------------------------------

def field_exists(feature_class, field_name):
    field_names = [f.name for f in arcpy.ListFields(feature_class)]
    return field_name in field_names


def add_text_field_if_missing(feature_class, field_name, length=255):
    if not field_exists(feature_class, field_name):
        arcpy.management.AddField(
            in_table=feature_class,
            field_name=field_name,
            field_type="TEXT",
            field_length=length
        )
        print("Added field:", field_name)
    else:
        print("Field already exists:", field_name)


def clean_part(value):
    if value is None:
        return ""

    text = str(value).strip()

    if text == "":
        return ""

    if text.upper() in ["<NULL>", "NULL", "NONE", "N/A", "NA", "NAN", "UNKNOWN", "UNK"]:
        return ""

    return text


def normalize_class_value(value):
    if value is None:
        return None

    text = str(value).strip()

    if text == "":
        return None

    if text.upper() in ["<NULL>", "NULL", "NONE", "N/A", "NA"]:
        return None

    try:
        return int(float(text))
    except:
        return None


def clean_text(value):
    if value is None:
        return ""

    text = str(value).strip().upper()

    if text in ["", "<NULL>", "NULL", "NONE", "N/A", "NA"]:
        return ""

    return text


# ------------------------------------------------------------
# Address cleaning functions
# ------------------------------------------------------------

def standardize_address(*parts):
    """
    Standardizes an address so that the same address written slightly
    different ways can still be compared.
    """

    cleaned_parts = []

    for p in parts:
        cleaned = clean_part(p)
        if cleaned:
            cleaned_parts.append(cleaned)

    if not cleaned_parts:
        return ""

    text = " ".join(cleaned_parts).upper()

    # punctuation can cause false mismatches
    text = re.sub(r"[.,;:#]", " ", text)

    # basic cleanup
    text = text.replace("&", " AND ")
    text = re.sub(r"\s+", " ", text).strip()

    # direction words
    direction_replacements = {
        r"\bNORTH\b": "N",
        r"\bSOUTH\b": "S",
        r"\bEAST\b": "E",
        r"\bWEST\b": "W",
        r"\bNORTHEAST\b": "NE",
        r"\bNORTHWEST\b": "NW",
        r"\bSOUTHEAST\b": "SE",
        r"\bSOUTHWEST\b": "SW"
    }

    for old, new in direction_replacements.items():
        text = re.sub(old, new, text)

    # street suffixes
    suffix_replacements = {
        r"\bSTREET\b": "ST",
        r"\bSTRT\b": "ST",
        r"\bAVENUE\b": "AVE",
        r"\bAV\b": "AVE",
        r"\bROAD\b": "RD",
        r"\bDRIVE\b": "DR",
        r"\bLANE\b": "LN",
        r"\bBOULEVARD\b": "BLVD",
        r"\bCOURT\b": "CT",
        r"\bPLACE\b": "PL",
        r"\bTERRACE\b": "TER",
        r"\bCIRCLE\b": "CIR",
        r"\bPARKWAY\b": "PKWY",
        r"\bHIGHWAY\b": "HWY",
        r"\bPIKE\b": "PIKE"
    }

    for old, new in suffix_replacements.items():
        text = re.sub(old, new, text)

    # unit/admin words
    unit_replacements = {
        r"\bSUITE\b": "STE",
        r"\bAPARTMENT\b": "APT",
        r"\bUNIT\b": "APT",
        r"\bROOM\b": "RM",
        r"\bFLOOR\b": "FL",
        r"\bBUILDING\b": "BLDG",
        r"\bDEPARTMENT\b": "DEPT",
        r"\bATTENTION\b": "ATTN"
    }

    for old, new in unit_replacements.items():
        text = re.sub(old, new, text)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def remove_unit(address):
    """
    Creates a base version of the address for comparison.
    This removes suite, apartment, department, attention lines, etc.
    """

    if address is None:
        return ""

    text = str(address).upper().strip()

    if text == "":
        return ""

    # Remove unit/admin text and anything after it.
    # Example: 311 ELM ST STE 270 becomes 311 ELM ST.
    text = re.sub(
        r"\b(APT|STE|SUITE|UNIT|FL|FLOOR|RM|ROOM|BLDG|BUILDING|DEPT|ATTN)\b.*$",
        "",
        text
    ).strip()

    # Sometimes unit numbers come after the suffix without a unit word.
    # Example: 311 ELM ST 1201 becomes 311 ELM ST.
    street_suffixes = {
        "ST", "AVE", "RD", "DR", "LN", "BLVD", "CT",
        "PL", "TER", "CIR", "PKWY", "HWY", "PIKE"
    }

    parts = text.split()

    if len(parts) >= 4:
        last = parts[-1]
        second_last = parts[-2]

        if second_last in street_suffixes and re.match(r"^[A-Z0-9\-]+$", last):
            text = " ".join(parts[:-1])

    text = re.sub(r"\s+", " ", text).strip()

    return text


def compare_addresses(situs_base, owner_base, mail_base):
    """
    Compares the cleaned street-level address fields.

    This is the logic I ended up wanting:
    if the owner address differs from situs OR the mailing address
    differs from situs, it should be treated as needing possible
    rental review.
    """

    situs_base = situs_base or ""
    owner_base = owner_base or ""
    mail_base = mail_base or ""

    if not situs_base:
        return "NO_SITUS_ADDRESS"

    owner_available = bool(owner_base)
    mail_available = bool(mail_base)

    owner_matches = owner_base == situs_base if owner_available else None
    mail_matches = mail_base == situs_base if mail_available else None

    if not owner_available and not mail_available:
        return "NO_COMPARABLE_ADDRESS"

    if owner_matches is True and mail_matches is True:
        return "OWNER_AND_MAIL_MATCH_SITUS"

    if owner_matches is False and mail_matches is False:
        return "OWNER_AND_MAIL_DIFFER_FROM_SITUS"

    if owner_matches is False and mail_matches is True:
        return "OWNER_DIFFERS_FROM_SITUS"

    if owner_matches is True and mail_matches is False:
        return "MAIL_DIFFERS_FROM_SITUS"

    if owner_matches is False and not mail_available:
        return "OWNER_DIFFERS_FROM_SITUS_NO_MAIL"

    if mail_matches is False and not owner_available:
        return "MAIL_DIFFERS_FROM_SITUS_NO_OWNER"

    if owner_matches is True and not mail_available:
        return "OWNER_MATCHES_SITUS_NO_MAIL"

    if mail_matches is True and not owner_available:
        return "MAIL_MATCHES_SITUS_NO_OWNER"

    return "REVIEW"


def possible_rental_flag(live_at_yn, match_type):
    """
    Possible rental means:
    - parcel is in a living-use class, and
    - owner or mailing address differs from situs.

    This is still just a screening flag.
    """

    live_at_yn = clean_part(live_at_yn).upper()
    match_type = match_type or ""

    if live_at_yn != "Y":
        return "N"

    rental_match_types = {
        "OWNER_AND_MAIL_DIFFER_FROM_SITUS",
        "OWNER_DIFFERS_FROM_SITUS",
        "MAIL_DIFFERS_FROM_SITUS",
        "OWNER_DIFFERS_FROM_SITUS_NO_MAIL",
        "MAIL_DIFFERS_FROM_SITUS_NO_OWNER"
    }

    if match_type in rental_match_types:
        return "Y"

    return "N"


def make_note(situs_std, owner_std, mail_std, situs_base, owner_base, mail_base, match_type, live_at_yn):
    notes = []

    if not situs_std:
        notes.append("Missing situs address")

    if not owner_std:
        notes.append("Missing owner street address")

    if not mail_std:
        notes.append("Missing mailing street address")

    if owner_std and owner_base != owner_std:
        notes.append("Owner unit/suite/admin text removed")

    if mail_std and mail_base != mail_std:
        notes.append("Mailing unit/suite/admin text removed")

    if live_at_yn not in [None, "", "Y", "N", "REVIEW"]:
        notes.append("LIVE_AT_YN needs review")

    if match_type == "OWNER_AND_MAIL_DIFFER_FROM_SITUS":
        notes.append("Owner and mailing addresses differ from situs")

    elif match_type == "OWNER_DIFFERS_FROM_SITUS":
        notes.append("Owner address differs from situs")

    elif match_type == "MAIL_DIFFERS_FROM_SITUS":
        notes.append("Mailing address differs from situs")

    elif match_type == "OWNER_DIFFERS_FROM_SITUS_NO_MAIL":
        notes.append("Owner address differs from situs; no mailing comparison")

    elif match_type == "MAIL_DIFFERS_FROM_SITUS_NO_OWNER":
        notes.append("Mailing address differs from situs; no owner comparison")

    elif match_type == "OWNER_AND_MAIL_MATCH_SITUS":
        notes.append("Owner and mailing addresses match situs")

    elif match_type == "NO_COMPARABLE_ADDRESS":
        notes.append("No owner or mailing address to compare")

    elif match_type == "NO_SITUS_ADDRESS":
        notes.append("No situs address to compare")

    elif match_type == "REVIEW":
        notes.append("Address comparison needs review")

    if not notes:
        notes.append("Standardized and compared")

    return "; ".join(notes)[:255]


# ------------------------------------------------------------
# Check that the main fields exist before doing anything
# ------------------------------------------------------------

required_fields = [
    class_field,
    situs_num_field,
    situs_st_field,
    situs_suf_field,
    owner_addr1_field,
    owner_addr1a_field,
    mail_addr1_field,
    mail_addr1a_field
]

existing_fields = [f.name for f in arcpy.ListFields(fc)]

missing_fields = []

for f in required_fields:
    if f not in existing_fields:
        missing_fields.append(f)

if missing_fields:
    print("These fields were not found:")
    for f in missing_fields:
        print(" -", f)

    print("")
    print("Available fields:")
    for f in arcpy.ListFields(fc):
        print(f.name, "| alias:", f.aliasName)

    raise Exception("Missing required fields. Update the field names at the top of the script.")


# ------------------------------------------------------------
# Add the working fields
# ------------------------------------------------------------

add_text_field_if_missing(fc, class_desc_field, 255)
add_text_field_if_missing(fc, live_at_field, 20)

add_text_field_if_missing(fc, situs_std_field, 255)
add_text_field_if_missing(fc, owner_std_field, 255)
add_text_field_if_missing(fc, mail_std_field, 255)

add_text_field_if_missing(fc, situs_base_field, 255)
add_text_field_if_missing(fc, owner_base_field, 255)
add_text_field_if_missing(fc, mail_base_field, 255)

add_text_field_if_missing(fc, addr_match_field, 100)
add_text_field_if_missing(fc, poss_rent_field, 10)
add_text_field_if_missing(fc, addr_note_field, 255)


# ------------------------------------------------------------
# First quick check: list the CLASS values in the table
# ------------------------------------------------------------

class_values = []

with arcpy.da.SearchCursor(fc, [class_field]) as cursor:
    for row in cursor:
        val = row[0]

        if val is None:
            val = "<Null>"

        class_values.append(val)

class_counts = Counter(class_values)

print("")
print("Observed CLASS values:")
print("-" * 60)

for value, count in sorted(class_counts.items(), key=lambda x: str(x[0])):
    print(str(value) + ":", count)

print("-" * 60)
print("Total unique CLASS values:", len(class_counts))


# ------------------------------------------------------------
# Main update cursor
#
# This is where the land use description, living-use flag,
# address fields, address comparison, and possible rental flag
# all get written.
# ------------------------------------------------------------

cursor_fields = [
    class_field,
    class_desc_field,
    live_at_field,

    situs_num_field,
    situs_st_field,
    situs_suf_field,

    owner_addr1_field,
    owner_addr1a_field,

    mail_addr1_field,
    mail_addr1a_field,

    situs_std_field,
    owner_std_field,
    mail_std_field,

    situs_base_field,
    owner_base_field,
    mail_base_field,

    addr_match_field,
    poss_rent_field,
    addr_note_field
]

updated_count = 0
unmapped_class_count = 0

live_yes_count = 0
live_no_count = 0
live_review_count = 0

rental_yes_count = 0
rental_no_count = 0

with arcpy.da.UpdateCursor(fc, cursor_fields) as cursor:
    for row in cursor:

        # Pull row values into named variables.
        raw_class = row[0]

        situs_num = row[3]
        situs_st = row[4]
        situs_suf = row[5]

        owner_addr1 = row[6]
        owner_addr1a = row[7]

        mail_addr1 = row[8]
        mail_addr1a = row[9]

        # Translate CLASS into CLASS_DESC.
        class_code = normalize_class_value(raw_class)

        if class_code is None:
            class_desc = "NO CLASS VALUE"
            unmapped_class_count += 1

        elif class_code in class_desc_lookup:
            class_desc = class_desc_lookup[class_code]

        else:
            class_desc = "UNMAPPED CLASS CODE - " + str(class_code)
            unmapped_class_count += 1

        # Create the living-use screen.
        cleaned_class_desc = clean_text(class_desc)

        if cleaned_class_desc == "":
            live_at_yn = "REVIEW"
            live_review_count += 1

        elif cleaned_class_desc in living_use_classes:
            live_at_yn = "Y"
            live_yes_count += 1

        elif cleaned_class_desc == "NO CLASS VALUE" or cleaned_class_desc.startswith("UNMAPPED"):
            live_at_yn = "REVIEW"
            live_review_count += 1

        else:
            live_at_yn = "N"
            live_no_count += 1

        # Build standardized street-level addresses.
        #
        # Important:
        # Owner Address 2 and Mailing Address 2 are not used here because
        # they often contain city/state/zip, not the street address.
        situs_std = standardize_address(situs_num, situs_st, situs_suf)
        owner_std = standardize_address(owner_addr1, owner_addr1a)
        mail_std = standardize_address(mail_addr1, mail_addr1a)

        # Remove units / suites / admin text for base comparison.
        situs_base = remove_unit(situs_std)
        owner_base = remove_unit(owner_std)
        mail_base = remove_unit(mail_std)

        # Compare the base address fields.
        addr_match = compare_addresses(situs_base, owner_base, mail_base)

        # Create possible rental review flag.
        poss_rent_yn = possible_rental_flag(live_at_yn, addr_match)

        if poss_rent_yn == "Y":
            rental_yes_count += 1
        else:
            rental_no_count += 1

        # Create short note.
        addr_note = make_note(
            situs_std,
            owner_std,
            mail_std,
            situs_base,
            owner_base,
            mail_base,
            addr_match,
            live_at_yn
        )

        # Write back to the row.
        row[1] = class_desc
        row[2] = live_at_yn

        row[10] = situs_std
        row[11] = owner_std
        row[12] = mail_std

        row[13] = situs_base
        row[14] = owner_base
        row[15] = mail_base

        row[16] = addr_match
        row[17] = poss_rent_yn
        row[18] = addr_note

        cursor.updateRow(row)
        updated_count += 1


# ------------------------------------------------------------
# Summarize CLASS_DESC after updating
# ------------------------------------------------------------

class_desc_values = []

with arcpy.da.SearchCursor(fc, [class_desc_field]) as cursor:
    for row in cursor:
        val = row[0]

        if val is None or str(val).strip() == "":
            val = "<Null or blank>"
        else:
            val = str(val).strip()

        class_desc_values.append(val)

class_desc_counts = Counter(class_desc_values)

print("")
print("CLASS_DESC summary:")
print("-" * 80)

for value, count in sorted(class_desc_counts.items(), key=lambda x: str(x[0])):
    print(value + ":", count)

print("-" * 80)


# ------------------------------------------------------------
# Summarize address match values
# ------------------------------------------------------------

addr_match_values = []

with arcpy.da.SearchCursor(fc, [addr_match_field]) as cursor:
    for row in cursor:
        val = row[0]

        if val is None or str(val).strip() == "":
            val = "<Null or blank>"
        else:
            val = str(val).strip()

        addr_match_values.append(val)

addr_match_counts = Counter(addr_match_values)

print("")
print("ADDR_MATCH summary:")
print("-" * 80)

for value, count in sorted(addr_match_counts.items(), key=lambda x: str(x[0])):
    print(value + ":", count)

print("-" * 80)


# ------------------------------------------------------------
# Sum delinquent taxes
# ------------------------------------------------------------

def sum_numeric_field(feature_class, value_field, where_field=None, where_value=None):
    total = 0.0
    used_count = 0
    null_count = 0
    non_numeric_count = 0

    if where_field:
        fields = [value_field, where_field]
    else:
        fields = [value_field]

    if not field_exists(feature_class, value_field):
        print("")
        print("Could not summarize", value_field, "because the field was not found.")
        return None

    if where_field and not field_exists(feature_class, where_field):
        print("")
        print("Could not summarize by", where_field, "because the field was not found.")
        return None

    with arcpy.da.SearchCursor(feature_class, fields) as cursor:
        for row in cursor:

            if where_field:
                filter_val = row[1]
                if str(filter_val).strip().upper() != str(where_value).strip().upper():
                    continue

            value = row[0]

            if value is None or str(value).strip() == "":
                null_count += 1
                continue

            try:
                total += float(value)
                used_count += 1
            except:
                non_numeric_count += 1

    return {
        "total": total,
        "used_count": used_count,
        "null_count": null_count,
        "non_numeric_count": non_numeric_count
    }


all_tax_sum = sum_numeric_field(fc, delq_taxes_field)

rental_tax_sum = sum_numeric_field(
    fc,
    delq_taxes_field,
    where_field=poss_rent_field,
    where_value="Y"
)


# ------------------------------------------------------------
# Final printout
# ------------------------------------------------------------

print("")
print("Final script summary")
print("=" * 80)
print("Records updated:", updated_count)
print("Null or unmapped CLASS values:", unmapped_class_count)

print("")
print("LIVE_AT_YN counts")
print("Y:", live_yes_count)
print("N:", live_no_count)
print("REVIEW:", live_review_count)

print("")
print("POSS_RENT_YN counts")
print("Y:", rental_yes_count)
print("N:", rental_no_count)

if all_tax_sum:
    print("")
    print("Delinquent taxes, all records")
    print("Sum: ${:,.2f}".format(all_tax_sum["total"]))
    print("Records included:", all_tax_sum["used_count"])
    print("Null/blank skipped:", all_tax_sum["null_count"])
    print("Non-numeric skipped:", all_tax_sum["non_numeric_count"])

if rental_tax_sum:
    print("")
    print("Delinquent taxes, possible rental review records")
    print("Sum: ${:,.2f}".format(rental_tax_sum["total"]))
    print("Records included:", rental_tax_sum["used_count"])
    print("Null/blank skipped:", rental_tax_sum["null_count"])
    print("Non-numeric skipped:", rental_tax_sum["non_numeric_count"])

print("")
print("Fields created or updated:")
print("-", class_desc_field)
print("-", live_at_field)
print("-", situs_std_field)
print("-", owner_std_field)
print("-", mail_std_field)
print("-", situs_base_field)
print("-", owner_base_field)
print("-", mail_base_field)
print("-", addr_match_field)
print("-", poss_rent_field)
print("-", addr_note_field)

print("")
print("Done.")