import folium
import pandas as pd
from folium.plugins import HeatMap
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from slugify import slugify

from constants import DATA_DIR, PLOT_DIR, PLACES

TICKS_FONT_SIZE = 16
LEGEND_FONT_SIZE = 20
AXES_FONT_SIZE = 24
TITLE_SIZE = 26

sns.set_color_codes("pastel")

plt.rc("font", size=AXES_FONT_SIZE)  # controls default text size
plt.rc("axes", titlesize=TITLE_SIZE)  # fontsize of the title
plt.rc("axes", labelsize=AXES_FONT_SIZE)  # fontsize of the x and y labels
plt.rc("xtick", labelsize=TICKS_FONT_SIZE)  # fontsize of the x tick labels
plt.rc("ytick", labelsize=TICKS_FONT_SIZE)  # fontsize of the y tick labels
plt.rc("legend", fontsize=LEGEND_FONT_SIZE)  # fontsize of the legend

TOP_SSP = 5

INT_PLACES = {}
for key, value in PLACES.items():
    INT_PLACES[int(key)] = value

df_list = []
# build a single dataframe with data from all locations
for key, val in PLACES.items():
    df = pd.read_hdf("%s/%s.h5" % (DATA_DIR, slugify(val)), key="df")
    df_list.append(df)

df_total = pd.concat(df_list, ignore_index=True)

# dataframes with just a few columns
df_sub = df_total[["id", "introduced", "place_id"]]
df_ssp = df_total[["id", "introduced", "place_id", "taxon__common_name_name"]]

# replace column values with more readable ones

df_ssp = df_ssp.replace(
    {"introduced": {True: "Introduced", False: "Native"}}
).replace({"place_id": INT_PLACES})
df_ssp = df_ssp.rename(
    columns={
        "introduced": "Introduced",
        "place_id": "Location",
        "taxon__common_name_name": "Species",
    }
)

# replace column values with more readable ones
df_sub = df_sub.replace(
    {"introduced": {True: "Introduced", False: "Native"}}
).replace({"place_id": INT_PLACES})
# calculate aggregate (total obs per place)
df_aggr = df_sub.groupby("place_id").agg("count").reset_index()
df_aggr = df_aggr[["id", "place_id"]]

df_grouped = df_sub.groupby(["place_id", "introduced"]).count()

df_percentages = pd.merge(
    df_grouped.reset_index().rename_axis(None, axis=1), df_aggr, on="place_id"
)
df_percentages = df_percentages.rename(
    columns={"id_x": "count", "id_y": "total"}
)
df_percentages["percentage"] = df_percentages.apply(
    lambda row: row["count"] / row["total"] * 100, axis=1
)

# PLOT SPP RICHNESS BY LOCATION

df_ssp_i = df_ssp[df_ssp["Introduced"] == "Introduced"]
df_ssp_n = df_ssp[df_ssp["Introduced"] == "Native"]
df = pd.DataFrame()
for key, val in PLACES.items():
    c = len(df_ssp_i[df_ssp_i["Location"] == val].Species.unique())
    df = df.append(
        {"Location": val, "Species": c, "Introduced": "Introduced"},
        ignore_index=True,
    )
    c = len(df_ssp_n[df_ssp_n["Location"] == val].Species.unique())
    df = df.append(
        {"Location": val, "Species": c, "Introduced": "Native"},
        ignore_index=True,
    )

f, ax = plt.subplots(figsize=(15, 8))

sns.barplot(x="Location", y="Species", hue="Introduced", data=df)
ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
ax.set_xlabel("")
# remove legend title (label)
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles=handles, labels=labels)

f.tight_layout()
f.savefig("%s/%s.png" % (PLOT_DIR, "richness_by_place"), dpi=300)
# END  PLOT SPP RICHNESS BY LOCATION


# PLOT STACK BAR TOTAL VALUES
df_to_plot = (
    df_grouped.reset_index()
    .pivot_table(index="introduced", columns="place_id", values="id")
    .T
)
f, ax = plt.subplots(figsize=(15, 8))
df_to_plot.sort_values("Native", ascending=False).plot(
    kind="bar", stacked=True, ax=ax
)

ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
ax.set_ylabel("# Observations")
ax.set_xlabel("")
legend = ax.figure.gca().get_legend()
legend.set_title("")

