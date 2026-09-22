"""Classify an opinion against the shipped schema without inventing claims."""
import json
from pathlib import Path


def matches(value, schema):
    types = {"object": dict, "array": list, "string": str, "null": type(None)}
    expected = schema.get("type")
    if expected:
        names = expected if isinstance(expected, list) else [expected]
        if not any(isinstance(value, types[name]) for name in names):
            return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            return False
        if schema.get("additionalProperties") is False and value.keys() - properties.keys():
            return False
        return all(matches(item, properties[key]) for key, item in value.items() if key in properties)
    if isinstance(value, list) and "items" in schema:
        return all(matches(item, schema["items"]) for item in value)
    return True


def classify(text):
    schema = json.loads((Path(__file__).resolve().parent.parent / "consultation.schema.json").read_text())
    try:
        value = json.loads(text)
    except ValueError:
        return {"format": "unstructured", "content": text}
    if matches(value, schema):
        return {"format": "structured", "content": value}
    return {"format": "unstructured", "content": text}
