# tLPF_mappings.py

import numpy as np
import chardet
from django.conf import settings

import logging
logger = logging.getLogger('validation')

def variant_conversion(x):
    x = str(x).strip()
    
    if not x:
        return []
    
    variants = []
    for variant in x.split(';'):
        variant = variant.strip()
        if variant:
            if '@' in variant:
                toponym, lang_script = variant.split('@', 1)
                variants.append({
                    'toponym': toponym.strip(),
                    'lang': lang_script.strip()
                })
            else:
                variants.append({
                    'toponym': variant
                })
    
    return variants

def safe_float_conversion(x):
    """Safely convert input to float, handling empty strings and None."""
    if x is None or str(x).strip() == "":
        return None
    try:
        return float(str(x).strip())
    except ValueError:
        return None

tLPF_mappings = {
    'id': {
        'lpf': '@id',
        'converter': lambda x: str(x).strip() or None
    },
    'title': {
        'lpf': 'names.0.toponym',
        'converter': lambda x: str(x).strip() or None
    },
    'title_source': {
        'lpf': 'names.0.citations.0.label',
        'converter': lambda x: str(x).strip() or None
    },
    'fclasses': {
        'lpf': 'properties.fclasses',
        'converter': lambda x: [item.strip() for item in str(x).split(';') if item.strip()] or None
    },
    'aat_types': {
        'lpf': 'types',
        'converter': lambda x: [{'identifier': f'aat:{item.strip()}'} for item in str(x).split(';') if item.strip()] or None
    },
    'attestation_year': {
        'lpf': 'names.0.citations.0.year',
        'converter': lambda x: str(x).strip() or None
    },
    'start': {
        'lpf': 'when.timespans.0.start.in',
        'converter': lambda x: str(x).strip() or None
    },
    'end': {
        'lpf': 'when.timespans.0.end.in',
        'converter': lambda x: str(x).strip() or None
    },
    'title_uri': {
        'lpf': 'names.0.citations.0.@id',
        'converter': lambda x: str(x).strip() or None
    },
    'ccodes': {
        'lpf': 'properties.ccodes',
        'converter': lambda x: [item.strip() for item in str(x).split(';') if item.strip()] or None
    },
    'matches': {
        'lpf': 'links',
        'converter': lambda x: [{'type': 'exactMatch', 'identifier': item.strip()} for item in str(x).split(';') if item.strip()] or None
    },
    'variants': {
        'lpf': 'additional_names',
        'converter': lambda x: variant_conversion(x)
    },
    'types': {
        'lpf': 'additional_types',
        'converter': lambda x: [{'label': item.strip()} for item in str(x).strip().split(';') if item.strip()] or None
    },
    'parent_name': {
        'lpf': 'relations.0',
        'converter': lambda x: {'relationType': 'gvp:broaderPartitive', 'label': str(x).strip()} if str(x).strip() else None
    },
    'parent_id': {
        'lpf': 'relations.0.relationTo',
        'converter': lambda x: str(x).strip() or None
    },
    'lon': {
        'lpf': 'geometry.coordinates.0',
        'converter': lambda x: safe_float_conversion(x)
    },
    'lat': {
        'lpf': 'geometry.coordinates.1',
        'converter': lambda x: safe_float_conversion(x)
    },
    'geowkt': {
        'lpf': 'geometry.geowkt',
        'converter': lambda x: str(x).strip() or None
    },
    'geo_source': {
        'lpf': 'geometry.citations.0.label',
        'converter': lambda x: str(x).strip() or None
    },
    'geo_id': {
        'lpf': 'geometry.citations.0.@id',
        'converter': lambda x: str(x).strip() or None
    },
    'description': {
        'lpf': 'descriptions.0.value',
        'converter': lambda x: str(x).strip() or None
    },
}
