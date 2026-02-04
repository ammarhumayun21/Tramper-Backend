"""
Custom parsers for handling nested form data.
"""

import re
from rest_framework.parsers import MultiPartParser, FormParser


def parse_nested_data(data):
    """
    Parse nested form data with bracket notation into proper Python dicts/lists.
    
    Converts:
        items[0][name] = "value"
        items[0][dimensions][height] = 10
    
    Into:
        {"items": [{"name": "value", "dimensions": {"height": 10}}]}
    """
    result = {}
    
    for key, value in data.items():
        # Check if key has bracket notation
        if '[' in key:
            parts = re.split(r'\[|\]', key)
            parts = [p for p in parts if p]  # Remove empty strings
            
            current = result
            for i, part in enumerate(parts[:-1]):
                next_part = parts[i + 1]
                
                # Determine if next level is list or dict
                is_next_list = next_part.isdigit()
                
                if part.isdigit():
                    part = int(part)
                    # Ensure list is long enough
                    while len(current) <= part:
                        current.append({})
                    if i == len(parts) - 2:
                        # Last key before value
                        next_key = parts[-1]
                        if next_key.isdigit():
                            next_key = int(next_key)
                            if not isinstance(current[part], list):
                                current[part] = []
                            while len(current[part]) <= next_key:
                                current[part].append(None)
                            current[part][next_key] = value
                        else:
                            if not isinstance(current[part], dict):
                                current[part] = {}
                            current[part][next_key] = value
                    else:
                        if is_next_list:
                            if not isinstance(current[part], list):
                                current[part] = []
                        else:
                            if not isinstance(current[part], dict):
                                current[part] = {}
                        current = current[part]
                else:
                    if part not in current:
                        current[part] = [] if is_next_list else {}
                    if i == len(parts) - 2:
                        # Last key before value
                        next_key = parts[-1]
                        if next_key.isdigit():
                            next_key = int(next_key)
                            if not isinstance(current[part], list):
                                current[part] = []
                            while len(current[part]) <= next_key:
                                current[part].append(None)
                            current[part][next_key] = value
                        else:
                            if not isinstance(current[part], dict):
                                current[part] = {}
                            current[part][next_key] = value
                    else:
                        current = current[part]
        else:
            result[key] = value
    
    return result


class NestedMultiPartParser(MultiPartParser):
    """
    MultiPartParser that handles nested bracket notation in form data.
    """
    
    def parse(self, stream, media_type=None, parser_context=None):
        result = super().parse(stream, media_type, parser_context)
        
        # Combine data and files
        data = result.data.copy()
        
        # Add files to data dict
        for key, value in result.files.items():
            data[key] = value
        
        # Parse nested structure
        parsed = parse_nested_data(data)
        
        # Convert back to QueryDict-like structure for DRF
        from django.http import QueryDict
        from rest_framework.request import Empty
        
        result.data = parsed
        
        return result


class NestedFormParser(FormParser):
    """
    FormParser that handles nested bracket notation in form data.
    """
    
    def parse(self, stream, media_type=None, parser_context=None):
        result = super().parse(stream, media_type, parser_context)
        
        data = result.data.copy() if hasattr(result.data, 'copy') else dict(result.data)
        parsed = parse_nested_data(data)
        result.data = parsed
        
        return result
