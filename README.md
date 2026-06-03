# Elmwood Place rental property review

This repository documents a rental property review method for Elmwood Place, Ohio, using public parcel data from Hamilton County.

The purpose of this project is to identify parcels that may need rental property review based on land use and address information. The method does not prove that a property is rented. It creates a review flag using the information available in the parcel dataset.

Parcel data was the starting point because it is one of the few public datasets that can connect land, ownership, mailing information, assessed land use, and tax information at the property level. But parcel data is administrative data. It was not created specifically to answer the question, “Is this property a rental?”

That means the data had to be interpreted carefully before it could be used.

## Why the parcel data needed review

The parcel table included useful information, but not in a form that could be used directly for rental review.

Some of the challenges were practical:

- Land use was stored as numeric class codes instead of readable descriptions
- Property, owner, and mailing addresses were split across different fields
- Some address fields included only the street address
- Other address fields could include city, state, ZIP code, unit numbers, suite numbers, or administrative text
- The same address could appear in slightly different formats
- Some records were blank, incomplete, or ambiguous
- Not every parcel with a different mailing address is a rental
- Not every rental property can be identified from parcel data alone

A simple address mismatch would have overflagged properties. For example, a nonresidential parcel, public parcel, church, parking lot, warehouse, railroad parcel, or vacant industrial lot could have an owner or mailing address that differs from the property address. That does not make it a residential rental.

The review method had to narrow the dataset first, then compare addresses in a more careful way.

## Main question

The project asks:

```text
Which parcels in Elmwood Place appear to be possible rental properties based on assessed land use and address mismatch patterns?
```

The answer is a review layer, not a final rental registry.

## Method summary

The method has three main parts:

1. Translate land use class codes into readable descriptions
2. Identify parcels where the assessed land use suggests people may live there
3. Compare street-level property, owner, and mailing addresses to flag possible rental review records

The script used for this work creates working fields, standardizes address fields, compares address values, assigns possible rental flags, writes review notes, and summarizes delinquent taxes.

## Input parcel layer

The script was written for an ArcGIS Pro layer or feature class named:

```python
fc = "Elmwood_Jurisdiction_Clip2"
```

This can be changed in the script if the layer name or path changes.

## Source fields used

The method uses existing parcel fields from the Hamilton County parcel data.

### Land use class

```text
CLASS
```

This is the numeric land use class field. The script translates this field into a readable description.

### Situs or property address

```text
ADDRNO
ADDRST
ADDRSF
```

These fields are used to build the property address, also called the situs address.

### Owner address

```text
OWNAD1
OWNAD1A
OWNAD2
```

The script defines these fields, but only `OWNAD1` and `OWNAD1A` are used for street-level address comparison.

`OWNAD2` is not used in the comparison because it usually contains city, state, and ZIP code information.

### Mailing address

```text
MLADR1
MLADR1A
MLADR2
```

The script defines these fields, but only `MLADR1` and `MLADR1A` are used for street-level address comparison.

`MLADR2` is not used in the comparison because it usually contains city, state, and ZIP code information.

### Delinquent taxes

```text
DELQ_TAXES
```

This field is summarized for all parcels and for possible rental review parcels.

## Fields created by the method

The script creates or updates the following working fields:

```text
CLASS_DESC
LIVE_AT_YN
SITUS_STD
OWNER_ST_STD
MAIL_ST_STD
SITUS_BASE
OWNER_BASE
MAIL_BASE
ADDR_MATCH
POSS_RENT_YN
ADDR_NOTE
```

These fields make the parcel table easier to review, filter, map, and explain.

## Step 1: Translate land use class codes

The original parcel data uses a numeric `CLASS` field. The method translates those numeric values into readable land use descriptions using Hamilton County Auditor land use class documentation.

The translated value is written to:

```text
CLASS_DESC
```

Examples include:

```text
RESIDENTIAL - SINGLE FAMILY
RESIDENTIAL - TWO FAMILY DWELLINGS
RESIDENTIAL - THREE FAMILY DWELLINGS
RESIDENTIAL - OTHER STRUCTURES
RESIDENTIAL - VACANT LAND
COMMERCIAL - APARTMENTS, 4 TO 19 UNITS
COMMERCIAL - RETAIL WITH APARTMENTS OVER
COMMERCIAL - OFFICE WITH APARTMENTS OVER
INDUSTRIAL - WAREHOUSE
PUBLICLY OWNED - MUNICIPALITIES
```

These descriptions are assessment land use classes. They are not zoning categories.

This step matters because the rental review should not be based on numeric codes that are hard to interpret. The review needed plain-language land use descriptions that could be checked, mapped, and explained.

## Step 2: Identify parcels where people may live

After translating the land use codes, the method creates a living-use field:

```text
LIVE_AT_YN
```

This field identifies whether the parcel’s assessed land use suggests that people may live at the parcel.

The following classes were included in the living-use screen:

```text
COMMERCIAL - APARTMENTS, 4 TO 19 UNITS
COMMERCIAL - OFFICE WITH APARTMENTS OVER
COMMERCIAL - RETAIL WITH APARTMENTS OVER
RESIDENTIAL - OTHER STRUCTURES
RESIDENTIAL - SINGLE FAMILY
RESIDENTIAL - THREE FAMILY DWELLINGS
RESIDENTIAL - TWO FAMILY DWELLINGS
RESIDENTIAL - VACANT LAND
```

These parcels are marked:

```text
Y
```

Clearly nonresidential classes are marked:

```text
N
```

Missing, blank, or unmapped class values are treated as review cases instead of being forced into a yes/no category.

