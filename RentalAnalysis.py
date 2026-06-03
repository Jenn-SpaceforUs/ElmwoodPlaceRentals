# Elmwood Place Rental Review Map
# Space for Us
#
# This script takes the rental review parcels and the village boundary exported
# from ArcGIS Pro as GeoJSON files, puts them into a Folium web map, and makes
# a clickable parcel review map.
#
# The parcels shown on the map are the possible rental properties that need
# review. These are screening results, not final rental determinations.

import geopandas as gpd
import folium
from branca.element import Template, MacroElement


# ------------------------------------------------------------
# File locations
# ------------------------------------------------------------

parcel_file = r"C:\Users\14154\Desktop\The Village of Elmwood Place\Rentals_FeaturesToJSON.geojson"

boundary_file = r"C:\Users\14154\Desktop\The Village of Elmwood Place\Elmwood_Jurisd_FeaturesToJSO.geojson"

out_map = r"C:\Users\14154\Desktop\The Village of Elmwood Place\elmwood_rental_review_map.html"


# ------------------------------------------------------------
# Logo
# ------------------------------------------------------------
# This is the logo file in the docs folder of the GitHub Pages repo.
# If the image does not show up, check that GitHub Pages is publishing
# from the docs folder and that the file name is exactly Logo.PNG.

use_logo = True
logo_url = "https://jenn-spaceforus.github.io/ElmwoodPlaceRentals/Logo.PNG"


# ------------------------------------------------------------
# Read in the two GeoJSON files
# ------------------------------------------------------------

parcels = gpd.read_file(parcel_file)
boundary = gpd.read_file(boundary_file)

print("Parcel file loaded.")
print("Number of parcels:", len(parcels))
print("Parcel CRS:", parcels.crs)

print("\nBoundary file loaded.")
print("Number of boundary features:", len(boundary))
print("Boundary CRS:", boundary.crs)


# ------------------------------------------------------------
# Convert to latitude/longitude for Folium
# ------------------------------------------------------------
# ArcGIS exported the data in a local/projected coordinate system.
# Folium needs EPSG:4326.

parcels = parcels.to_crs(epsg=4326)
boundary = boundary.to_crs(epsg=4326)

print("\nConverted both layers to EPSG:4326.")


# ------------------------------------------------------------
# Print the fields just so I can double-check them in the console
# ------------------------------------------------------------

print("\nParcel fields:")
for f in parcels.columns:
    print(f)


# ------------------------------------------------------------
# Little cleanup functions for the popup text
# ------------------------------------------------------------

def clean_value(value):
    # Keeps nulls and weird empty values from showing up in the popup.
    if value is None:
        return ""

    value = str(value).strip()

    if value.lower() in ["none", "nan", "null"]:
        return ""

    return value


def get_value(row, possible_fields):
    # Looks for the first field that exists and has a real value.
    # This is helpful because I changed field names a few times while building this.
    for field in possible_fields:
        if field in row.index:
            value = clean_value(row[field])
            if value != "":
                return value

    return ""


def yes_no(value):
    # Makes Y/N fields easier to read in the popup.
    value = clean_value(value)

    if value.upper() == "Y":
        return "Yes"

    if value.upper() == "N":
        return "No"

    return value


# ------------------------------------------------------------
# Popup content
# ------------------------------------------------------------
# These fields are the main ones I want people to see:
#
# OWNNM1
# SITUS_STD
# OWNER_ST_STD
# MAIL_ST_STD
# SITUS_BASE
# OWNER_BASE
# MAIL_BASE
# ADDR_MATCH
# POSS_RENT_YN
# ADDR_NOTE
# CLASS_DESC
# LIVE_AT_YN
#
# I removed APN / parcel ID from the popup because it was not displaying
# the way I wanted and it is not necessary for the public review version.

