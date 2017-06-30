import sys

from fnmatch import fnmatchcase
from itertools import starmap
from collections import Mapping, Sequence, MutableMapping, MutableSequence


__author__ = "Lars van Gemerden"

if sys.version_info[0] < 3:
    value_sequence_types = (basestring, bytearray, bytes, buffer)
else:
    value_sequence_types = (str, bytearray, bytes)


_marker = object()


class BasePath(list):
    """
    Helper classes to be able to use '.' separated paths to access elements in objects, lists and dictionaries.
    """
    sep = "."

    @classmethod
    def items(cls, obj, all=False, _path=None):
        """ iterates over all (wildpath, value) items in the (nested) object """
        if _path is None:
            _path = cls()
        elif all:
            yield _path, obj
        if isinstance(obj, value_sequence_types):
            if not all:
                yield _path, obj
        elif isinstance(obj, Mapping):
            for key, sub_obj in obj.items():
                for sub_path, sub_obj in cls.items(sub_obj, all, _path + cls(key)):
                    yield sub_path, sub_obj
        elif isinstance(obj, Sequence):
            for index, sub_obj in enumerate(obj):
                for sub_path, sub_obj in cls.items(sub_obj, all, _path + cls(str(index))):
                    yield sub_path, sub_obj
        elif hasattr(obj, "__dict__"):
            for key, sub_obj in obj.__dict__.items():
                for sub_path, sub_obj in cls.items(sub_obj, all, _path + cls(key)):
                    yield sub_path, sub_obj
        elif not all:
            yield _path, obj

    @classmethod
    def paths(cls, obj, all=False):
        for sub_path, _ in cls.items(obj, all=all):
            yield sub_path

    @classmethod
    def values(cls, obj, all=False):
        for _, sub_obj in cls.items(obj, all=all):
            yield sub_obj

    def __init__(self, string_or_seq=None):
        string_or_seq = string_or_seq or ()
        if isinstance(string_or_seq, str):
            list.__init__(self, string_or_seq.split(self.sep))
        else:
            list.__init__(self, string_or_seq)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.__class__(list.__getitem__(self, key))
        return list.__getitem__(self, key)

    def __getslice__(self, i, j):
        return self.__getitem__(slice(i, j))

    def get_in(self, obj, default=_marker):
        try:
            return self._get_in(obj)
        except (IndexError, KeyError, AttributeError):
            if default is _marker:
                raise
            return default

    def _get_in(self, obj):
        raise NotImplementedError

    def set_in(self, obj, value):
        raise NotImplementedError

    def del_in(self, obj):
        raise NotImplementedError

    def pop_in(self, obj):
        result = self._get_in(obj)
        self.del_in(obj)
        return result

    def has_in(self, obj):
        """checks presence of item at wildpath 'self' from the 'obj'"""
        try:
            self._get_in(obj)
        except (KeyError, IndexError, AttributeError):
            return False
        return True

    def __add__(self, other):
        return self.__class__(list.__add__(self, other))

    def __str__(self):
        return self.sep.join(str(v) for v in self)


class Path(BasePath):
    """
    Fast implementation of the baseclass that does not allow wildcards and slicing.
    """

    def _get_in(self, obj):
        """returns item at wildpath 'self' from the 'obj'"""
        for key in self:
            if isinstance(obj, Mapping):
                obj = obj[key]
            elif isinstance(obj, Sequence):
                obj = obj[int(key)]
            else:
                obj = getattr(obj, key)
        return obj

    def set_in(self, obj, value):
        """sets item at wildpath 'self' from the 'obj' to 'value'"""
        obj = self[:-1]._get_in(obj)
        if isinstance(obj, MutableMapping):
            obj[self[-1]] = value
        elif isinstance(obj, MutableSequence):
            obj[int(self[-1])] = value
        else:
            setattr(obj, self[-1], value)

    def del_in(self, obj):
        """deletes item at wildpath 'self' from the 'obj'"""
        obj = self[:-1]._get_in(obj)
        if isinstance(obj, MutableMapping):
            del obj[self[-1]]
        elif isinstance(obj, MutableSequence):
            del obj[int(self[-1])]
        else:
            delattr(obj, self[-1])


def parse_slice(key, parse_item=lambda v: int(v) if v else None):
    return slice(*map(parse_item, key.split(':')))


def parse_slice_star(key, parse_item=lambda v: int(v) if v else None):
    if key == "*":
        return slice(None)
    try:
        return slice(*map(parse_item, key.split(':')))
    except (ValueError, TypeError) as e:
        raise IndexError("sequence index wildcard can only be '*' or slice (e.g. 1:3)")


def match_key(k, wild_key, sep='|', inv='!'):
    if wild_key[0] == inv:
        return not any(fnmatchcase(k, key) for key in wild_key[1:].split(sep))
    return any(fnmatchcase(k, key) for key in wild_key.split(sep))


