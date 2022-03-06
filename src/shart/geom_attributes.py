import copy


# exists for performance reasons
class MutableGeomAttributesManager:

    def __init__(self, existing_attributes=None):
        if existing_attributes is None:
            self.existing_attributes = dict()
        else:
            self.existing_attributes = existing_attributes

    def remove_geom_attributes(self, index):
        if index in self.existing_attributes:
            del self.existing_attributes[index]

    def move_geom_attributes(self, index_from, index_to):
        if index_to in self.existing_attributes:
            raise ValueError(f"Attempt to map index {index_from} to index {index_to}: {index_from} already has entries.")

        if index_from not in self.existing_attributes:
            return self # nothing to do

        self.existing_attributes[index_to] = self.existing_attributes[index_from]
        del self.existing_attributes[index_from]

    def add_attribute(self, index, key, value):
        attribute_dict = self.existing_attributes.setdefault(index, dict())
        attribute_dict[key] = value

    def add_attributes(self, index, attributes):
        self.existing_attributes.setdefault(index, dict()).update(attributes)

    def to_immutable(self):
        return GeomAttributesManager(self.existing_attributes)

    @staticmethod
    def copy(other):
        return MutableGeomAttributesManager({k: v for k, v in other.attributes})


class GeomAttributesManager:

    # Note: class should be immutable
    def __init__(self, existing_attributes=None):
        if existing_attributes is None:
            self._attributes = dict()
        else:
            self._attributes = copy.deepcopy(existing_attributes)

    @property
    def attributes(self):
        for k, v in self._attributes.items():
            yield k, copy.deepcopy(v)

    def union(self, other):
        result_attributes = copy.deepcopy(self._attributes)
        for k, v in other.attributes:
            if k in result_attributes:
                raise ValueError("Attribute key collision")

            result_attributes[k] = copy.deepcopy(v)

        return GeomAttributesManager(result_attributes)

    def offset_keys(self, offset):
        result_attributes = dict()
        for k, v in self._attributes.items():
            result_attributes[k + offset] = copy.deepcopy(v)

        return GeomAttributesManager(result_attributes)

    # extracts the supplied index and converts it to a zero indexed attribute
    def extract_index(self, geom_index):
        return GeomAttributesManager(
            existing_attributes={0: self.get_geom_attributes(geom_index)}
        )

    def add_geom_attribute(self, geom_index, key, value):
        new_attributes = copy.deepcopy(self._attributes)
        if geom_index not in new_attributes:
            new_attributes[geom_index] = dict()

        new_attributes[geom_index][key] = value

        return GeomAttributesManager(new_attributes)

    def move_geom_attributes(self, index_from, index_to):
        if index_from not in self._attributes:
            return self # nothing to do

        new_attributes = copy.deepcopy(self._attributes)

        if index_to in new_attributes:
            raise ValueError("Index already has attributes.")

        new_attributes[index_to] = copy.deepcopy(new_attributes[index_from])
        del new_attributes[index_from]

        return GeomAttributesManager(new_attributes)

    def get_geom_attributes(self, geom_index):
        return self._attributes.get(geom_index, dict())
