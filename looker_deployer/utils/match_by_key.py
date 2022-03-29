def match_by_key(tuple_to_search, dictionary_to_match, key_to_match_on):
    matched = None

    for item in tuple_to_search:
        if getattr(item, key_to_match_on) == getattr(dictionary_to_match, key_to_match_on):
            matched = item
            break

    return matched
