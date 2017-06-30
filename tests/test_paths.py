import json
import unittest

from copy import deepcopy

from wildpath.paths import Path, WildPath, parse_slice


class Object(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestBase(unittest.TestCase):

    def setUp(self):
        self.simple = Object(
            a=1,
            b=[2, 3],
            c=dict(d=4, e=5),
            d=Object(e=6),
            e=[dict(a=7, b=8),
               dict(b=9, c=0)]
        )
        self.complex = Object(
            aa=1,
            ba=[2, 3],
            bb=[4, 5],
            ca=dict(d=6, e=7, f=8),
            cb=Object(e=9),
            ff=[1,2,3,4,5,6],
            gg=[dict(a=1, b=2), dict(b=3, c=4), dict(a=5, b=6, c=7)]
        )


class TestPath(TestBase):

    def test_slice(self):
        path = Path("1.a.2.b.3.c")
        self.assertEqual(type(path[-1:0:-2]), Path)
        self.assertEqual(path[::2], Path("1.2.3"))
        self.assertEqual(path[1:-1], Path("a.2.b.3"))
        self.assertEqual(path[-1:0:-2], Path("c.b.a"))

    def test_some_basics(self):
        path = Path('')

    def test_basic_get(self):
        p1 = Path("a")
        p2 = Path("1")
        self.assertEqual(p1.get_in(dict(a=1)), 1)
        self.assertEqual(p2.get_in([0, 1]), 1)
        self.assertEqual(p1.get_in(Object(a=1)), 1)

    def test_basic_set(self):
        p1 = Path("a")
        p2 = Path("1")
        d = dict(a=1)
        l = [0, 1]
        o = Object(a=1)
        p1.set_in(d, 0)
        p2.set_in(l, 0)
        p1.set_in(o, 0)
        self.assertEqual(p1.get_in(d), 0)
        self.assertEqual(p2.get_in(l), 0)
        self.assertEqual(p1.get_in(o), 0)

    def test_basic_del(self):
        p1 = Path("a")
        p2 = Path("1")
        d = dict(a=1)
        l = [0, 1]
        o = Object(a=1)
        p1.del_in(d)
        p2.del_in(l)
        p1.del_in(o)
        self.assertEqual(d, {})
        self.assertEqual(l, [0])
        self.assertEqual(len(o.__dict__), 0)

    def test_longer_get(self):
        s = deepcopy(self.simple)
        p = Path("b.0")
        self.assertEqual(p.get_in(s), 2)
        p = Path("c.d")
        self.assertEqual(p.get_in(s), 4)
        p = Path("d.e")
        self.assertEqual(p.get_in(s), 6)
        p = Path("e.1.b")
        self.assertEqual(p.get_in(s), 9)

    def test_longer_set(self):
        s = deepcopy(self.simple)
        p = Path("b.0")
        p.set_in(s, 11)
        self.assertEqual(p.get_in(s), 11)
        p = Path("c.d")
        p.set_in(s, 11)
        self.assertEqual(p.get_in(s), 11)
        p = Path("d.e")
        p.set_in(s, 11)
        self.assertEqual(p.get_in(s), 11)

    def test_longer_del(self):
        s = deepcopy(self.simple)
        p = Path("b.0")
        p.del_in(s)
        self.assertEqual(s.b, [3])
        p = Path("c.d")
        p.del_in(s)
        self.assertEqual(s.c, {"e": 5})
        p = Path("d.e")
        p.del_in(s)
        self.assertEqual(len(s.d.__dict__), 0)

    def test_exceptions(self):
        s = deepcopy(self.simple)
        with self.assertRaises(KeyError):
            Path("e.1.a").get_in(s)
        with self.assertRaises(IndexError):
            Path("e.2.a").get_in(s)
        with self.assertRaises(AttributeError):
            Path("f.3").get_in(s)

class TestIterators(TestBase):

    def test_iteritems_all(self):
        paths = [path for path in Path.items(self.simple, all=True)]
        self.assertEqual(len(paths), 16)

        new = {}
        for path, value in Path.items(self.simple, all=True):
            path.set_in(new, value)

        for path in Path.paths(new):
            self.assertEqual(path.get_in(self.simple), path.get_in(new))

    def test_iteritems(self):
        items = [path for path in Path.items(self.simple, all=False)]
        self.assertTrue(all(isinstance(item, tuple) for item in items))
        self.assertEqual(len(items), 10)


class TestWildPath(TestBase):

    def test_pop(self):
        for path_string in ["b*", "ca|cb", "ca.d", "gg.*.b", "ff.*", "ff.:", "*", "ff.::2", "ff.-1:0:-2"]:
            obj = deepcopy(self.complex)
            path = WildPath(path_string)
            get = path.get_in(obj)
            self.assertEqual(path.pop_in(obj), get)

    def test_slice(self):
        path = WildPath("1.a.2.b.3.c")
        self.assertEqual(type(path[-1:0:-2]), WildPath)
        self.assertEqual(path[::2], WildPath("1.2.3"))
        self.assertEqual(path[1:-1], WildPath("a.2.b.3"))
        self.assertEqual(path[-1:0:-2], WildPath("c.b.a"))

    def test_basic_get(self):
        p1 = WildPath("a")
        p2 = WildPath("1")
        self.assertEqual(p1.get_in(dict(a=1)), 1)
        self.assertEqual(p2.get_in([0, 1]), 1)
        self.assertEqual(p1.get_in(Object(a=1)), 1)

    def test_basic_set(self):
        p1 = WildPath("a")
        p2 = WildPath("1")
        d = dict(a=1)
        l = [0, 1]
        o = Object(a=1)
        p1.set_in(d, 0)
        p2.set_in(l, 0)
        p1.set_in(o, 0)
        self.assertEqual(p1.get_in(d), 0)
        self.assertEqual(p2.get_in(l), 0)
        self.assertEqual(p1.get_in(o), 0)

    def test_basic_del(self):
        p1 = WildPath("a")
        p2 = WildPath("1")
        d = dict(a=1)
        l = [0, 1]
        o = Object(a=1)
        p1.del_in(d)
        p2.del_in(l)
        p1.del_in(o)
        self.assertEqual(d, {})
        self.assertEqual(l, [0])
        self.assertEqual(len(o.__dict__), 0)

    def test_longer_get(self):
        s = deepcopy(self.simple)
        p = WildPath("b.0")
        self.assertEqual(p.get_in(s), 2)
        p = WildPath("c.d")
        self.assertEqual(p.get_in(s), 4)
        p = WildPath("d.e")
        self.assertEqual(p.get_in(s), 6)

    def test_longer_set(self):
        s = deepcopy(self.simple)
        p = WildPath("b.0")
        p.set_in(s, 11)
        self.assertEqual(p.get_in(s), 11)
        p = WildPath("c.d")
        p.set_in(s, 11)
        self.assertEqual(p.get_in(s), 11)
        p = WildPath("d.e")
        p.set_in(s, 11)
        self.assertEqual(p.get_in(s), 11)
        s = deepcopy(self.simple)
        p = WildPath("e.*.b")
        p.set_in(s, [11,12])
        self.assertEqual(p.get_in(s), [11,12])

    def test_constant_set(self):
        s = deepcopy(self.simple)
        p = WildPath("e.*.b")
        p.set_in(s, 13)
        self.assertEqual(p.get_in(s), [13,13])

        s = deepcopy(self.simple)
        p = WildPath("e.*.*")
        p.set_in(s, 13)
        self.assertEqual(p.get_in(s), [{'a': 13, 'b': 13}, {'c': 13, 'b': 13}])

        s = deepcopy(self.simple)
        p = WildPath("e.*")
        p.set_in(s, 13)
        self.assertEqual(p.get_in(s), [13, 13])

    def test_longer_del(self):
        s = deepcopy(self.simple)
        p = WildPath("b.0")
        p.del_in(s)
        self.assertEqual(s.b, [3])
        p = WildPath("c.d")
        p.del_in(s)
        self.assertEqual(s.c, {"e": 5})
        p = WildPath("d.e")
        p.del_in(s)
        self.assertEqual(len(s.d.__dict__), 0)

    def test_wild_slice(self):
        s = deepcopy(self.complex)
        self.assertEqual(WildPath("ff.::2").get_in(s), [1,3,5])
        self.assertEqual(WildPath("ff.1:3").get_in(s), [2,3])
        self.assertEqual(WildPath("ff.:").get_in(s), [1,2,3,4,5,6])
        self.assertEqual(WildPath("ff.-1:0:-2").get_in(s), [6,4,2])
        self.assertEqual(WildPath("gg.:2.b").get_in(s), [2,3])
        with self.assertRaises(KeyError):
            self.assertEqual(WildPath("gg.:2.a").get_in(s), [6,4,2])

        WildPath("ff.1:3").set_in(s, [7])
        self.assertEqual(s.ff, [1,7,4,5,6])
        s = deepcopy(self.complex)
        WildPath("ff.0:3").del_in(s)
        self.assertEqual(s.ff, [4,5,6])

    def test_wild_or(self):
        s = deepcopy(self.complex)
        self.assertEqual(WildPath("aa|ba").get_in(s), {"aa": 1, "ba": [2, 3]})
        self.assertEqual(WildPath("ca.d|e").get_in(s), {"d": 6, "e": 7})

    def test_wild_get(self):
        s = deepcopy(self.complex)
        self.assertEqual(WildPath("bb.*").get_in(s), [4, 5])
        self.assertEqual(WildPath("b*.1").get_in(s), {'ba': 3, 'bb': 5})
        self.assertEqual(WildPath("c*.e").get_in(s), {'ca': 7, 'cb': 9})
        self.assertEqual(WildPath("c*.e*").get_in(s), {'ca': {'e': 7}, 'cb': {'e': 9}})

    def test_wild_set(self):
        p1 = WildPath("bb.*")
        p2 = WildPath("b*.1")
        p3 = WildPath("c*.e")
        p4 = WildPath("c*.e*")
        s = deepcopy(self.complex)
        p1.set_in(s, [14,15])
        self.assertEqual(p1.get_in(s), [14, 15])
        s = deepcopy(self.complex)
        p2.set_in(s, {'ba': 13, 'bb': 15})
        self.assertEqual(p2.get_in(s), {'ba': 13, 'bb': 15})
        s = deepcopy(self.complex)
        p3.set_in(s, {'ca': 17, 'cb': 18})
        self.assertEqual(p3.get_in(s), {'ca': 17, 'cb': 18})
        s = deepcopy(self.complex)
        p4.set_in(s, {'ca': {'e': 17}, 'cb': {'e': 18}})
        self.assertEqual(p4.get_in(s), {'ca': {'e': 17}, 'cb': {'e': 18}})

    def test_wild_del(self):
        p1 = WildPath("bb.*")
        p2 = WildPath("b*.1")
        p3 = WildPath("c*.e")
        p4 = WildPath("c*.e*")
        p5 = WildPath("*")
        s = deepcopy(self.complex)
        p1.del_in(s)
        self.assertEqual(p1.get_in(s), [])
        s = deepcopy(self.complex)
        p2.del_in(s)
        self.assertEqual(s.ba, [2])
        self.assertEqual(s.bb, [4])
        s = deepcopy(self.complex)
        p3.del_in(s)
        self.assertEqual(s.ca, {"d": 6, "f": 8})
        self.assertEqual(s.cb.__dict__, {})
        s = deepcopy(self.complex)
        p4.del_in(s)
        self.assertEqual(s.ca, {"d": 6, "f": 8})
        self.assertEqual(s.cb.__dict__, {})
        s = deepcopy(self.complex)
        p5.del_in(s)
        self.assertEqual(s.__dict__, {})

    def test_exceptions(self):
        s = deepcopy(self.simple)
        with self.assertRaises(KeyError):
            Path("e.1.a").get_in(s)
        with self.assertRaises(IndexError):
            Path("e.2.a").get_in(s)
        with self.assertRaises(AttributeError):
            Path("f.3").get_in(s)


class TestOther(unittest.TestCase):

    def test_parse_slice(self):
        s = parse_slice("0:1")
        self.assertEqual((s.start, s.stop, s.step), (0,1,None))
        s = parse_slice(":1")
        self.assertEqual((s.start, s.stop, s.step), (None,1,None))
        s = parse_slice("0:1:2")
        self.assertEqual((s.start, s.stop, s.step), (0,1,2))
        s = parse_slice(":1:2")
        self.assertEqual((s.start, s.stop, s.step), (None,1,2))
        s = parse_slice("::2")
        self.assertEqual((s.start, s.stop, s.step), (None,None,2))
        s = parse_slice(":")
        self.assertEqual((s.start, s.stop, s.step), (None,None,None))




