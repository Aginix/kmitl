def get_value(model, field, lang=None, value_type=None):
    if model:
        data = model[field]
        if lang:
            data = model.with_context(lang=lang)[field]

        if value_type is bool:
            return data

        if not data:
            return None
        elif value_type is int:
            return int(data)
        elif value_type is float:
            return float(data)
        else:
            return data
    return None
