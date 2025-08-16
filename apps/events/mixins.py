class GroupedFormMixin:
    field_groups = []

    def get_field_groups(self):
        return [
            (group_title, [self[field_name] for field_name in field_list])
            for group_title, field_list in self.field_groups
        ]
