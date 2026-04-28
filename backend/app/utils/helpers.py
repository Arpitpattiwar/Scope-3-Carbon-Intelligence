def region_value(region) -> str:
    """
    Safely extract the string value from a Region enum or plain string.
    Handles: Region.north → "north", "north" → "north", "Region.north" → "north"
    """
    if hasattr(region, "value"):
        return region.value
    s = str(region)
    return s.split(".")[-1] if "." in s else s