def make_popup(row):

    owner_name = get_value(row, ["OWNNM1", "Owner Name 1"])

    situs_std = get_value(row, ["SITUS_STD"])
    owner_st_std = get_value(row, ["OWNER_ST_STD"])
    mail_st_std = get_value(row, ["MAIL_ST_STD"])

    situs_base = get_value(row, ["SITUS_BASE"])
    owner_base = get_value(row, ["OWNER_BASE"])
    mail_base = get_value(row, ["MAIL_BASE"])

    addr_match = get_value(row, ["ADDR_MATCH"])
    possible_rental = yes_no(get_value(row, ["POSS_RENT_YN"]))
    addr_note = get_value(row, ["ADDR_NOTE"])

    class_desc = get_value(row, ["CLASS_DESC"])
    live_at_yn = yes_no(get_value(row, ["LIVE_AT_YN"]))

    html = f"""
    <div style="
        font-family: Arial, sans-serif;
        width: 390px;
        color: #2b2b2b;
    ">

        <div style="
            font-size: 15px;
            font-weight: 700;
            color: #24352f;
            margin-bottom: 4px;
            line-height: 1.25;
        ">
            Potential Rental Property Review
        </div>

        <div style="
            font-size: 11px;
            color: #666666;
            margin-bottom: 10px;
            line-height: 1.35;
        ">
            Screening result based on standardized address fields, assessed land use,
            and owner or mailing address comparison.
        </div>

        <div style="
            border-top: 1px solid #dddddd;
            padding-top: 8px;
            margin-top: 6px;
        ">
            <div style="
                font-weight: 700;
                font-size: 12px;
                margin-bottom: 5px;
                color: #24352f;
            ">
                Review Summary
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <tr>
                    <td style="font-weight: 700; width: 40%; padding: 3px 0;">Potential rental</td>
                    <td style="padding: 3px 0;">{possible_rental}</td>
                </tr>
                <tr>
                    <td style="font-weight: 700; padding: 3px 0;">Address match result</td>
                    <td style="padding: 3px 0;">{addr_match}</td>
                </tr>
                <tr>
                    <td style="font-weight: 700; padding: 3px 0;">Review note</td>
                    <td style="padding: 3px 0;">{addr_note}</td>
                </tr>
            </table>
        </div>

        <div style="
            border-top: 1px solid #dddddd;
            padding-top: 8px;
            margin-top: 8px;
        ">
            <div style="
                font-weight: 700;
                font-size: 12px;
                margin-bottom: 5px;
                color: #24352f;
            ">
                Property and Owner
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <tr>
                    <td style="font-weight: 700; width: 40%; padding: 3px 0;">Owner</td>
                    <td style="padding: 3px 0;">{owner_name}</td>
                </tr>
                <tr>
                    <td style="font-weight: 700; padding: 3px 0;">Situs address</td>
                    <td style="padding: 3px 0;">{situs_std}</td>
                </tr>
            </table>
        </div>

        <div style="
            border-top: 1px solid #dddddd;
            padding-top: 8px;
            margin-top: 8px;
        ">
            <div style="
                font-weight: 700;
                font-size: 12px;
                margin-bottom: 5px;
                color: #24352f;
            ">
                Standardized Address Fields
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <tr>
                    <td style="font-weight: 700; width: 40%; padding: 3px 0;">Situs address</td>
                    <td style="padding: 3px 0;">{situs_std}</td>
                </tr>
                <tr>
                    <td style="font-weight: 700; padding: 3px 0;">Owner street address</td>
                    <td style="padding: 3px 0;">{owner_st_std}</td>
                </tr>
                <tr>
                    <td style="font-weight: 700; padding: 3px 0;">Mailing street address</td>
                    <td style="padding: 3px 0;">{mail_st_std}</td>
                </tr>
            </table>
        </div>

        <div style="
            border-top: 1px solid #dddddd;
            padding-top: 8px;
            margin-top: 8px;
        ">
            <div style="
                font-weight: 700;
                font-size: 12px;
                margin-bottom: 5px;
                color: #24352f;
            ">
                Address Bases Used for Matching
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <tr>
                    <td style="font-weight: 700; width: 40%; padding: 3px 0;">Situs base</td>
                    <td style="padding: 3px 0;">{situs_base}</td>
                </tr>
                <tr>
                    <td style="font-weight: 700; padding: 3px 0;">Owner base</td>
                    <td style="padding: 3px 0;">{owner_base}</td>
                </tr>
                <tr>
                    <td style="font-weight: 700; padding: 3px 0;">Mailing base</td>
                    <td style="padding: 3px 0;">{mail_base}</td>
                </tr>
            </table>
        </div>

        <div style="
            border-top: 1px solid #dddddd;
            padding-top: 8px;
            margin-top: 8px;
        ">
            <div style="
                font-weight: 700;
                font-size: 12px;
                margin-bottom: 5px;
                color: #24352f;
            ">
                Land Use
            </div>

            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <tr>
                    <td style="font-weight: 700; width: 40%; padding: 3px 0;">Assessed land use</td>
                    <td style="padding: 3px 0;">{class_desc}</td>
                </tr>
                <tr>
                    <td style="font-weight: 700; padding: 3px 0;">Living use indicated</td>
                    <td style="padding: 3px 0;">{live_at_yn}</td>
                </tr>
            </table>
        </div>

        <div style="
            border-top: 1px solid #dddddd;
            padding-top: 8px;
            margin-top: 8px;
            font-size: 10.5px;
            color: #666666;
            line-height: 1.35;
        ">
            This map is a screening tool. Shaded parcels should be reviewed before
            being treated as confirmed rental properties.
        </div>

    </div>
    """

    return html


# Add popup HTML to the parcels table.
parcels["POPUP_HTML"] = parcels.apply(make_popup, axis=1)


# ------------------------------------------------------------
# Map extent
# ------------------------------------------------------------
# I am using the village boundary to frame the map, not just the selected parcels.

minx, miny, maxx, maxy = boundary.total_bounds

center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2


# ------------------------------------------------------------
# Make the map
# ------------------------------------------------------------

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=16,
    tiles="CartoDB positron",
    control_scale=True,
)

m.fit_bounds([
    [miny, minx],
    [maxy, maxx],
])


# ------------------------------------------------------------
# Drawing styles
# ------------------------------------------------------------