This step keeps the rental review focused on parcels with residential or living-use relevance. It reduces false flags from commercial, industrial, public, institutional, utility, railroad, parking, and other nonresidential parcels.

## Step 3: Build comparable address fields

The parcel dataset stores address information in pieces. The method builds standardized address fields so that the comparison is more consistent.

The script creates:

```text
SITUS_STD
OWNER_ST_STD
MAIL_ST_STD
```

The standardized fields clean the address text by:

- converting text to uppercase
- removing punctuation that can create false mismatches
- replacing direction words such as `NORTH` with `N`
- replacing street suffixes such as `STREET` with `ST`
- replacing unit and administrative words such as `SUITE` with `STE`

This does not make the address data perfect. It makes the records consistent enough for a first-pass review.

## Step 4: Compare street-level addresses only

The method intentionally compares street-level address components, not full address blocks.

This is important because the situs address and mailing address are not built the same way in the parcel data. A property address may include only a street address, while an owner or mailing address may include city, state, and ZIP code. Comparing those full strings can make matching addresses appear different.

For that reason, the method compares:

### Situs address

```text
ADDRNO + ADDRST + ADDRSF
```

### Owner street address

```text
OWNAD1 + OWNAD1A
```

### Mailing street address

```text
MLADR1 + MLADR1A
```

It does not compare `OWNAD2` or `MLADR2`.

This choice reduces false mismatches caused by city, state, ZIP code, or full mailing block differences.

## Step 5: Remove unit and administrative text for base comparison

After standardizing the address fields, the method creates base address fields:

```text
SITUS_BASE
OWNER_BASE
MAIL_BASE
```

These fields remove unit, suite, apartment, floor, building, department, and attention text before comparison.

For example:

```text
311 ELM ST STE 270
```

becomes:

```text
311 ELM ST
```

This makes the comparison focus on the street-level address.

The goal is not to erase useful detail from the parcel record. The goal is to avoid treating a unit number, suite number, or administrative mailing line as evidence that two addresses are different.

## Step 6: Classify the address match

The script writes the address comparison result to:

```text
ADDR_MATCH
```

Possible values include:

```text
OWNER_AND_MAIL_MATCH_SITUS
OWNER_AND_MAIL_DIFFER_FROM_SITUS
OWNER_DIFFERS_FROM_SITUS
MAIL_DIFFERS_FROM_SITUS
OWNER_DIFFERS_FROM_SITUS_NO_MAIL
MAIL_DIFFERS_FROM_SITUS_NO_OWNER
OWNER_MATCHES_SITUS_NO_MAIL
MAIL_MATCHES_SITUS_NO_OWNER
NO_COMPARABLE_ADDRESS
NO_SITUS_ADDRESS
REVIEW
```

This field shows why a parcel was or was not flagged. It also makes the review easier to check later, because the address condition is visible in the table.

## Step 7: Determine possible rental review status

The possible rental review flag is written to:

```text
POSS_RENT_YN
```

A parcel is marked:

```text
Y
```

when both conditions are true:

```text
LIVE_AT_YN = Y
```

and

```text
the owner or mailing street-level address differs from the situs address
```

A parcel is marked:

```text
N
```

when it does not meet that logic.

In plain language, the method flags a parcel for possible rental review when the parcel appears to be a place where people may live and the owner or mailing address does not match the property address.

This is a screening method. It is not a legal determination, a rental license record, or proof of tenancy.

## Step 8: Add review notes

The script writes a short explanation to:

```text
ADDR_NOTE
```

Examples include:

```text
Owner and mailing addresses differ from situs
Owner address differs from situs
Mailing address differs from situs
Owner and mailing addresses match situs
Missing situs address
No owner or mailing address to compare
Owner unit/suite/admin text removed
```

This field helps with manual review, map popups, filtering, and checking the logic parcel by parcel.

## Step 9: Summarize delinquent taxes

The script also summarizes:

```text
DELQ_TAXES
```

It calculates delinquent tax totals for:

```text
all parcel records
possible rental review records only
```

For each group, the script reports:

```text
total delinquent taxes
records included
null or blank values skipped
non-numeric values skipped
```

This does not change the tax data. It gives a quick summary of how delinquent taxes appear in the full parcel layer and within the possible rental review group.

## How to read the output

The final output is an updated parcel layer with working fields that can be reviewed in ArcGIS Pro, symbolized on a map, filtered, exported, or used in popups.

The most important review fields are:

```text
CLASS_DESC
LIVE_AT_YN
ADDR_MATCH
POSS_RENT_YN
ADDR_NOTE
DELQ_TAXES
```

Together, these fields explain:

- what kind of parcel it appears to be
- whether people may live there
- whether the owner or mailing address differs from the property address
- whether the parcel was flagged for possible rental review
- what address condition produced the flag
- whether delinquent taxes are attached to the record

## Limitations

This method depends on public parcel data, and parcel data has limits.

A different owner or mailing address can be a useful signal, but it does not always mean a property is rented. A property owner may use a different mailing address for tax bills, family reasons, estate issues, business records, property management, or ordinary administrative convenience.

Some rental properties may not be identified by this method. If the owner receives mail at the property address, the parcel may not be flagged. If the parcel data is outdated, incomplete, or formatted unexpectedly, the review flag may miss something or mark something that needs correction.

The land use classification also has limits. Assessment classes are not the same as zoning, occupancy, licensing, or current use. A parcel’s class may suggest residential relevance, but it does not confirm who lives there, whether the property is occupied, or whether it is rented.

For those reasons, `POSS_RENT_YN` should be read as a review flag. It points to parcels worth checking. It should be paired with local knowledge, additional records, field review, rental registration data if available, code enforcement records, tax records, or follow-up research.

