# backend/utils/helpers.py
import re
from datetime import datetime
from neo4j.time import DateTime as Neo4jDateTime

def clean_text(text: str) -> str:
    """Basic text cleaning."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_hashtags(text: str) -> list[str]:
    """Extracts hashtags from text."""
    if not isinstance(text, str):
        return []
    return re.findall(r'#(\w+)', text)

def extract_mentions(text: str) -> list[str]:
    """Extracts mentions from text."""
    if not isinstance(text, str):
       return []
    return re.findall(r'@(\w+)', text)

def format_timestamp(timestamp_str: str) -> str:
    """Attempts to normalize various timestamp formats to ISO 8601."""
    if not isinstance(timestamp_str, str):
        return None
    try:
        if 'T' in timestamp_str and 'Z' in timestamp_str:
            return timestamp_str
        if '-' in timestamp_str and ':' in timestamp_str:
            dt_obj = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            return dt_obj.isoformat() + 'Z'
        return timestamp_str
    except ValueError:
        return timestamp_str

# THIS IS THE NEW, RECURSIVE FUNCTION THAT WILL FIX THE ERROR
def serialize_neo4j_value(value):
    """
    Recursively converts Neo4j temporal types to JSON-serializable formats.
    This is the definitive fix for the 'DateTime not JSON serializable' error.
    It handles values that are dictionaries or lists containing DateTime objects.
    """
    if isinstance(value, (Neo4jDateTime, datetime)):
        return value.isoformat() if value else None
    elif isinstance(value, dict):
        # If the value is a dictionary, recursively process each of its values
        return {k: serialize_neo4j_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        # If the value is a list, recursively process each of its items
        return [serialize_neo4j_value(v) for v in value]
    # You could add other Neo4j types here if needed (e.g., Point)
    else:
        # Return the value as is if it's already a serializable type
        return value