def _get_with_key(value, k):
    try:
        return value.__getitem__(k)
    except AttributeError:
        return value


def _get_with_slice(value, s, obj):
    if isinstance(value, Sequence):
        return value
    else:
        return [value for _ in range(*s.indices(len(obj)))]


class WildPath(BasePath):
    """
    Implementation of the baseclass that allows for wildcards, multiple keys and slicing.
    """

    sep = "."

    def _get_in(self, obj):
        """returns item at wildpath 'self' from the 'obj'"""
        if not len(self):
            return obj
        key = self[0]
        if '*' in key or '?' in key or ':' in key or "|" in key or '!' in key:
            if isinstance(obj, Mapping):
                return obj.__class__((k, self[1:]._get_in(v)) for k, v in obj.items() if match_key(k, key))
            elif isinstance(obj, Sequence):
                return obj.__class__(map(self[1:]._get_in, obj[parse_slice_star(key)]))
            else:
                return {k: self[1:]._get_in(v) for k, v in obj.__dict__.items() if match_key(k, key)}
        else:
            if isinstance(obj, Mapping):
                return self[1:]._get_in(obj[key])
            elif isinstance(obj, Sequence):
                return self[1:]._get_in(obj[int(key)])
            else:
                return self[1:]._get_in(getattr(obj, key))

    def set_in(self, obj, value):
        """sets item(s) at wildpath 'self' from the 'obj' to 'value'"""
        key = self[0]
        if '*' in key or '?' in key or ':' in key or "|" in key or '!' in key:
            if len(self) == 1:
                if isinstance(obj, MutableMapping):
                    [obj.__setitem__(k, _get_with_key(value, k)) for k in obj if match_key(k, key)]
                elif isinstance(obj, MutableSequence):
                    slice_ = parse_slice_star(key)
                    obj[slice_] = _get_with_slice(value, slice_, obj)
                else:
                    [setattr(obj, k, _get_with_key(value, k)) for k in obj.__dict__ if match_key(k, key)]
            else:
                if isinstance(obj, MutableMapping):
                    for _ in starmap(self[1:].set_in, ((v, _get_with_key(value, k))
                                                       for k, v in obj.items()
                                                       if match_key(k, key))):
                        pass
                elif isinstance(obj, MutableSequence):
                    slice_ = parse_slice_star(key)
                    for _ in map(self[1:].set_in, obj[slice_], _get_with_slice(value, slice_, obj)):
                        pass
                else:
                    for _ in starmap(self[1:].set_in, ((v, _get_with_key(value, k))
                                                       for k, v in obj.__dict__.items()
                                                       if match_key(k, key))):
                        pass
        else:
            if len(self) == 1:
                if isinstance(obj, MutableMapping):
                    obj[key] = value
                elif isinstance(obj, MutableSequence):
                    obj[int(key)] = value
                else:
                    setattr(obj, key, value)
            else:
                if isinstance(obj, Mapping):
                    self[1:].set_in(obj[key], value)
                elif isinstance(obj, Sequence):
                    self[1:].set_in(obj[int(key)], value)
                else:
                    self[1:].set_in(getattr(obj, key), value)

    def del_in(self, obj):
        """deletes item(s) at wildpath 'self' from the 'obj'"""
        key = self[0]
        if '*' in key or '?' in key or ':' in key or "|" in key or '!' in key:
            if len(self) == 1:
                if isinstance(obj, MutableMapping):
                    [obj.__delitem__(k) for k in list(obj.keys()) if match_key(k, key)]
                elif isinstance(obj, MutableSequence):
                    del obj[parse_slice_star(key)]
                else:
                    [delattr(obj, k) for k in list(obj.__dict__.keys()) if match_key(k, key)]
            else:
                if isinstance(obj, MutableMapping):
                    for _ in map(self[1:].del_in, (v for k, v in obj.items() if match_key(k, key))):
                        pass
                elif isinstance(obj, MutableSequence):
                    for _ in map(self[1:].del_in, obj[parse_slice_star(key)]):
                        pass
                else:
                    for _ in map(self[1:].del_in, (v for k, v in obj.__dict__.items() if match_key(k, key))):
                        pass
        else:
            if len(self) == 1:
                if isinstance(obj, MutableMapping):
                    del obj[key]
                elif isinstance(obj, MutableSequence):
                    del obj[int(key)]
                else:
                    delattr(obj, key)
            else:
                if isinstance(obj, Mapping):
                    self[1:].del_in(obj[key])
                elif isinstance(obj, Sequence):
                    self[1:].del_in(obj[int(key)])
                else:
                    self[1:].del_in(getattr(obj, key))



if __name__ == "__main__":
    pass