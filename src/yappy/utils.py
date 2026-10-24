def get_asset_url(type: str, path: str):
    if not path: return None

    return f"https://files.yapper.website/{type}s/{path}"

def serialize_value(item):
    d = None
    if isinstance(item, dict):
        d = serialize(item)
    elif isinstance(item, list):
        d = [serialize_value(i) for i in item]
    elif hasattr(item, "to_dict"):
        d = item.to_dict()
    else:
        d = item
    return d

def remove_unnecessary(json: dict):
    d = {}
    for key in json.keys():
        if json[key]:
            d[key]=json[key]
    return d

def serialize(json: dict):
    d = {}
    for key in json.keys():
        item = json[key]
        d[key] = serialize_value(item)
    return d
