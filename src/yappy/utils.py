def get_asset_url(type: str, path: str):
    if not path: return None

    return f"https://files.yapper.website/{type}s/{path}"