ax.figure.tight_layout()
ax.figure.savefig("%s/%s.png" % (PLOT_DIR, "stack_by_count"), dpi=300)
# END PLOT STACK BAR TOTAL VALUES


# PLOT STACK BAR PERCENTAGES
f, ax = plt.subplots(figsize=(15, 8))

df_to_plot = (
    df_percentages.sort_values("total", ascending=False)
    .reset_index()
    .pivot_table(index="introduced", columns="place_id", values="percentage")
    .T
)
df_to_plot.plot(kind="bar", stacked=True, ax=ax)

ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
ax.set_ylabel("Percentage")
ax.set_xlabel("")

legend = ax.figure.gca().get_legend()
legend.set_title("")

ax.figure.tight_layout()
ax.figure.savefig("%s/%s.png" % (PLOT_DIR, "stack_by_perc"), dpi=300)
# END PLOT STACK BAR PERCENTAGES


# PLOT TOTAL SPP BARPLOTS
df_total_ssp_by_location = (
    df_ssp.groupby(["Species", "Introduced", "Location"])["id"]
    .count()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

df_total_ssp = (
    df_ssp.groupby(["Species", "Introduced"])["id"]
    .count()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

df_total_ssp_inv = df_total_ssp[df_total_ssp["Introduced"] == "Introduced"]
df_total_ssp_nat = df_total_ssp[df_total_ssp["Introduced"] == "Native"]

df_top_ssp_inv = df_total_ssp_inv[:TOP_SSP].copy()
other_row = pd.DataFrame(
    data={
        "Species": ["Others"],
        "Introduced": ["Introduced"],
        "count": [df_total_ssp_inv["count"][TOP_SSP:].sum()],
    }
)
df_to_plot = pd.concat([df_top_ssp_inv, other_row])

f, ax = plt.subplots(figsize=(15, 8))

ax = sns.barplot(
    x="count",
    y="Species",
    data=df_to_plot,
    label="Count",
    color="b",
)

ax.set_title("Introduced Species Observations")
ax.set_xlabel("# Observations")
ax.set_ylabel("")
f.tight_layout()
f.savefig(fname="%s/%s.png" % (PLOT_DIR, "bar_top_introduced"), dpi=300)

df_top_nat_inv = df_total_ssp_nat[:TOP_SSP].copy()
other_row = pd.DataFrame(
    data={
        "Species": ["Others"],
        "Introduced": ["Introduced"],
        "count": [df_total_ssp_nat["count"][TOP_SSP:].sum()],
    }
)
df_to_plot = pd.concat([df_top_nat_inv, other_row])

f, ax = plt.subplots(figsize=(15, 8))
sns.barplot(
    x="count",
    y="Species",
    data=df_to_plot,
    label="Count",
    color="b",
)
ax.set_xlabel("# Observations")
ax.set_title("Native Species Observations")
ax.set_ylabel("")
f.tight_layout()
f.savefig(fname="%s/%s.png" % (PLOT_DIR, "bar_top_native"), dpi=300)

# END PLOT TOTAL SPP BARPLOTS


# PRINT BASIC STATS

df_ssp["Location"].value_counts()

for key, value in PLACES.items():
    print(value)
    print(df_ssp[df_ssp["Location"] == val]["Introduced"].value_counts())


# PLOT TIME SERIES BAR BY YEAR
f, ax = plt.subplots(figsize=(15, 8))

df_total["Timestamp"] = pd.to_datetime(df_total["observed_on"])
df_by_year = df_total.sort_values("Timestamp").set_index("Timestamp")
df_by_year["Counts"] = np.zeros(len(df_by_year))

# Get introduced df
df_int = df_by_year[df_by_year["introduced"] == True]
df_int = df_int.resample("Y").count()
df_int = df_int[df_int.index > "1999-12-31"]
df_int["type"] = "Introduced"
# Get native df
df_nat = df_by_year[df_by_year["introduced"] == False]
df_nat = df_nat.resample("Y").count()
df_nat = df_nat[df_nat.index > "1999-12-31"]
df_nat["type"] = "Native"

dff = pd.concat([df_nat[["Counts", "type"]], df_int[["Counts", "type"]]])
# plot
sns.barplot(x=dff.index, y="Counts", hue="type", data=dff)


x_dates = dff.index.strftime("%Y").sort_values().unique()
ax.set_xticklabels(labels=x_dates, rotation=45, ha="right")
ax.set_ylabel("# Observations")
ax.set_xlabel("Year")
# remove legend title (label)
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles=handles, labels=labels)

f.savefig(fname="%s/%s.png" % (PLOT_DIR, "obs_by_year_multi"), dpi=300)
# END PLOT TIME SERIES BAR BY YEAR


# PLOT TOTAL REGRESSION

f, ax = plt.subplots(figsize=(15, 8))

dfreg = df_by_year.resample("Y").count()
dfreg = dfreg[dfreg.index > "1999-12-31"]
dfreg["year"] = dfreg.index.strftime("%y").astype("int64")
dfreg["Year"] = dfreg.index.strftime("%Y")
dfregnoi = dfreg.reset_index()
sns.regplot(x="year", y="Counts", data=dfregnoi, ax=ax)

x_dates = dfreg["Year"].sort_values().unique()
ax.set_xticks(dfreg["year"].sort_values().unique())
ax.set_xticklabels(labels=x_dates, rotation=45, ha="right")
ax.set_ylabel("# Observations")
ax.set_xlabel("Year")

f.savefig(fname="%s/%s.png" % (PLOT_DIR, "obs_by_year_regplot"), dpi=300)
# END PLOT TOTAL REGRESSION


# PLOT SEASONAL TIME SERIES BAR BY MONTH AND TYPE
f, ax = plt.subplots(figsize=(15, 8))

# Get introduced df
df_int = df_by_year[df_by_year["introduced"] == True]
df_int = df_int.resample("M").count()
# df_int = df_int[df_int.index > "1999-12-31"]
df_int["type"] = "Introduced"
# Get native df
df_nat = df_by_year[df_by_year["introduced"] == False]
df_nat = df_nat.resample("M").count()
# df_nat = df_nat[df_nat.index > "1999-12-31"]
df_nat["type"] = "Native"
# Concat dfs
dff = pd.concat([df_nat[["Counts", "type"]], df_int[["Counts", "type"]]])

dff["Month"] = dff.index.strftime("%m")
dff["month"] = dff.index.strftime("%b")
dff = dff.sort_values(["Month"], ascending=True)

dftp = dff.groupby(["Month", "type"]).agg(
    counts=pd.NamedAgg(column="Counts", aggfunc=sum)
)
df = dftp.reset_index()

# plot
sns.barplot(x="Month", y="counts", hue="type", data=df)

x_dates = dff.month.unique()
ax.set_xticklabels(labels=x_dates, rotation=45, ha="right")
ax.set_ylabel("# Observations")
ax.set_xlabel("Month")
# remove legend title (label)
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles=handles, labels=labels)
f.savefig(fname="%s/%s.png" % (PLOT_DIR, "obs_by_month"), dpi=300)
# PLOT SEASONAL TIME SERIES BAR BY MONTH AND TYPE


# BUILD MAP

basemap = folium.Map(
        location=[-36.667802, 174.908157],
        zoom_start=12,
        control_scale=True,
        zoom_control=True,
        )
obs_coords = list(zip(df_total['latitude'], df_total['longitude']))
heatmap = HeatMap(obs_coords, min_opacity=0.2, radius=25)
fg_hm = folium.FeatureGroup(name='Observations', show=False)
basemap.add_child(fg_hm)
heatmap.add_to(fg_hm)
folium.LayerControl().add_to(basemap)
folium.LayerControl().add_to(heatmap)

basemap.save("%s/%s.html" % (PLOT_DIR, "map"))

# END BUILD MAP