def village_boundary_style(feature):
    # Boundary is mostly there to orient the analysis.
    return {
        "fillColor": "#ffffff",
        "color": "#2f3e38",
        "weight": 2.5,
        "fillOpacity": 0.02,
        "opacity": 0.75,
    }


def rental_parcel_style(feature):
    # These are the possible rental review parcels.
    return {
        "fillColor": "#8fb7a5",
        "color": "#3f4f49",
        "weight": 0.7,
        "fillOpacity": 0.45,
    }


def rental_parcel_highlight(feature):
    # Hover style only changes the parcel itself.
    # There is no hover label anymore.
    return {
        "fillColor": "#f4d35e",
        "color": "#111111",
        "weight": 2,
        "fillOpacity": 0.7,
    }


# ------------------------------------------------------------
# Add boundary first so it stays underneath the parcels
# ------------------------------------------------------------

folium.GeoJson(
    boundary,
    name="Elmwood Place village boundary",
    style_function=village_boundary_style,
).add_to(m)


# ------------------------------------------------------------
# Add the parcels
# ------------------------------------------------------------
# I am adding them one at a time because that gives me more control over
# the popup content and formatting.
#
# There is no tooltip on the parcels now. The review card only opens
# when someone clicks a parcel.

for index, row in parcels.iterrows():

    one_parcel = gpd.GeoSeries([row.geometry], crs=parcels.crs).__geo_interface__

    popup = folium.Popup(
        row["POPUP_HTML"],
        max_width=440
    )

    folium.GeoJson(
        one_parcel,
        style_function=rental_parcel_style,
        highlight_function=rental_parcel_highlight,
        popup=popup,
    ).add_to(m)


# ------------------------------------------------------------
# Title box
# ------------------------------------------------------------

if use_logo:
    logo_part = f"""
        <img src="{logo_url}" style="
            max-height: 36px;
            max-width: 110px;
            width: auto;
            display: block;
        ">
    """
else:
    logo_part = """
        <div style="
            font-size: 11px;
            letter-spacing: 0.04em;
            color: #5f6f68;
            font-weight: 700;
            white-space: nowrap;
        ">
            Space for Us
        </div>
    """


title_html = f"""
{{% macro html(this, kwargs) %}}
<div style="
    position: fixed;
    top: 16px;
    left: 50px;
    z-index: 9999;
    background-color: rgba(255, 255, 255, 0.95);
    padding: 14px 18px;
    border-radius: 8px;
    border: 1px solid #cccccc;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    font-family: Arial, sans-serif;
    max-width: 570px;
">

    <div style="
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 8px;
    ">

        <div style="min-width: 90px;">
            {logo_part}
        </div>

        <div style="
            font-size: 21px;
            font-weight: 700;
            color: #24352f;
            line-height: 1.15;
            white-space: nowrap;
        ">
            Elmwood Place Rental Review Map
        </div>

    </div>

    <div style="
        font-size: 13px;
        color: #444444;
        line-height: 1.4;
    ">
        A parcel-level review map using standardized address fields, land use classification,
        and address comparison results to identify properties that may require rental review.
    </div>

</div>
{{% endmacro %}}
"""

title = MacroElement()
title._template = Template(title_html)
m.get_root().add_child(title)


# ------------------------------------------------------------
# Legend
# ------------------------------------------------------------

legend_html = """
{% macro html(this, kwargs) %}
<div style="
    position: fixed;
    bottom: 28px;
    left: 50px;
    z-index: 9999;
    background-color: rgba(255, 255, 255, 0.95);
    padding: 12px 14px;
    border-radius: 8px;
    border: 1px solid #cccccc;
    box-shadow: 0 2px 8px rgba(0,0,0,0.16);
    font-family: Arial, sans-serif;
    font-size: 12px;
    color: #333333;
    max-width: 370px;
">
    <div style="font-weight: 700; margin-bottom: 8px;">Legend</div>

    <div style="
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    ">
        <span style="
            display: inline-block;
            width: 18px;
            height: 14px;
            background-color: rgba(143, 183, 165, 0.65);
            border: 1px solid #3f4f49;
        "></span>
        <span>Potential rental property to review</span>
    </div>

    <div style="
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    ">
        <span style="
            display: inline-block;
            width: 18px;
            height: 14px;
            background-color: rgba(255, 255, 255, 0.25);
            border: 2px solid #2f3e38;
        "></span>
        <span>Elmwood Place village boundary</span>
    </div>

    <div style="
        line-height: 1.4;
        color: #555555;
        border-top: 1px solid #dddddd;
        padding-top: 8px;
    ">
        Shaded parcels are screening results and should be treated as properties
        requiring review, not final rental determinations.
    </div>
</div>
{% endmacro %}
"""

legend = MacroElement()
legend._template = Template(legend_html)
m.get_root().add_child(legend)


# ------------------------------------------------------------
# No layer control on purpose
# ------------------------------------------------------------
# I do not want the public/user version of this map to have a layer toggle box.


# ------------------------------------------------------------
# Save the map
# ------------------------------------------------------------

m.save(out_map)

print("\nMap saved:")
print(out_map)