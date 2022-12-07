platform_to_routing_dict = {
    'br1': 'americas',
    'eun1': 'europe',
    'euw1': 'europe',
    'jp1': 'asia',
    'kr': 'asia',
    'la1': 'americas',
    'la2': 'americas',
    'na1': 'americas',
    'oc1': 'asia',
    'ru': 'europe',
    'tr1': 'europe'
}

region_to_platform_dict = {
    'br': 'br1',
    'eun': 'eun1',
    'euw': 'euw1',
    'jp': 'jp1',
    'kr': 'kr',
    'lan': 'la1',
    'las': 'la2',
    'na': 'na1',
    'oc': 'oc1',
    'ru': 'ru',
    'tr': 'tr1'
}

platform_to_region_dict = {
    v: k
    for k, v in region_to_platform_dict.items()
}


def region_to_platform(region: str):
    """Converter for the flag"""
    return region_to_platform_dict[region.lower()]


def platform_to_region(platform: str):
    return platform_to_region_dict[platform.lower()]
