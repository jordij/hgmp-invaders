import pandas as pd
import requests
import yaml

from slugify import slugify

from constants import API_BASEURL, DATA_DIR, PLACES

# Load predefined API parameters
params = yaml.load(open("params.yaml"), yaml.SafeLoader)
api_params = params["api"]


def get_data(api_params={}):
    print("Querying API... page %d" % api_params["page"])
    r = requests.get(
        API_BASEURL,
        params=api_params,
        headers={"Content-Type": "application/json"},
    )
    if r.status_code != 200:
        raise Exception(
            "Yikes - iNaturalist API error: {}".format(r.status_code)
        )

    df = pd.read_json(r.content)

    if len(df.index) == api_params["per_page"]:  # more pages to fetch
        api_params["page"] += 1
        df = df.append(get_data(api_params))
    return df


# Need to query by place in order
# to know which obs belongs to which place
for key, val in PLACES.items():
    print("Fetching iNaturalist data from %s" % val)
    api_params["place_id"] = int(key)
    api_params["page"] = 1

    # Get Invasive spp first
    api_params["introduced"] = True
    df = get_data(api_params)
    # taxon column comes a nested dict
    # eg {'id': 60176, 'name': 'Atriplex prostrata', 'rank': 'species', 'ancestry': '48460/47126/211194/47125/47124/47366/52327/518889/518888/58112', 'common_name': {'id': 1076857, 'name': 'Creeping Saltbush', 'is_valid': True, 'lexicon': 'English'}}
    df2 = pd.concat(
        [df, df["taxon"].apply(pd.Series).add_prefix("taxon__")], axis=1
    )
    df3 = pd.concat(
        [
            df2,
            df2["taxon__common_name"]
            .apply(pd.Series)
            .add_prefix("taxon__common_name_"),
        ],
        axis=1,
    ).drop("taxon__common_name", axis=1)
    df_invasive = df3.assign(introduced=True).assign(place_id=int(key))
    print("%d observations from introduced spp in %s" % (len(df_invasive), val))

    # reset api params
    api_params = params["api"]
    api_params["page"] = 1
    api_params["place_id"] = int(key)
    # Get non-invasive spp now
    api_params["introduced"] = False
    df = get_data(api_params)
    # taxon column comes a nested dict
    # eg {'id': 60176, 'name': 'Atriplex prostrata', 'rank': 'species', 'ancestry': '48460/47126/211194/47125/47124/47366/52327/518889/518888/58112', 'common_name': {'id': 1076857, 'name': 'Creeping Saltbush', 'is_valid': True, 'lexicon': 'English'}}
    df2 = pd.concat(
        [df, df["taxon"].apply(pd.Series).add_prefix("taxon__")], axis=1
    )
    df3 = pd.concat(
        [
            df2,
            df2["taxon__common_name"]
            .apply(pd.Series)
            .add_prefix("taxon__common_name_"),
        ],
        axis=1,
    ).drop("taxon__common_name", axis=1)
    df_native = df3.assign(introduced=False).assign(place_id=int(key))
    print("%d observations from native spp in %s" % (len(df_native), val))

    df_final = pd.concat([df_invasive, df_native], ignore_index=True)
    print("%d Total observations from ALL spp in %s" % (len(df_final), val))

    # remove columns with non-pickable data (nested dicts etc)
    del df_final["iconic_taxon"]
    del df_final["user"]
    del df_final["photos"]
    del df_final["taxon"]

    df_final.to_hdf("%s/%s.h5" % (DATA_DIR, slugify(val)), key="df", mode="w")
