import json
import os

DEFAULT_PRIVATE_MAVEN_GROUP_ID_PREFIXES = ['com.']


def get_private_maven_group_id_prefixes():
    """Return Maven group-ID prefixes that identify private/commercial artifacts.

    Read from the PRIVATE_MAVEN_GROUP_ID_PREFIXES env var (JSON array, e.g. '["com.sonarsource."]').
    Defaults to '["com."]' when unset. An empty list ('[]') means no group is treated as private.
    Non-list JSON values fall back to the default.
    """
    raw = os.environ.get('PRIVATE_MAVEN_GROUP_ID_PREFIXES', '["com."]')
    try:
        prefixes = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return list(DEFAULT_PRIVATE_MAVEN_GROUP_ID_PREFIXES)
    if not isinstance(prefixes, list):
        return list(DEFAULT_PRIVATE_MAVEN_GROUP_ID_PREFIXES)
    return prefixes


def is_private_maven_group_id(gid: str) -> bool:
    return any(gid.startswith(p) for p in get_private_maven_group_id_prefixes())
