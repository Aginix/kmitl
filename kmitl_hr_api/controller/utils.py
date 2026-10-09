def get_data(obj, attr, data_type=None):
    list_attr = attr.split(".")
    tmp_obj = obj
    for index, value in enumerate(list_attr):
        if index == len(list_attr) - 1:
            if data_type == "boolean":
                return getattr(tmp_obj, value)
            if getattr(tmp_obj, value) is False:
                return None
            return getattr(tmp_obj, value)
        tmp_obj = getattr(tmp_obj, value)
